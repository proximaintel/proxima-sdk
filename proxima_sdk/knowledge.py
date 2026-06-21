"""
Proxima SDK — Knowledge Client

The primary interface for toolboxes to access enterprise data.
All access goes through the gateway (authenticated, RBAC-enforced, governance-logged).

The toolbox NEVER calls Knowledge Service directly. It authenticates to the gateway
using the agent's service principal credentials and calls POST /knowledge/{base_id}/query.

Usage:
    from proxima_sdk import PlatformContext

    def validate_invoice(params: dict, ctx: PlatformContext) -> dict:
        results = ctx.knowledge.query("finance-kb", "overdue invoices over $50K")
        invoices = ctx.knowledge.read("invoices-gold")
        # ... business logic
"""

import os
import time
from typing import Optional

import httpx

from .types import SearchResult, SearchResults, Citation, QueryMetadata
from .exceptions import (
    SourceNotFoundError,
    ConnectionFailedError,
    QueryFailedError,
    TimeoutError as ProximaTimeoutError,
)


class KnowledgeClient:
    """
    Access enterprise data through the Proxima Gateway.

    Provides:
    - query(base_id, query) → dict (full KB query via gateway)
    - read(source_id) → pd.DataFrame (structured data via gateway)
    - search(source_id, query) → SearchResults (unstructured/vector via gateway)

    All access authenticated, RBAC-enforced, governance-logged.
    """

    def __init__(self, gateway_url: str, knowledge_bases: list[str], sources: list[dict],
                 token: str = "", client_id: str = "", client_secret: str = "",
                 tenant_id: str = "", audience: str = "", timeout: float = 30.0):
        """
        Args:
            gateway_url: Platform gateway URL (e.g., https://gateway.example.com)
            knowledge_bases: List of KB IDs this agent can access
            sources: Legacy source definitions (for backward compat with read())
            token: Pre-obtained token (dev mode / _context HMAC)
            client_id: Agent SP client ID (production - client credentials flow)
            client_secret: Agent SP client secret (production)
            tenant_id: IdP tenant ID (for token endpoint)
            audience: Gateway audience (for token scope)
            timeout: HTTP timeout in seconds
        """
        self._gateway_url = gateway_url.rstrip("/")
        self._knowledge_bases = knowledge_bases
        self._sources = {s["id"]: s for s in sources}
        self._timeout = timeout
        self._cache: dict = {}

        # Auth
        self._token = token
        self._client_id = client_id or os.getenv("PROXIMA_AGENT_CLIENT_ID", "")
        self._client_secret = client_secret or os.getenv("PROXIMA_AGENT_CLIENT_SECRET", "")
        self._tenant_id = tenant_id or os.getenv("PROXIMA_TENANT_ID", "")
        self._audience = audience or os.getenv("PROXIMA_AUDIENCE", "")
        self._token_expires_at: float = 0

    def _get_token(self) -> str:
        """Get a valid access token. Uses cached token if not expired."""
        # If we have a pre-set token (dev mode / _context), use it
        if self._token and not self._client_id:
            return self._token

        # Check if cached token is still valid (with 60s buffer)
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        # Client credentials flow
        if not self._client_id or not self._client_secret or not self._tenant_id:
            return self._token  # Fall back to whatever we have

        token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        scope = f"{self._audience}/.default" if self._audience else ""

        try:
            res = httpx.post(token_url, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": scope,
                "grant_type": "client_credentials",
            }, timeout=10.0)

            if res.status_code == 200:
                data = res.json()
                self._token = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 3600)
                return self._token
        except Exception:
            pass

        return self._token

    def _headers(self) -> dict:
        """Build request headers with auth token."""
        token = self._get_token()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def query(self, base_id: str, query: str, top_k: int = 5) -> dict:
        """
        Query a knowledge base through the gateway.

        Args:
            base_id: Knowledge base ID
            query: Natural language query
            top_k: Number of results

        Returns:
            dict with results, citations, metadata

        Raises:
            QueryFailedError: Gateway returned an error
            ConnectionFailedError: Gateway unreachable
        """
        try:
            start = time.time()
            res = httpx.post(
                f"{self._gateway_url}/knowledge/{base_id}/query",
                json={"query": query, "top_k": top_k},
                headers=self._headers(),
                timeout=self._timeout,
            )
            duration = int((time.time() - start) * 1000)

            if res.status_code == 403:
                raise QueryFailedError(base_id, "Access denied. Check role_assignments for this agent.")
            if res.status_code == 404:
                raise SourceNotFoundError(base_id)
            if res.status_code != 200:
                raise QueryFailedError(base_id, f"HTTP {res.status_code}: {res.text[:200]}")

            return res.json()

        except httpx.ConnectError:
            raise ConnectionFailedError("Gateway", self._gateway_url, "Gateway unreachable.")
        except httpx.TimeoutException:
            raise ProximaTimeoutError("Gateway", self._timeout)

    def read(self, source_id: str, use_cache: bool = True):
        """
        Read structured data from a knowledge source.
        Routes through gateway /knowledge/{base_id}/query.

        Args:
            source_id: ID of the registered knowledge source
            use_cache: If True, returns cached data within same tool execution

        Returns:
            pd.DataFrame with the source data (requires pandas)
        """
        import pandas as pd

        if use_cache and source_id in self._cache:
            return self._cache[source_id]

        # Find which KB contains this source
        # For now, query the first available KB with the source name
        base_id = self._knowledge_bases[0] if self._knowledge_bases else "default"

        result = self.query(base_id, f"read all data from {source_id}", top_k=1)

        # Parse results into DataFrame
        for r in result.get("results", []):
            content = r.get("content", "")
            if "rows" in content and "|" in content:
                # Try to parse markdown table
                try:
                    lines = [l.strip() for l in content.split("\n") if l.strip() and "|" in l]
                    if len(lines) >= 3:
                        headers = [h.strip() for h in lines[0].split("|") if h.strip()]
                        rows = []
                        for line in lines[2:]:
                            if "---" in line or "..." in line:
                                continue
                            row = [c.strip() for c in line.split("|") if c.strip()]
                            if len(row) == len(headers):
                                rows.append(row)
                        if rows:
                            df = pd.DataFrame(rows, columns=headers)
                            if use_cache:
                                self._cache[source_id] = df
                            return df
                except Exception:
                    pass

        # Fallback: return empty DataFrame
        df = pd.DataFrame()
        if use_cache:
            self._cache[source_id] = df
        return df

    def search(self, source_id: str, query: str, top_k: int = 5) -> SearchResults:
        """
        Search knowledge via gateway.

        Args:
            source_id: Source or KB ID to search
            query: Natural language search query
            top_k: Number of results

        Returns:
            SearchResults with content and citations
        """
        base_id = source_id if source_id in self._knowledge_bases else (self._knowledge_bases[0] if self._knowledge_bases else source_id)

        result = self.query(base_id, query, top_k=top_k)

        results = []
        for r in result.get("results", []):
            citation_data = r.get("citation", {})
            results.append(SearchResult(
                content=r.get("content", ""),
                citation=Citation(
                    source=citation_data.get("source", ""),
                    title=citation_data.get("title", ""),
                    confidence=citation_data.get("confidence", 0.0),
                    metadata=citation_data,
                ),
                score=0.0,
            ))

        return SearchResults(
            results=results,
            query=query,
            sources_queried=result.get("metadata", {}).get("sources_queried", 0),
            duration_ms=result.get("metadata", {}).get("duration_ms", 0),
        )

    @property
    def available_bases(self) -> list[str]:
        """List KB IDs available to this agent."""
        return list(self._knowledge_bases)

    @property
    def available_sources(self) -> list[str]:
        """List source IDs (legacy compat)."""
        return list(self._sources.keys())

    def clear_cache(self):
        """Clear the in-memory read cache."""
        self._cache.clear()

    def close(self):
        """No persistent client to close (stateless HTTP calls)."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
