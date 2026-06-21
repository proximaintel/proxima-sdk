"""
Proxima SDK — Platform Context

The single entry point injected into every toolbox tool call.
Contains everything the toolbox needs to interact with the platform.

Usage:
    from proxima_sdk import PlatformContext

    def my_tool(params: dict, ctx: PlatformContext) -> dict:
        data = ctx.knowledge.read("invoices-gold")
        ctx.governance.log_action("validated_invoice", {"id": params["invoice_id"]})
        return {"result": "pass"}
"""

from typing import Optional
from .knowledge import KnowledgeClient


class GovernanceClient:
    """Log actions and events to the platform governance system."""

    def __init__(self, gateway_url: str, agent_id: str):
        self._gateway_url = gateway_url
        self._agent_id = agent_id

    def log_action(self, action: str, detail: dict | None = None):
        """Log a toolbox action to governance (async fire-and-forget)."""
        import httpx
        try:
            httpx.post(
                f"{self._gateway_url}/governance/logs",
                json={"agent_id": self._agent_id, "type": "action", "action": action, "detail": detail or {}},
                timeout=5.0,
            )
        except Exception:
            pass  # Non-blocking — governance logging should never break tool execution


class SecretsClient:
    """Resolve secrets from the platform secret store."""

    def __init__(self, gateway_url: str):
        self._gateway_url = gateway_url

    def resolve(self, name: str) -> str:
        """Resolve a secret value by name."""
        import httpx
        from .exceptions import SecretNotFoundError, ConnectionFailedError
        try:
            res = httpx.post(f"{self._gateway_url}/internal/secrets/resolve", json={"name": name}, timeout=5.0)
            if res.status_code == 200:
                return res.json().get("value", "")
            elif res.status_code == 404:
                raise SecretNotFoundError(name)
            return ""
        except httpx.ConnectError:
            raise ConnectionFailedError("Gateway", self._gateway_url)


class PlatformContext:
    """
    Injected into every tool call. Provides access to all platform services.

    Constructed by the gateway from the agent's config and passed to the toolbox
    in the request payload under the `_context` key.
    """

    def __init__(self, config: dict):
        """
        Args:
            config: The _context dict injected by the gateway into tool call payloads.
                {
                    "gateway_url": "https://gateway.example.com",
                    "agent_id": "invoice-intelligence",
                    "knowledge_bases": ["finance-kb"],
                    "sources": [...],
                    "token": "<_context HMAC token for dev mode>",
                    "identity": {
                        "client_id": "<agent SP client_id>",
                        "client_secret": "<agent SP secret>",
                        "tenant_id": "<IdP tenant>",
                        "audience": "api://<gateway app id>"
                    }
                }
        """
        self._config = config
        self._knowledge: Optional[KnowledgeClient] = None
        self._governance: Optional[GovernanceClient] = None
        self._secrets: Optional[SecretsClient] = None

    @property
    def knowledge(self) -> KnowledgeClient:
        """Access enterprise data through the gateway."""
        if self._knowledge is None:
            identity = self._config.get("identity", {})
            self._knowledge = KnowledgeClient(
                gateway_url=self._config.get("gateway_url", "http://localhost:9000"),
                knowledge_bases=self._config.get("knowledge_bases", []),
                sources=self._config.get("sources", []),
                token=self._config.get("token", ""),
                client_id=identity.get("client_id", ""),
                client_secret=identity.get("client_secret", ""),
                tenant_id=identity.get("tenant_id", ""),
                audience=identity.get("audience", ""),
            )
        return self._knowledge

    @property
    def governance(self) -> GovernanceClient:
        """Log actions to the platform governance system."""
        if self._governance is None:
            self._governance = GovernanceClient(
                gateway_url=self._config.get("gateway_url", "http://localhost:9000"),
                agent_id=self._config.get("agent_id", ""),
            )
        return self._governance

    @property
    def secrets(self) -> SecretsClient:
        """Resolve secrets from the platform secret store."""
        if self._secrets is None:
            self._secrets = SecretsClient(
                gateway_url=self._config.get("gateway_url", "http://localhost:9000"),
            )
        return self._secrets

    @property
    def agent_id(self) -> str:
        return self._config.get("agent_id", "")

    def close(self):
        if self._knowledge:
            self._knowledge.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
