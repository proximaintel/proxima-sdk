"""
Proxima SDK — Testing Utilities

Mock clients for unit testing toolbox code without the full platform stack.

Usage:
    from proxima_sdk.testing import mock_context
    import pandas as pd

    def test_validate_invoice():
        ctx = mock_context(sources={
            "invoices-gold": pd.DataFrame([{"invoice_id": "INV-001", "amount": 1000}]),
            "vendors-gold": pd.DataFrame([{"vendor_id": "V-001", "name": "Acme"}]),
        })
        result = validate_invoice({"invoice_id": "INV-001"}, ctx)
        assert result["validation"] == "pass"
"""

from typing import Optional
import pandas as pd
from .types import SearchResult, SearchResults, Citation
from .context import PlatformContext


class MockKnowledgeClient:
    """Mock knowledge client for testing. Returns pre-loaded DataFrames."""

    def __init__(self, sources: dict[str, pd.DataFrame] | None = None, search_results: dict[str, list[dict]] | None = None):
        self._sources = sources or {}
        self._search_results = search_results or {}

    def read(self, source_id: str, use_cache: bool = True) -> pd.DataFrame:
        if source_id not in self._sources:
            from .exceptions import SourceNotFoundError
            raise SourceNotFoundError(source_id)
        return self._sources[source_id]

    def search(self, source_id: str, query: str, top_k: int = 5) -> SearchResults:
        results = self._search_results.get(source_id, [])
        return SearchResults(
            results=[SearchResult(content=r.get("content", ""), citation=Citation(source=source_id, title=r.get("title", "")), score=r.get("score", 0.9)) for r in results[:top_k]],
            query=query,
            sources_queried=1,
            duration_ms=1,
        )

    @property
    def available_sources(self) -> list[str]:
        return list(self._sources.keys())

    def clear_cache(self):
        pass

    def close(self):
        pass


class MockGovernanceClient:
    """Mock governance client — records actions for assertion."""

    def __init__(self):
        self.actions: list[dict] = []

    def log_action(self, action: str, detail: dict | None = None):
        self.actions.append({"action": action, "detail": detail or {}})


class MockSecretsClient:
    """Mock secrets client — returns pre-configured values."""

    def __init__(self, secrets: dict[str, str] | None = None):
        self._secrets = secrets or {}

    def resolve(self, name: str) -> str:
        return self._secrets.get(name, "")


class MockPlatformContext(PlatformContext):
    """Mock platform context for testing."""

    def __init__(self, sources: dict[str, pd.DataFrame] | None = None, search_results: dict[str, list[dict]] | None = None, secrets: dict[str, str] | None = None):
        super().__init__({"agent_id": "test-agent", "knowledge_service_url": "", "gateway_url": "", "sources": []})
        self._knowledge = MockKnowledgeClient(sources=sources, search_results=search_results)
        self._governance = MockGovernanceClient()
        self._secrets = MockSecretsClient(secrets=secrets)


def mock_context(sources: dict[str, pd.DataFrame] | None = None, search_results: dict[str, list[dict]] | None = None, secrets: dict[str, str] | None = None) -> MockPlatformContext:
    """Create a mock PlatformContext for unit testing."""
    return MockPlatformContext(sources=sources, search_results=search_results, secrets=secrets)
