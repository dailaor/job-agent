from __future__ import annotations

import base64
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from pypdf import PdfWriter

from job_agent.config import AgentConfig, Preferences, load_config, save_config
from job_agent.models import Candidate
from job_agent.service import AgentService


def _docx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>本科，3 年工作经验，熟悉 SQL、Python、数据分析和需求分析</w:t></w:r></w:p></w:body></w:document>""",
        )
    return buffer.getvalue()


def _pdf_bytes(title: str = "test") -> bytes:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Title": title})
    writer.write(buffer)
    return buffer.getvalue()


class ResumeServiceTests(unittest.TestCase):
    def _service(self, directory: str) -> AgentService:
        config_path = Path(directory) / "config.json"
        save_config(
            AgentConfig(
                candidate=Candidate("测试用户"),
                preferences=Preferences(),
                greetings={"default": "您好"},
            ),
            config_path,
        )
        return AgentService(config_path, Path(directory) / "data" / "agent.sqlite3")

    def test_pdf_can_be_replaced_by_docx_and_updates_active_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            pdf = _pdf_bytes("first")
            first = service.replace_resume("求职简历.pdf", base64.b64encode(pdf).decode("ascii"))
            pdf_path = Path(first["path"])
            self.assertTrue(pdf_path.is_file())

            second = service.replace_resume("新版简历.docx", base64.b64encode(_docx_bytes()).decode("ascii"))
            config = load_config(service.config_path)
            self.assertEqual(config.candidate.resume_filename, "新版简历.docx")
            self.assertEqual(config.candidate.resume_path, second["path"])
            self.assertEqual(config.candidate.profile_source, "resume")
            self.assertIn("SQL", config.candidate.skills)
            self.assertEqual(config.candidate.years_experience, 3)
            self.assertEqual(config.candidate.education, "本科")
            self.assertTrue(Path(second["path"]).is_file())
            self.assertFalse(pdf_path.exists())

    def test_invalid_file_does_not_change_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            before = service.get_config()
            with self.assertRaisesRegex(ValueError, "不是有效"):
                service.replace_resume("伪造.pdf", base64.b64encode(b"not a pdf").decode("ascii"))
            self.assertEqual(service.get_config(), before)

    def test_replacing_same_extension_with_relative_data_path_keeps_file(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            service = self._service(directory)
            service.database_path = Path(os.path.relpath(Path(directory) / "data" / "agent.sqlite3", Path.cwd()))
            first = _pdf_bytes("first")
            second = _pdf_bytes("second")
            service.replace_resume("first.pdf", base64.b64encode(first).decode("ascii"))
            result = service.replace_resume("second.pdf", base64.b64encode(second).decode("ascii"))
            self.assertEqual(Path(result["path"]).read_bytes(), second)

    def test_missing_previous_resume_can_be_recovered_through_upload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            first = service.replace_resume("first.pdf", base64.b64encode(_pdf_bytes("first")).decode("ascii"))
            Path(first["path"]).unlink()
            self.assertFalse(service.resume_info()["available"])
            recovered = service.replace_resume("recovered.pdf", base64.b64encode(_pdf_bytes("recovered")).decode("ascii"))
            self.assertTrue(Path(recovered["path"]).is_file())

    def test_config_failure_restores_previous_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            first_bytes = _pdf_bytes("first")
            first = service.replace_resume("first.pdf", base64.b64encode(first_bytes).decode("ascii"))
            before = service.get_config()
            with patch("job_agent.service.save_config", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    service.replace_resume("second.pdf", base64.b64encode(_pdf_bytes("second")).decode("ascii"))
            self.assertEqual(Path(first["path"]).read_bytes(), first_bytes)
            self.assertEqual(service.get_config(), before)

    def test_unreadable_new_resume_does_not_reuse_old_inferred_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            service.replace_resume("profile.docx", base64.b64encode(_docx_bytes()).decode("ascii"))
            result = service.replace_resume("scan.pdf", base64.b64encode(_pdf_bytes("scan")).decode("ascii"))
            candidate = result["config"]["candidate"]
            self.assertFalse(result["profile_updated"])
            self.assertEqual(candidate["profile_source"], "manual_review")
            self.assertEqual(candidate["skills"], [])
            self.assertEqual(candidate["years_experience"], 0)


if __name__ == "__main__":
    unittest.main()
