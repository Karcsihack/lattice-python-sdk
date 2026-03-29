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
_HEADER_ANONYMIZED        = "X-Lattice-Anonymized"
# Set by the proxy with a short description of what was redacted.
_HEADER_REDACTED_FIELDS   = "X-Lattice-Redacted-Fields"
# Set by the proxy with its own processing time (optional).
_HEADER_PROXY_LATENCY_MS  = "X-Lattice-Proxy-Latency-Ms"
# Set by the proxy with the anonymization latency in ms (optional).
_HEADER_ANON_LATENCY_MS   = "X-Lattice-Anon-Latency-Ms"
# Set by the proxy with the number of anonymized entities found.
_HEADER_ENTITY_COUNT      = "X-Lattice-Entity-Count"
# Set by the proxy with the original (pre-anonymization) prompt snippet.
_HEADER_ORIGINAL_TEXT     = "X-Lattice-Original-Text"
# Set by the proxy with the anonymized prompt that was sent upstream.
_HEADER_ANONYMIZED_TEXT   = "X-Lattice-Anonymized-Text"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TelemetryReport:
    """
    A structured summary of a single Lattice-proxied LLM call.

    Attributes:
        total_latency_ms:  Wall-clock time from request start to response
                           end, measured client-side (milliseconds).
        proxy_latency_ms:  Processing time reported by the Lattice Proxy
                           itself, if the header is present (milliseconds).
                           ``None`` when the header is absent.
        anon_latency_ms:   Time the proxy spent on anonymization (ms).
                           ``None`` when the header is absent.
        anonymized:        ``True`` when the proxy confirmed PII was handled.
        entity_count:      Number of PII entities anonymized. ``None`` if
                           the header is absent.
        redacted_fields:   List of field names the proxy anonymized, e.g.
                           ``["email", "phone_number"]``.  Empty list when
                           no fields were redacted or the header is absent.
        original_text:     Prompt snippet before anonymization (may be
                           truncated by the proxy). ``None`` if not provided.
        anonymized_text:   Prompt snippet after anonymization (what the
                           upstream LLM actually received). ``None`` if not
                           provided.
        raw_headers:       The full response headers for custom inspection.
    """

    total_latency_ms:  float
    proxy_latency_ms:  float | None
    anon_latency_ms:   float | None
    anonymized:        bool
    entity_count:      int | None
    redacted_fields:   list[str]
    original_text:     str | None
    anonymized_text:   str | None
    raw_headers:       dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        lines: list[str] = []

        # ── Text comparison block (only when proxy supplies both snippets) ──
        if self.original_text:
            lines.append(
                f"[LATTICE] \u250c Original Text  : {self.original_text}"
            )
        if self.anonymized_text:
            lines.append(
                f"[LATTICE] \u2514 Text to Cloud  : {self.anonymized_text}"
            )

        # ── Summary line ────────────────────────────────────────────────────
        parts: list[str] = []
        if self.entity_count is not None:
            parts.append(f"entities={self.entity_count}")
        if self.anon_latency_ms is not None:
            parts.append(f"latency_anon={self.anon_latency_ms:.0f}ms")
        parts.append(f"latency_total={self.total_latency_ms:.0f}ms")

        status = "\u2713 Completed" if self.anonymized else "\u2717 Not anonymized"
        lines.append(f"[LATTICE] {status:<14} | {' | '.join(parts)}")

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

        # Parse anonymization-specific latency.
        anon_latency_ms: float | None = None
        raw_anon_latency = headers.get(_HEADER_ANON_LATENCY_MS)
        if raw_anon_latency:
            try:
                anon_latency_ms = float(raw_anon_latency)
            except ValueError:
                pass

        # Parse entity count.
        entity_count: int | None = None
        raw_entity_count = headers.get(_HEADER_ENTITY_COUNT)
        if raw_entity_count:
            try:
                entity_count = int(raw_entity_count)
            except ValueError:
                pass

        # Parse text snippets.
        original_text   = headers.get(_HEADER_ORIGINAL_TEXT)   or None
        anonymized_text = headers.get(_HEADER_ANONYMIZED_TEXT) or None

        return TelemetryReport(
            total_latency_ms=self._elapsed_ms,
            proxy_latency_ms=proxy_latency_ms,
            anon_latency_ms=anon_latency_ms,
            anonymized=anonymized,
            entity_count=entity_count,
            redacted_fields=redacted_fields,
            original_text=original_text,
            anonymized_text=anonymized_text,
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
