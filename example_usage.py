"""
example_usage.py

Shows how to migrate from the official OpenAI client to Lattice SDK
in a single line of code.

Run:
    # 1. Start the Lattice Proxy (Go binary or Docker container)
    # 2. Copy .env.example to .env and fill in your key
    # 3. python example_usage.py
"""

# ---------------------------------------------------------------------------
# 0. Load environment variables from a local .env file (optional helper)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is not installed — rely on OS-level env vars.

# ---------------------------------------------------------------------------
# BEFORE (standard OpenAI — no privacy layer, data leaves raw)
# ---------------------------------------------------------------------------
# from openai import OpenAI
# client = OpenAI()

# ---------------------------------------------------------------------------
# AFTER  (Lattice SDK — 1-line change, full Enterprise privacy layer active)
# ---------------------------------------------------------------------------
from lattice_sdk import LatticeOpenAI, LatencyTracker

client = LatticeOpenAI()
# That's it. Every call below is now:
#   1. Routed through the Lattice Proxy at LATTICE_PROXY_URL.
#   2. Scanned and anonymized for PII before leaving your perimeter.
#   3. Logged with a full audit trail.


# ---------------------------------------------------------------------------
# Example 1 — Basic chat completion (identical API to openai.OpenAI)
# ---------------------------------------------------------------------------
print("\n── Example 1: Basic completion ─────────────────────────────────\n")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. "
                "Do NOT include any personal information in your answers."
            ),
        },
        {
            "role": "user",
            "content": "Explain the concept of differential privacy in 2 sentences.",
        },
    ],
    max_tokens=150,
)

print("Model reply:", response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Example 2 — Completion with telemetry (latency + anonymization check)
# ---------------------------------------------------------------------------
print("\n── Example 2: Telemetry-aware completion ───────────────────────\n")

tracker = LatencyTracker()

with tracker.measure():
    response2 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": (
                    "Summarise this employee record: "
                    "John Doe, john.doe@example.com, SSN 123-45-6789, "
                    "salary $95,000."
                ),
            }
        ],
        max_tokens=100,
    )

# The Lattice Proxy injects X-Lattice-* headers into every response.
# httpx exposes them via response.headers; the openai SDK surfaces them
# through the raw_response attribute when available.
proxy_headers = getattr(response2, "headers", {})
report = tracker.build_report(proxy_headers)

print("Model reply:", response2.choices[0].message.content)
print()
print(report)


# ---------------------------------------------------------------------------
# Example 3 — Runtime proxy override (useful in CI/CD or multi-tenant setups)
# ---------------------------------------------------------------------------
print("\n── Example 3: Per-instance proxy override ──────────────────────\n")

staging_client = LatticeOpenAI(proxy_url="http://staging-proxy.internal:8080/v1")

response3 = staging_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Ping!"}],
    max_tokens=10,
)

print(f"Staging proxy URL  : {staging_client.proxy_url}")
print(f"Staging reply      : {response3.choices[0].message.content}")
