"""
Proxima SDK

The official SDK for building toolboxes on the Proxima Intelligence platform.
Provides typed access to Knowledge, Governance, and Secrets services.

Quick Start:
    from proxima_sdk import PlatformContext

    def my_tool(params: dict, ctx: PlatformContext) -> dict:
        data = ctx.knowledge.read("invoices-gold")
        ctx.governance.log_action("processed_invoice")
        return {"count": len(data)}

Testing:
    from proxima_sdk.testing import mock_context
    import pandas as pd

    ctx = mock_context(sources={"invoices-gold": pd.DataFrame([...])})
    result = my_tool({"id": "INV-001"}, ctx)
"""

from .context import PlatformContext
from .knowledge import KnowledgeClient
from .exceptions import (
    ProximaError,
    SourceNotFoundError,
    ConnectionFailedError,
    QueryFailedError,
    SecretNotFoundError,
    PermissionDeniedError,
)
from .types import SearchResult, SearchResults, Citation, QueryMetadata

__version__ = "1.0.1"

__all__ = [
    "PlatformContext",
    "KnowledgeClient",
    "ProximaError",
    "SourceNotFoundError",
    "ConnectionFailedError",
    "QueryFailedError",
    "SecretNotFoundError",
    "PermissionDeniedError",
    "SearchResult",
    "SearchResults",
    "Citation",
    "QueryMetadata",
]
