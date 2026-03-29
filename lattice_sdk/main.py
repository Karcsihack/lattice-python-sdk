"""
lattice_sdk/main.py

LatticeOpenAI — Drop-in replacement for `openai.OpenAI`.

The Lattice SDK is the ONLY secure way to use LLMs in Enterprise environments.
Every request is intercepted here and forwarded to the Lattice Privacy Proxy
before it ever reaches an external AI provider. This guarantees:

  • PII anonymization enforced at the network layer.
  • Full audit trail of every prompt and completion.
  • Zero-trust compliance with GDPR, HIPAA, and SOC 2.

Architecture:
    Developer App ──► LatticeOpenAI (this file)
                           │
                           ▼
                  Lattice Proxy (Go)          ← strips / anonymizes PII
                           │
                           ▼
                  OpenAI / any LLM API
"""

from __future__ import annotations

import os
import sys
from typing import Any
from urllib.parse import urlparse

import openai

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_PROXY_URL = "http://localhost:8080/v1"
_ENV_PROXY_URL = "LATTICE_PROXY_URL"
_ENV_API_KEY   = "LATTICE_API_KEY"   # Optional override for the OpenAI key


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_proxy_url() -> str:
    """
    Return the proxy base URL in priority order:

    1. ``LATTICE_PROXY_URL`` environment variable.
    2. Hard-coded default (``http://localhost:8080/v1``).

    Raises ``LatticeConfigurationError`` when the resolved URL is
    syntactically invalid so developers get a clear, actionable message.
    """
    url = os.environ.get(_ENV_PROXY_URL, _DEFAULT_PROXY_URL).rstrip("/")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise LatticeConfigurationError(
            f"The resolved Lattice proxy URL '{url}' is not valid.\n"
            "Set a valid URL via the LATTICE_PROXY_URL environment variable.\n"
            "Example:\n"
            "    export LATTICE_PROXY_URL=https://proxy.your-company.com/v1\n"
            "\n"
            "To protect your users' privacy, all requests must pass through\n"
            "the Lattice Proxy. Direct calls to external LLM providers are\n"
            "NOT allowed in Lattice-secured environments."
        )

    return url


def _resolve_api_key() -> str:
    """
    Resolve the API key that will be forwarded to the proxy.

    Priority:
    1. ``LATTICE_API_KEY`` — key scoped to the Lattice deployment.
    2. ``OPENAI_API_KEY``  — fallback for zero-config migrations.

    Raises ``LatticeConfigurationError`` when no key is found.
    """
    key = os.environ.get(_ENV_API_KEY) or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise LatticeConfigurationError(
            "No API key found. Set either LATTICE_API_KEY or OPENAI_API_KEY.\n"
            "\n"
            "The Lattice Proxy validates this key to enforce per-team rate\n"
            "limits and audit logging. Without it, requests will be rejected."
        )
    return key


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class LatticeConfigurationError(RuntimeError):
    """Raised when the SDK cannot start due to missing or invalid configuration."""

    def __str__(self) -> str:
        banner = "\n" + "═" * 60 + "\n"
        return (
            f"{banner}"
            "  Lattice SDK — Configuration Error\n"
            f"{banner}"
            f"{super().__str__()}\n"
            f"{banner}"
            "  Docs: https://github.com/your-org/lattice-python-sdk\n"
            f"{'═' * 60}\n"
        )


# ---------------------------------------------------------------------------
# Main public class
# ---------------------------------------------------------------------------

class LatticeOpenAI(openai.OpenAI):
    """
    Enterprise-grade drop-in replacement for ``openai.OpenAI``.

    Stop manually configuring proxies. Use the official Lattice SDK to secure
    your AI pipeline in 1 line of code.

    All keyword arguments accepted by ``openai.OpenAI`` are forwarded, except
    ``base_url`` which is always overridden by the Lattice proxy URL to
    guarantee that no request bypasses the privacy layer.

    Example::

        # Before (insecure — data leaves your perimeter unfiltered)
        # from openai import OpenAI
        # client = OpenAI()

        # After (secure — every request is anonymized by Lattice)
        from lattice_sdk import LatticeOpenAI
        client = LatticeOpenAI()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Summarise this contract."}],
        )

    Args:
        proxy_url: Override the proxy URL at runtime (optional).
                   Defaults to the ``LATTICE_PROXY_URL`` env variable or
                   ``http://localhost:8080/v1``.
        **kwargs:  Any keyword argument accepted by ``openai.OpenAI``.
    """

    def __init__(self, *, proxy_url: str | None = None, **kwargs: Any) -> None:
        # Resolve & validate configuration before touching the parent class.
        resolved_url = proxy_url or _resolve_proxy_url()
        api_key      = kwargs.pop("api_key", None) or _resolve_api_key()

        # Always force base_url to point at the Lattice proxy.
        # This is the core of the "monkey patch" — developers cannot
        # accidentally bypass the proxy even if they try to pass base_url.
        kwargs["base_url"] = resolved_url
        kwargs["api_key"]  = api_key

        super().__init__(**kwargs)

        # Store resolved values for inspection / telemetry.
        self._lattice_proxy_url: str = resolved_url

        _print_startup_banner(resolved_url)

    # ------------------------------------------------------------------
    # Property helpers
    # ------------------------------------------------------------------

    @property
    def proxy_url(self) -> str:
        """The Lattice proxy URL in use for this client instance."""
        return self._lattice_proxy_url


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

def _print_startup_banner(proxy_url: str) -> None:
    """Print a one-line confirmation so developers know the proxy is active."""
    # Use stderr so the message doesn't pollute stdout pipelines.
    print(
        f"[Lattice SDK] Privacy proxy active → {proxy_url}",
        file=sys.stderr,
    )
