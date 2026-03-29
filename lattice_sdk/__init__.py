"""
Lattice SDK — The only secure way to use LLMs in Enterprise environments.

Drop-in replacement for the official OpenAI client that routes every request
through the Lattice Privacy Proxy, ensuring PII anonymization, audit logging,
and compliance before any data reaches an external AI provider.

Usage:
    from lattice_sdk import LatticeOpenAI

    client = LatticeOpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}],
    )
"""

from lattice_sdk.main import LatticeOpenAI
from lattice_sdk.telemetry import LatencyTracker, validate_anonymization

__version__ = "0.1.0"
__all__ = ["LatticeOpenAI", "LatencyTracker", "validate_anonymization"]
