"""
setup.py — Build & distribution configuration for lattice-sdk.

Install locally:
    pip install .

Install in editable mode (development):
    pip install -e .

Build a wheel for distribution:
    pip install build && python -m build
"""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    # -----------------------------------------------------------------------
    # Package identity
    # -----------------------------------------------------------------------
    name="lattice-sdk",
    version="0.1.0",
    author="Lattice Team",
    author_email="sdk@lattice.dev",
    description=(
        "Stop manually configuring proxies. "
        "Use the official Lattice SDK to secure your AI pipeline in 1 line of code."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Karcsihack/lattice-python-sdk",
    project_urls={
        "Bug Tracker":    "https://github.com/Karcsihack/lattice-python-sdk/issues",
        "Documentation":  "https://docs.lattice.dev/sdk/python",
        "Lattice Proxy":  "https://github.com/Karcsihack/lattice-proxy",
    },
    license="MIT",
    # -----------------------------------------------------------------------
    # Package discovery
    # -----------------------------------------------------------------------
    packages=find_packages(exclude=["tests*", "examples*"]),
    python_requires=">=3.9",
    # -----------------------------------------------------------------------
    # Runtime dependencies
    # -----------------------------------------------------------------------
    install_requires=[
        # The SDK wraps the official OpenAI Python library.
        # We pin a minimum version to guarantee the interface we depend on.
        "openai>=1.30.0",
    ],
    extras_require={
        # Optional extras for richer telemetry export.
        "telemetry": [
            "httpx>=0.27.0",  # Already a transitive dep of openai; explicit for clarity.
        ],
        # Developer tooling.
        "dev": [
            "pytest>=8.0",
            "pytest-asyncio>=0.23",
            "respx>=0.21",      # HTTP mocking for httpx-based clients.
            "python-dotenv>=1.0",
        ],
    },
    # -----------------------------------------------------------------------
    # PyPI classifiers (https://pypi.org/classifiers/)
    # -----------------------------------------------------------------------
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "Topic :: Internet :: Proxy Servers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    # -----------------------------------------------------------------------
    # CLI entry point (optional — expose a quick health-check command)
    # -----------------------------------------------------------------------
    entry_points={
        "console_scripts": [
            "lattice-check=lattice_sdk.main:_resolve_proxy_url",
        ],
    },
    # -----------------------------------------------------------------------
    # Include non-Python files
    # -----------------------------------------------------------------------
    include_package_data=True,
)
