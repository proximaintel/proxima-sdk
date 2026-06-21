"""
Proxima SDK — Types

Typed data structures for toolbox developers.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Citation:
    """Source attribution for a knowledge retrieval result."""
    source: str
    title: str = ""
    section: str = ""
    page: Optional[int] = None
    url: str = ""
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single result from a knowledge search (unstructured/vector)."""
    content: str
    citation: Citation
    score: float = 0.0


@dataclass
class SearchResults:
    """Collection of search results with metadata."""
    results: list[SearchResult]
    query: str
    sources_queried: int = 0
    duration_ms: int = 0

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self):
        return iter(self.results)

    @property
    def top(self) -> Optional[SearchResult]:
        return self.results[0] if self.results else None

    @property
    def contents(self) -> list[str]:
        return [r.content for r in self.results]


@dataclass
class QueryMetadata:
    """Metadata about a structured data query."""
    source: str
    row_count: int
    columns: list[str]
    query_executed: str = ""
    duration_ms: int = 0
    cached: bool = False
