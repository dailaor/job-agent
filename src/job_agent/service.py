from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import AgentConfig, config_from_dict, config_to_dict, load_config, save_config
from .database import Database
from .orchestrator import JobAgent
from .resume import extract_resume_text, infer_resume_profile


class AgentService:
    MAX_RESUME_BYTES = 10 * 1024 * 1024

    def __init__(self, config_path: str | Path, database_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self.database_path = Path(database_path)

    @property
    def config(self) -> AgentConfig:
        return load_config(self.config_path)

    @property
    def db(self) -> Database:
        return Database(self.database_path)

    def agent(self) -> JobAgent:
        return JobAgent(self.config, self.db)

    def get_config(self) -> dict[str, Any]:
        return config_to_dict(self.config)

    def resume_info(self) -> dict[str, Any]:
        candidate = self.config.candidate
        path = Path(candidate.resume_path).expanduser() if candidate.resume_path else None
        return {
            "configured": bool(candidate.resume_path),
            "available": bool(path and path.is_file()),
            "filename": candidate.resume_filename or (path.name if path else ""),
            "path": str(path) if path else "",
            "profile_source": candidate.profile_source,
            "text_available": bool(candidate.resume_text_path and Path(candidate.resume_text_path).is_file()),
        }

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = config_from_dict(payload)
        save_config(config, self.config_path)
        return config_to_dict(config)

    def replace_resume(self, filename: str, content_base64: str) -> dict[str, Any]:
        """Validate and atomically replace the one active, locally managed resume."""

        display_name = Path(filename).name.strip()
        suffix = Path(display_name).suffix.lower()
        if not display_name or suffix not in {".pdf", ".docx"}:
            raise ValueError("仅支持 PDF 或 DOCX 简历")
        encoded = content_base64.split(",", 1)[-1] if content_base64.startswith("data:") else content_base64
        encoded = "".join(encoded.split())
        if not encoded:
            raise ValueError("简历文件为空")
        if len(encoded) > ((self.MAX_RESUME_BYTES + 2) // 3) * 4 + 8:
            raise ValueError("简历不能超过 10 MB")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("简历内容不是有效的 Base64 数据") from exc
        if not content:
            raise ValueError("简历文件为空")
        if len(content) > self.MAX_RESUME_BYTES:
            raise ValueError("简历不能超过 10 MB")
        extracted_text = extract_resume_text(suffix, content)
        inferred = infer_resume_profile(extracted_text)

        resume_dir = self.database_path.parent / "resumes"
        resume_dir.mkdir(parents=True, exist_ok=True)
        target = resume_dir / f"current{suffix}"
        text_target = resume_dir / "current.txt"
        config = self.config
        previous_path = Path(config.candidate.resume_path) if config.candidate.resume_path else None
        previous_profile_source = config.candidate.profile_source
        config.candidate.resume_path = str(target.resolve())
        config.candidate.resume_filename = display_name
        config.candidate.resume_text_path = str(text_target.resolve())
        if inferred.skills:
            config.candidate.skills = inferred.skills
        if inferred.years_experience is not None:
            config.candidate.years_experience = inferred.years_experience
        if inferred.education is not None:
            config.candidate.education = inferred.education
        inferred_any = bool(inferred.skills or inferred.years_experience is not None or inferred.education is not None)
        inferred_complete = bool(inferred.skills and inferred.years_experience is not None and inferred.education is not None)
        if inferred_any:
            config.candidate.profile_source = "resume" if inferred_complete else "resume_partial"
        elif previous_profile_source != "manual":
            # Never silently score a new unreadable resume with a prior resume's inferred profile.
            config.candidate.skills = []
            config.candidate.years_experience = 0
            config.candidate.education = ""
            config.candidate.profile_source = "manual_review"

        transaction_id = uuid4().hex
        temporary = resume_dir / f".{target.name}.{transaction_id}.uploading"
        text_temporary = resume_dir / f".{text_target.name}.{transaction_id}.uploading"
        target_backup = resume_dir / f".{target.name}.{transaction_id}.backup"
        text_backup = resume_dir / f".{text_target.name}.{transaction_id}.backup"
        temporary.write_bytes(content)
        text_temporary.write_text(extracted_text, encoding="utf-8")
        target_had_value = target.is_file()
        text_had_value = text_target.is_file()
        try:
            if target_had_value:
                target.replace(target_backup)
            if text_had_value:
                text_target.replace(text_backup)
            temporary.replace(target)
            text_temporary.replace(text_target)
            save_config(config, self.config_path)
        except Exception:
            for created in (target, text_target):
                try:
                    if created.is_file():
                        created.unlink()
                except OSError:
                    pass
            if target_had_value and target_backup.is_file():
                target_backup.replace(target)
            if text_had_value and text_backup.is_file():
                text_backup.replace(text_target)
            for leftover in (temporary, text_temporary):
                try:
                    if leftover.is_file():
                        leftover.unlink()
                except OSError:
                    pass
            raise
        else:
            for backup in (target_backup, text_backup):
                try:
                    if backup.is_file():
                        backup.unlink()
                except OSError:
                    pass

        managed_names = {"current.pdf", "current.docx"}
        target_resolved = target.resolve()
        previous_resolved = previous_path.expanduser().resolve() if previous_path else None
        if previous_path and previous_path.name.lower() in managed_names and previous_resolved != target_resolved:
            try:
                if previous_resolved and previous_resolved.parent == resume_dir.resolve() and previous_resolved.is_file():
                    previous_resolved.unlink()
            except OSError:
                pass
        return {
            "filename": display_name,
            "path": str(target.resolve()),
            "size": len(content),
            "extracted_characters": len(extracted_text),
            "profile_updated": inferred_any,
            "config": config_to_dict(config),
        }

    def dashboard(self) -> dict[str, Any]:
        data = self.db.dashboard()
        data["channels"] = self.agent().channel_catalog()
        return data

    def channels(self) -> list[dict[str, Any]]:
        return self.agent().channel_catalog()

    def jobs(self) -> list[dict[str, Any]]:
        return self.db.list_jobs()

    def applications(self) -> list[dict[str, Any]]:
        return self.db.list_applications()

    def events(self) -> list[dict[str, Any]]:
        return self.db.list_events()
