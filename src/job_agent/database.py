from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import ApplicationStatus, Evaluation, Job, JobStatus, utc_now


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    url TEXT NOT NULL,
    apply_url TEXT,
    description TEXT NOT NULL DEFAULT '',
    salary_min INTEGER,
    salary_max INTEGER,
    experience_min REAL,
    experience_max REAL,
    education TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    deadline TEXT,
    recruiter_name TEXT,
    recruiter_activity TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS evaluations (
    job_id INTEGER PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    hard_pass INTEGER NOT NULL,
    strategy TEXT NOT NULL,
    ability_relation TEXT NOT NULL,
    matched_json TEXT NOT NULL,
    missing_json TEXT NOT NULL,
    hard_reasons_json TEXT NOT NULL,
    match_score REAL NOT NULL,
    need_score REAL NOT NULL DEFAULT 50,
    company_score REAL NOT NULL,
    overall_score REAL NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    greeting TEXT,
    external_id TEXT,
    evidence TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(job_id)
);
CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    records_count INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            evaluation_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(evaluations)").fetchall()
            }
            if "need_score" not in evaluation_columns:
                connection.execute("ALTER TABLE evaluations ADD COLUMN need_score REAL NOT NULL DEFAULT 50")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def event(self, entity_type: str, entity_id: str | int, event_type: str, payload: dict[str, Any] | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO events(entity_type, entity_id, event_type, payload_json, occurred_at) VALUES (?, ?, ?, ?, ?)",
                (entity_type, str(entity_id), event_type, json.dumps(payload or {}, ensure_ascii=False), utc_now()),
            )

    def upsert_job(self, job: Job) -> tuple[int, bool]:
        now = utc_now()
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM jobs WHERE source=? AND source_id=?", (job.source, job.source_id)
            ).fetchone()
            if existing:
                job_id = int(existing["id"])
                connection.execute(
                    """UPDATE jobs SET title=?, company=?, location=?, url=?, apply_url=?, description=?,
                       salary_min=?, salary_max=?, experience_min=?, experience_max=?, education=?, published_at=?,
                       deadline=?, recruiter_name=?, recruiter_activity=?, metadata_json=?, last_seen_at=? WHERE id=?""",
                    (
                        job.title, job.company, job.location, job.url, job.apply_url, job.description,
                        job.salary_min, job.salary_max, job.experience_min, job.experience_max,
                        job.education, job.published_at, job.deadline, job.recruiter_name,
                        job.recruiter_activity, json.dumps(job.metadata, ensure_ascii=False), now, job_id,
                    ),
                )
                return job_id, False
            duplicate = connection.execute(
                "SELECT id FROM jobs WHERE fingerprint=? LIMIT 1", (job.fingerprint,)
            ).fetchone()
            status = JobStatus.DUPLICATE.value if duplicate else JobStatus.DISCOVERED.value
            cursor = connection.execute(
                """INSERT INTO jobs(fingerprint, source, source_id, title, company, location, url, apply_url,
                   description, salary_min, salary_max, experience_min, experience_max, education, published_at,
                   deadline, recruiter_name, recruiter_activity, metadata_json, status, first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job.fingerprint, job.source, job.source_id, job.title, job.company, job.location, job.url,
                    job.apply_url, job.description, job.salary_min, job.salary_max, job.experience_min,
                    job.experience_max, job.education, job.published_at, job.deadline, job.recruiter_name,
                    job.recruiter_activity, json.dumps(job.metadata, ensure_ascii=False), status, now, now,
                ),
            )
            return int(cursor.lastrowid), True

    def resolve_fingerprint_priority(self, fingerprint: str, channel_priority: list[str]) -> None:
        """Keep one cross-channel record, without replacing an already-started application."""
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT j.id, j.source, j.status, a.id AS application_id FROM jobs j
                   LEFT JOIN applications a ON a.job_id=j.id WHERE j.fingerprint=? ORDER BY j.id""",
                (fingerprint,),
            ).fetchall()
            if len(rows) < 2:
                return
            started = [row for row in rows if row["application_id"] is not None]
            if started:
                winner_id = int(started[0]["id"])
            else:
                def rank(row: sqlite3.Row) -> tuple[int, int]:
                    channel = "official" if str(row["source"]).startswith("official:") else str(row["source"])
                    try:
                        priority = channel_priority.index(channel)
                    except ValueError:
                        priority = len(channel_priority)
                    return priority, int(row["id"])
                winner_id = int(min(rows, key=rank)["id"])
            for row in rows:
                job_id = int(row["id"])
                if job_id == winner_id:
                    if row["status"] == JobStatus.DUPLICATE.value:
                        connection.execute("UPDATE jobs SET status=? WHERE id=?", (JobStatus.DISCOVERED.value, job_id))
                elif row["application_id"] is None and row["status"] in {
                    JobStatus.DISCOVERED.value, JobStatus.ELIGIBLE.value, JobStatus.DUPLICATE.value
                }:
                    connection.execute("UPDATE jobs SET status=? WHERE id=?", (JobStatus.DUPLICATE.value, job_id))

    def list_jobs(self, *, status: str | None = None, source: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("j.status=?")
            params.append(status)
        if source:
            clauses.append("j.source=?")
            params.append(source)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = f"""SELECT j.*, e.strategy, e.ability_relation, e.match_score, e.need_score, e.company_score,
                    e.overall_score, e.reason AS evaluation_reason, e.hard_reasons_json,
                    a.status AS application_status, a.id AS application_id
                    FROM jobs j LEFT JOIN evaluations e ON e.job_id=j.id
                    LEFT JOIN applications a ON a.job_id=j.id{where}
                    ORDER BY COALESCE(e.overall_score, -1) DESC, j.id DESC LIMIT ?"""
        params.append(limit)
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def get_job(self, job_id: int) -> Job | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return Job.from_row(dict(row)) if row else None

    def set_job_status(self, job_id: int, status: JobStatus) -> None:
        with self.connect() as connection:
            connection.execute("UPDATE jobs SET status=? WHERE id=?", (status.value, job_id))

    def save_evaluation(self, evaluation: Evaluation) -> None:
        data = evaluation.to_dict()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO evaluations(job_id, hard_pass, strategy, ability_relation, matched_json,
                   missing_json, hard_reasons_json, match_score, need_score, company_score, overall_score, confidence,
                   reason, evaluated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(job_id) DO UPDATE SET hard_pass=excluded.hard_pass, strategy=excluded.strategy,
                   ability_relation=excluded.ability_relation, matched_json=excluded.matched_json,
                   missing_json=excluded.missing_json, hard_reasons_json=excluded.hard_reasons_json,
                   match_score=excluded.match_score, need_score=excluded.need_score, company_score=excluded.company_score,
                   overall_score=excluded.overall_score, confidence=excluded.confidence,
                   reason=excluded.reason, evaluated_at=excluded.evaluated_at""",
                (
                    evaluation.job_id, int(evaluation.hard_pass), data["strategy"], evaluation.ability_relation,
                    json.dumps(evaluation.matched_capabilities, ensure_ascii=False),
                    json.dumps(evaluation.missing_capabilities, ensure_ascii=False),
                    json.dumps(evaluation.hard_reasons, ensure_ascii=False), evaluation.match_score, evaluation.need_score,
                    evaluation.company_score, evaluation.overall_score, evaluation.confidence,
                    evaluation.reason, utc_now(),
                ),
            )

    def create_application(self, job_id: int, channel: str, greeting: str | None = None) -> int:
        now = utc_now()
        with self.connect() as connection:
            existing = connection.execute("SELECT id FROM applications WHERE job_id=?", (job_id,)).fetchone()
            if existing:
                return int(existing["id"])
            cursor = connection.execute(
                "INSERT INTO applications(job_id, channel, status, greeting, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, channel, ApplicationStatus.PLANNED.value, greeting, now, now),
            )
            return int(cursor.lastrowid)

    def update_application(
        self,
        application_id: int,
        status: ApplicationStatus,
        *,
        evidence: str | None = None,
        error: str | None = None,
        external_id: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE applications SET status=?, evidence=COALESCE(?, evidence), error=?,
                   external_id=COALESCE(?, external_id), updated_at=? WHERE id=?""",
                (status.value, evidence, error, external_id, utc_now(), application_id),
            )
        self.event("application", application_id, status.value, {"evidence": evidence, "error": error})

    def list_applications(self, *, status: str | None = None, channel: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("a.status=?")
            params.append(status)
        if channel:
            clauses.append("a.channel=?")
            params.append(channel)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT a.*, j.title, j.company, j.location, j.url, j.apply_url, j.source,
                    e.strategy, e.overall_score FROM applications a
                    JOIN jobs j ON j.id=a.job_id LEFT JOIN evaluations e ON e.job_id=j.id
                    {where} ORDER BY a.updated_at DESC LIMIT ?""", params
            ).fetchall()
        return [dict(row) for row in rows]

    def eligible_jobs_for_sources(self, sources: list[str], limit: int = 500) -> list[dict[str, Any]]:
        """Return unplanned eligible jobs for an explicit set of registered source IDs."""

        normalized = list(dict.fromkeys(source.strip() for source in sources if source.strip()))
        if not normalized:
            return []
        placeholders = ",".join("?" for _ in normalized)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT j.*, e.strategy, e.overall_score, e.match_score, e.need_score, e.company_score
                    FROM jobs j JOIN evaluations e ON e.job_id=j.id
                    LEFT JOIN applications a ON a.job_id=j.id
                    WHERE j.status=? AND j.source IN ({placeholders}) AND e.strategy<>? AND a.id IS NULL
                    ORDER BY e.overall_score DESC, j.id DESC LIMIT ?""",
                (JobStatus.ELIGIBLE.value, *normalized, "不投", limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_application(self, application_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT a.*, j.title, j.company, j.location, j.url, j.apply_url, j.source
                   FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.id=?""",
                (application_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_events(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def today_action_count(self, channel: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT COUNT(*) AS count FROM applications WHERE channel=? AND (
                   (substr(created_at,1,10)=substr(?,1,10) AND status=?) OR
                   (substr(updated_at,1,10)=substr(?,1,10) AND status IN (?, ?, ?, ?))
                   )""",
                (
                    channel, utc_now(), ApplicationStatus.PLANNED.value, utc_now(),
                    ApplicationStatus.AWAITING_REPLY.value, ApplicationStatus.HR_REPLIED.value,
                    ApplicationStatus.OFFICIAL_SUBMITTED.value, ApplicationStatus.CONFIRMED.value,
                ),
            ).fetchone()
        return int(row["count"])

    def dashboard(self) -> dict[str, Any]:
        with self.connect() as connection:
            jobs = {row["status"]: row["count"] for row in connection.execute("SELECT status, COUNT(*) count FROM jobs GROUP BY status")}
            apps = {row["status"]: row["count"] for row in connection.execute("SELECT status, COUNT(*) count FROM applications GROUP BY status")}
            strategies = {row["strategy"]: row["count"] for row in connection.execute("SELECT strategy, COUNT(*) count FROM evaluations GROUP BY strategy")}
            recent_events = [dict(row) for row in connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT 20")]
            sources = [dict(row) for row in connection.execute("SELECT * FROM source_runs ORDER BY id DESC LIMIT 20")]
        return {"jobs": jobs, "applications": apps, "strategies": strategies, "events": recent_events, "sources": sources}

    def record_source_run(self, source: str, status: str, records_count: int, message: str, started_at: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO source_runs(source,status,records_count,message,started_at,finished_at) VALUES(?,?,?,?,?,?)",
                (source, status, records_count, message, started_at, utc_now()),
            )

    def latest_source_runs(self) -> dict[str, dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT sr.* FROM source_runs sr
                   JOIN (SELECT source, MAX(id) AS max_id FROM source_runs GROUP BY source) latest
                     ON latest.max_id=sr.id
                   ORDER BY sr.id DESC"""
            ).fetchall()
        return {str(row["source"]): dict(row) for row in rows}
