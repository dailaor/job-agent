"""Local community job-intelligence ingestion and retrieval."""

from .models import EvidenceBundle, PostDocument, RetrievedEvidence
from .service import KnowledgeService

__all__ = ["EvidenceBundle", "KnowledgeService", "PostDocument", "RetrievedEvidence"]
