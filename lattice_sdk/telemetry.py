"""
lattice_sdk/telemetry.py

Lightweight telemetry utilities for the Lattice SDK.

Measures end-to-end latency of proxy-routed LLM calls and validates that the
Lattice Proxy has correctly anonymized the request by inspecting the response
headers returned by the Go proxy server.

These utilities are intentionally minimal — no external dependencies, no
background threads, no persistent connections to a metrics backend.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Mapping

# ---------------------------------------------------------------------------
# Header constants (must match the Go proxy implementation)
# ---------------------------------------------------------------------------

# Set by the proxy to "true" when PII was detected and anonymized.
_HEADER_ANONYMIZED       = "X-Lattice-Anonymized"
# Set by the proxy with a short description of what was redacted.
_HEADER_REDACTED_FIELDS  = "X-Lattice-Redacted-Fields"
# Set by the proxy with its own processing time (optional).
_HEADER_PROXY_LATENCY_MS = "X-Lattice-Proxy-Latency-Ms"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TelemetryReport:
    """
    A structured summary of a single Lattice-proxied LLM call.

    Attributes:
        total_latency_ms:    Wall-clock time from request start to response
                             end, measured client-side (milliseconds).
        proxy_latency_ms:    Processing time reported by the Lattice Proxy
                             itself, if the header is present (milliseconds).
                             ``None`` when the header is absent.
        anonymized:          ``True`` when the proxy confirmed PII was handled.
        redacted_fields:     List of field names the proxy anonymized, e.g.
                             ``["email", "phone_number"]``.  Empty list when
                             no fields were redacted or the header is absent.
        raw_headers:         The full response headers for custom inspection.
    """

    total_latency_ms:    float
    proxy_latency_ms:    float | None
    anonymized:          bool
    redacted_fields:     list[str]
    raw_headers:         dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [
            "┌─ Lattice Telemetry Report ─────────────────────────────┐",
            f"│  Total latency   : {self.total_latency_ms:>8.1f} ms (client-side)       │",
        ]
        if self.proxy_latency_ms is not None:
            lines.append(
                f"│  Proxy latency   : {self.proxy_latency_ms:>8.1f} ms (server-side)       │"
            )
        anonymized_str = "✓ YES" if self.anonymized else "✗ NO"
        lines.append(
            f"│  PII anonymized  :   {anonymized_str:<36}│"
        )
        if self.redacted_fields:
            fields_str = ", ".join(self.redacted_fields)
            lines.append(
                f"│  Redacted fields : {fields_str:<38}│"
            )
        lines.append(
            "└────────────────────────────────────────────────────────┘"
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Latency tracker
# ---------------------------------------------------------------------------

class LatencyTracker:
    """
    Context-manager that measures wall-clock latency and inspects proxy headers.

    Usage::

        tracker = LatencyTracker()
        with tracker.measure():
            response = client.chat.completions.create(...)

        report = tracker.build_report(response.headers)
        print(report)
    """

    def __init__(self) -> None:
        self._start: float | None = None
        self._elapsed_ms: float   = 0.0

    @contextmanager
    def measure(self) -> Generator[None, None, None]:
        """Time the block and store elapsed milliseconds."""
        self._start = time.perf_counter()
        try:
            yield
        finally:
            self._elapsed_ms = (time.perf_counter() - self._start) * 1_000

    @property
    def elapsed_ms(self) -> float:
        """Milliseconds elapsed during the last ``measure()`` block."""
        return self._elapsed_ms

    def build_report(
        self,
        headers: Mapping[str, str] | None = None,
    ) -> TelemetryReport:
        """
        Build a :class:`TelemetryReport` from the measured latency and the
        proxy-injected response headers.

        Args:
            headers: HTTP response headers from the OpenAI-compatible response.
                     Pass ``None`` (or omit) when headers are unavailable.

        Returns:
            A :class:`TelemetryReport` instance ready for logging or display.
        """
        headers = dict(headers) if headers else {}

        # Parse anonymization status.
        anonymized = headers.get(_HEADER_ANONYMIZED, "").lower() == "true"

        # Parse redacted field list (comma-separated).
        raw_fields = headers.get(_HEADER_REDACTED_FIELDS, "")
        redacted_fields = (
            [f.strip() for f in raw_fields.split(",") if f.strip()]
            if raw_fields
            else []
        )

        # Parse optional proxy-side latency.
        proxy_latency_ms: float | None = None
        raw_proxy_latency = headers.get(_HEADER_PROXY_LATENCY_MS)
        if raw_proxy_latency:
            try:
                proxy_latency_ms = float(raw_proxy_latency)
            except ValueError:
                pass

        return TelemetryReport(
            total_latency_ms=self._elapsed_ms,
            proxy_latency_ms=proxy_latency_ms,
            anonymized=anonymized,
            redacted_fields=redacted_fields,
            raw_headers=headers,
        )


# ---------------------------------------------------------------------------
# Standalone helper
# ---------------------------------------------------------------------------

def validate_anonymization(headers: Mapping[str, str]) -> bool:
    """
    Return ``True`` when the Lattice Proxy confirms anonymization occurred.

    This is a convenience function for callers that only need a boolean check
    without building a full :class:`TelemetryReport`.

    Args:
        headers: HTTP response headers from a Lattice-proxied response.

    Example::

        response = client.chat.completions.create(...)
        if not validate_anonymization(response.headers):
            raise RuntimeError("Proxy did not confirm PII anonymization!")
    """
    return headers.get(_HEADER_ANONYMIZED, "").lower() == "true"
