from __future__ import annotations

from typing import Protocol

from ..models import SourceFetchResult


class KnowledgeSource(Protocol):
    id: str

    def fetch(self, url: str) -> SourceFetchResult: ...


class SourceRegistry:
    def __init__(self, sources: list[KnowledgeSource] | None = None) -> None:
        self._sources = {source.id: source for source in sources or []}

    def register(self, source: KnowledgeSource) -> None:
        if source.id in self._sources:
            raise ValueError(f"knowledge source already registered: {source.id}")
        self._sources[source.id] = source

    def get(self, source_id: str) -> KnowledgeSource | None:
        return self._sources.get(source_id)

    def catalog(self) -> list[str]:
        return sorted(self._sources)
