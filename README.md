# Lattice SDK for Python

> **Stop manually configuring proxies. Use the official Lattice SDK to secure your AI pipeline in 1 line of code.**

[![Security & Quality](https://github.com/Karcsihack/lattice-python-sdk/actions/workflows/security.yml/badge.svg)](https://github.com/Karcsihack/lattice-python-sdk/actions/workflows/security.yml)
[![PyPI version](https://img.shields.io/pypi/v/lattice-sdk.svg)](https://pypi.org/project/lattice-sdk/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is Lattice SDK?

Lattice SDK is a **drop-in replacement** for the official `openai` Python library.  
Every call you make is automatically routed through the **[Lattice Privacy Proxy](https://github.com/Karcsihack/lattice-proxy)** — an open-source Go service that anonymizes PII _before_ your data ever reaches OpenAI or any other external LLM provider.

| Without Lattice SDK             | With Lattice SDK                         |
| ------------------------------- | ---------------------------------------- |
| Data sent raw to OpenAI         | PII anonymized at the network layer      |
| No audit trail                  | Full prompt & completion logging         |
| Manual proxy configuration      | Zero-config, 1-line migration            |
| GDPR compliance is your problem | GDPR / HIPAA / SOC 2 enforced by default |

---

## The Lattice Suite

This SDK is the fourth pillar of the Lattice ecosystem:

| Repository                                                           | Role                             |
| -------------------------------------------------------------------- | -------------------------------- |
| [lattice-proxy](https://github.com/Karcsihack/lattice-proxy)         | Privacy proxy server (Go)        |
| [lattice-automate](https://github.com/Karcsihack/lattice-automate)   | AI agent orchestration (Python)  |
| [lattice-dashboard](https://github.com/Karcsihack/lattice-dashboard) | Monitoring & control UI          |
| **lattice-python-sdk**                                               | **Developer SDK — you are here** |

---

## Installation

```bash
pip install lattice-sdk
```

---

## Quick Start

```python
# Before (unsafe — raw data reaches OpenAI)
# from openai import OpenAI
# client = OpenAI()

# After (1-line migration — Lattice handles everything)
from lattice_sdk import LatticeOpenAI

client = LatticeOpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarise this contract."}],
)

print(response.choices[0].message.content)
```

That single import change routes every request through the Lattice Proxy.  
No other code modifications required.

---

## Configuration

| Environment Variable | Default                            | Description                    |
| -------------------- | ---------------------------------- | ------------------------------ |
| `LATTICE_PROXY_URL`  | `http://localhost:8080/v1`         | URL of the Lattice Proxy       |
| `LATTICE_API_KEY`    | _(falls back to `OPENAI_API_KEY`)_ | API key forwarded to the proxy |

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

---

## Telemetry

Measure latency and verify that the proxy anonymized each request:

```python
from lattice_sdk import LatticeOpenAI, LatencyTracker

client  = LatticeOpenAI()
tracker = LatencyTracker()

with tracker.measure():
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}],
    )

report = tracker.build_report(response.headers)
print(report)
```

Sample output:

```
[LATTICE] ┌ Original Text  : Hello, I'm John Smith. My ID is 12345678Z and my email is john@email.com
[LATTICE] └ Text to Cloud  : Hello, I'm [USER_1]. My ID is [ID_NUMBER_2] and my email is [EMAIL_3]
[LATTICE] ✓ Completed      | entities=3 | latency_anon=91ms | latency_total=308ms
```

> No real PII ever reaches the cloud. The upstream API only sees tokens.

The telemetry module reads the following headers injected by the Lattice Proxy:

| Header                       | Example value            | Meaning                                      |
| ---------------------------- | ------------------------ | -------------------------------------------- |
| `X-Lattice-Anonymized`       | `true`                   | PII was detected and anonymized              |
| `X-Lattice-Redacted-Fields`  | `email, ssn`             | Comma-separated list of redacted field types |
| `X-Lattice-Entity-Count`     | `3`                      | Number of PII entities found                 |
| `X-Lattice-Anon-Latency-Ms`  | `91`                     | Time spent on anonymization (ms)             |
| `X-Lattice-Proxy-Latency-Ms` | `18`                     | Total proxy-side processing time (ms)        |
| `X-Lattice-Original-Text`    | `Hello, I'm John...`     | Prompt snippet before anonymization          |
| `X-Lattice-Anonymized-Text`  | `Hello, I'm [USER_1]...` | Prompt snippet sent to the upstream LLM      |

---

## Runtime Proxy Override

Override the proxy URL per-client instance — useful in multi-tenant or CI/CD setups:

```python
staging_client = LatticeOpenAI(proxy_url="https://staging-proxy.internal/v1")
```

---

## How It Works

```
Your Application
      │
      ▼
LatticeOpenAI          ← forces base_url → Lattice Proxy
      │
      ▼
Lattice Proxy (Go)     ← scans & anonymizes PII, logs audit trail
      │
      ▼
OpenAI / any LLM API   ← receives clean, anonymized prompts
```

The `LatticeOpenAI` class inherits from `openai.OpenAI` and overrides `base_url` at construction time.  
Because OpenAI's SDK uses `base_url` for every HTTP call, **no request can bypass the proxy** — even if calling internal methods directly.

---

## Security

- The SDK never reads or stores API keys beyond forwarding them to the proxy.
- `LATTICE_PROXY_URL` is validated syntactically on startup; malformed URLs raise `LatticeConfigurationError` before any network call is made.
- All HTTP connections respect the `ssl_context` and `http_client` arguments accepted by `openai.OpenAI`.

---

## Contributing

```bash
git clone https://github.com/Karcsihack/lattice-python-sdk
cd lattice-python-sdk
pip install -e ".[dev]"
pytest
```

---

## License

MIT © [Karcsihack](https://github.com/Karcsihack)
