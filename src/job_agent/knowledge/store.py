from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path
from typing import Any

from ..database import Database
from ..models import utc_now
from .models import EvidenceBundle, KnowledgeChunk, PolicyDecision, PolicyStatus, PostDocument


KNOWLEDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL DEFAULT '',
    role_family TEXT NOT NULL DEFAULT '',
    employment_type TEXT NOT NULL DEFAULT 'unknown',
    business_unit TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    seniority TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    collected_at TEXT NOT NULL,
    collection_method TEXT NOT NULL,
    source_status TEXT NOT NULL,
    policy_status TEXT NOT NULL,
    policy_reasons_json TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    quality_score REAL NOT NULL,
    content_hash TEXT NOT NULL,
    content_text TEXT NOT NULL DEFAULT '',
    author_hash TEXT NOT NULL DEFAULT '',
    duplicate_of_document_id INTEGER REFERENCES knowledge_documents(id) ON DELETE SET NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source, url_hash)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_scope
    ON knowledge_documents(company, role_family, policy_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_hash ON knowledge_documents(content_hash);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    topic TEXT NOT NULL,
    text TEXT NOT NULL,
    contextual_text TEXT NOT NULL,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL,
    chunk_hash TEXT NOT NULL,
    embedding_provider TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    UNIQUE(document_id, chunk_hash)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_topic ON knowledge_chunks(topic);

CREATE TABLE IF NOT EXISTS knowledge_retrieval_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    company TEXT NOT NULL,
    role_family TEXT NOT NULL,
    employment_type TEXT NOT NULL DEFAULT 'unknown',
    query_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_evidence (
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL REFERENCES knowledge_chunks(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    retrieval_score REAL NOT NULL,
    rank INTEGER NOT NULL,
    retrieved_at TEXT NOT NULL,
    PRIMARY KEY(job_id, chunk_id, dimension)
);
"""


def _url_hash(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pack_vector(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def _unpack_vector(blob: bytes, dimensions: int) -> list[float]:
    if len(blob) != dimensions * 4:
        return []
    return list(struct.unpack(f"<{dimensions}f", blob))


class KnowledgeStore:
    def __init__(self, database: Database | str | Path) -> None:
        self.database = database if isinstance(database, Database) else Database(database)
        with self.database.connect() as connection:
            connection.executescript(KNOWLEDGE_SCHEMA)
            self._migrate_schema(connection)

    @staticmethod
    def _migrate_schema(connection: sqlite3.Connection) -> None:
        document_columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(knowledge_documents)")
        }
        if "employment_type" not in document_columns:
            connection.execute(
                "ALTER TABLE knowledge_documents ADD COLUMN employment_type TEXT NOT NULL DEFAULT 'unknown'"
            )
        retrieval_columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(knowledge_retrieval_runs)")
        }
        if "employment_type" not in retrieval_columns:
            connection.execute(
                "ALTER TABLE knowledge_retrieval_runs ADD COLUMN employment_type TEXT NOT NULL DEFAULT 'unknown'"
            )
        connection.execute(
            """UPDATE knowledge_documents
               SET employment_type = CASE
                   WHEN lower(title || ' ' || seniority) LIKE '%实习%'
                     OR lower(title || ' ' || seniority) LIKE '%intern%' THEN 'internship'
                   WHEN title LIKE '%校招%' OR title LIKE '%秋招%' OR title LIKE '%春招%'
                     OR title LIKE '%社招%' OR title LIKE '%正职%' OR title LIKE '%全职%'
                     OR seniority LIKE '%校招%' OR seniority LIKE '%社招%'
                     OR seniority LIKE '%正职%' OR seniority LIKE '%全职%' THEN 'full_time'
                   ELSE employment_type
               END
               WHERE employment_type='unknown'"""
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_documents_scope_v2
               ON knowledge_documents(company, role_family, employment_type, policy_status)"""
        )

    def save_document(
        self,
        document: PostDocument,
        decision: PolicyDecision,
        *,
        retain_full_text: bool,
    ) -> dict[str, Any]:
        now = utc_now()
        url_hash = _url_hash(document.url)
        with self.database.connect() as connection:
            duplicate = connection.execute(
                """SELECT id FROM knowledge_documents
                   WHERE content_hash=? AND policy_status=? AND NOT (source=? AND url_hash=?) LIMIT 1""",
                (document.content_hash, PolicyStatus.ACCEPTED.value, document.source, url_hash),
            ).fetchone()
            status = PolicyStatus.DUPLICATE if duplicate else decision.status
            reasons = list(decision.reasons)
            if duplicate:
                reasons.append(f"与知识文档 {int(duplicate['id'])} 内容重复")
            existing = connection.execute(
                "SELECT id FROM knowledge_documents WHERE source=? AND url_hash=?",
                (document.source, url_hash),
            ).fetchone()
            values = (
                document.url, document.title, decision.company, decision.role_family,
                decision.employment_type.value, document.business_unit, document.city,
                document.seniority, document.published_at,
                now, document.collection_method, document.source_status.value, status.value,
                json.dumps(reasons, ensure_ascii=False), json.dumps(decision.topics, ensure_ascii=False),
                decision.quality_score, document.content_hash,
                decision.sanitized_content if retain_full_text else "", document.author_hash,
                int(duplicate["id"]) if duplicate else None,
                json.dumps(document.metadata, ensure_ascii=False),
            )
            if existing:
                document_id = int(existing["id"])
                connection.execute(
                    """UPDATE knowledge_documents SET source_url=?, title=?, company=?, role_family=?, employment_type=?,
                       business_unit=?, city=?, seniority=?, published_at=?, collected_at=?, collection_method=?,
                       source_status=?, policy_status=?, policy_reasons_json=?, topics_json=?, quality_score=?,
                       content_hash=?, content_text=?, author_hash=?, duplicate_of_document_id=?, metadata_json=?
                       WHERE id=?""",
                    (*values, document_id),
                )
                connection.execute("DELETE FROM knowledge_chunks WHERE document_id=?", (document_id,))
                created = False
            else:
                cursor = connection.execute(
                    """INSERT INTO knowledge_documents(
                       source, source_url, url_hash, title, company, role_family, employment_type,
                       business_unit, city, seniority,
                       published_at, collected_at, collection_method, source_status, policy_status,
                       policy_reasons_json, topics_json, quality_score, content_hash, content_text, author_hash,
                       duplicate_of_document_id, metadata_json
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (document.source, *values[:1], url_hash, *values[1:]),
                )
                document_id = int(cursor.lastrowid)
                created = True
        return {
            "document_id": document_id,
            "created": created,
            "status": status.value,
            "reasons": reasons,
            "employment_type": decision.employment_type.value,
            "duplicate_of_document_id": int(duplicate["id"]) if duplicate else None,
        }

    def replace_chunks(
        self,
        document_id: int,
        chunks: list[KnowledgeChunk],
        *,
        embedding_provider: str,
        embedding_dimensions: int,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM knowledge_chunks WHERE document_id=?", (document_id,))
            connection.executemany(
                """INSERT INTO knowledge_chunks(
                   document_id, ordinal, topic, text, contextual_text, start_offset, end_offset, chunk_hash,
                   embedding_provider, embedding_dimensions, embedding
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        document_id, chunk.ordinal, chunk.topic, chunk.text, chunk.contextual_text,
                        chunk.start_offset, chunk.end_offset, chunk.chunk_hash, embedding_provider,
                        embedding_dimensions, sqlite3.Binary(_pack_vector(chunk.embedding)),
                    )
                    for chunk in chunks
                ],
            )

    def list_documents(self, *, limit: int = 200) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT d.*, COUNT(c.id) AS chunk_count FROM knowledge_documents d
                   LEFT JOIN knowledge_chunks c ON c.document_id=d.id
                   GROUP BY d.id ORDER BY d.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item.pop("content_text", None)
            item["policy_reasons"] = json.loads(item.pop("policy_reasons_json") or "[]")
            item["topics"] = json.loads(item.pop("topics_json") or "[]")
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            results.append(item)
        return results

    def stats(self) -> dict[str, Any]:
        with self.database.connect() as connection:
            documents = {
                row["policy_status"]: int(row["count"])
                for row in connection.execute(
                    "SELECT policy_status, COUNT(*) count FROM knowledge_documents GROUP BY policy_status"
                )
            }
            chunks = int(connection.execute("SELECT COUNT(*) count FROM knowledge_chunks").fetchone()["count"])
            scopes = [
                dict(row) for row in connection.execute(
                    """SELECT company, role_family, employment_type, COUNT(*) AS documents
                       FROM knowledge_documents WHERE policy_status=?
                       GROUP BY company, role_family, employment_type ORDER BY documents DESC""",
                    (PolicyStatus.ACCEPTED.value,),
                ).fetchall()
            ]
        return {"documents": documents, "chunks": chunks, "scopes": scopes}

    def delete_document(self, document_id: int) -> bool:
        with self.database.connect() as connection:
            retrieval_ids: list[int] = []
            for row in connection.execute("SELECT id, evidence_json FROM knowledge_retrieval_runs"):
                try:
                    evidence = json.loads(row["evidence_json"] or "{}")
                except json.JSONDecodeError:
                    # A malformed cache cannot be proven free of the deleted snippet.
                    retrieval_ids.append(int(row["id"]))
                    continue
                items = [*(evidence.get("ability") or []), *(evidence.get("need") or [])]
                if any(int(item.get("document_id", 0)) == document_id for item in items if isinstance(item, dict)):
                    retrieval_ids.append(int(row["id"]))
            if retrieval_ids:
                connection.executemany(
                    "DELETE FROM knowledge_retrieval_runs WHERE id=?",
                    [(retrieval_id,) for retrieval_id in retrieval_ids],
                )
            cursor = connection.execute("DELETE FROM knowledge_documents WHERE id=?", (document_id,))
            return cursor.rowcount > 0

    def candidate_chunks(
        self,
        *,
        role_family: str,
        employment_type: str,
        topics: list[str],
        embedding_provider: str,
        company: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        clauses = [
            "d.policy_status=?", "d.role_family=?", "d.employment_type=?", "c.embedding_provider=?",
        ]
        params: list[Any] = [
            PolicyStatus.ACCEPTED.value, role_family, employment_type, embedding_provider,
        ]
        if company:
            clauses.append("d.company=?")
            params.append(company)
        if topics:
            placeholders = ",".join("?" for _ in topics)
            clauses.append(f"c.topic IN ({placeholders})")
            params.extend(topics)
        params.append(limit)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""SELECT c.*, d.source, d.source_url, d.title, d.company, d.role_family, d.employment_type,
                    d.business_unit, d.published_at, d.quality_score, d.collection_method
                    FROM knowledge_chunks c JOIN knowledge_documents d ON d.id=c.document_id
                    WHERE {' AND '.join(clauses)} ORDER BY d.quality_score DESC, d.id DESC LIMIT ?""",
                params,
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["embedding"] = _unpack_vector(item["embedding"], int(item["embedding_dimensions"]))
            results.append(item)
        return results

    def save_retrieval(self, bundle: EvidenceBundle, queries: dict[str, str]) -> None:
        now = bundle.retrieved_at
        with self.database.connect() as connection:
            connection.execute("DELETE FROM evaluation_evidence WHERE job_id=?", (bundle.job_id,))
            connection.execute(
                """INSERT INTO knowledge_retrieval_runs(
                   job_id, company, role_family, employment_type, query_json, evidence_json, retrieved_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    bundle.job_id, bundle.company, bundle.role_family, bundle.employment_type,
                    json.dumps(queries, ensure_ascii=False), json.dumps(bundle.to_dict(), ensure_ascii=False), now,
                ),
            )
            for dimension, evidence in (("ability", bundle.ability), ("need", bundle.need)):
                connection.executemany(
                    """INSERT INTO evaluation_evidence(
                       job_id, chunk_id, dimension, retrieval_score, rank, retrieved_at
                       ) VALUES (?, ?, ?, ?, ?, ?)""",
                    [
                        (bundle.job_id, item.chunk_id, dimension, item.score, rank, now)
                        for rank, item in enumerate(evidence, start=1)
                    ],
                )

    def latest_evidence(self, job_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT evidence_json FROM knowledge_retrieval_runs WHERE job_id=? ORDER BY id DESC LIMIT 1",
                (job_id,),
            ).fetchone()
        return json.loads(row["evidence_json"]) if row else None
