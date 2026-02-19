"""Shared fixtures for Publications test suite."""

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_FILE = PROJECT_ROOT / "data" / "meta.yaml"


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def meta():
    """Load and return the document manifest."""
    with open(META_FILE) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def documents(meta):
    """Return the documents dict from meta.yaml."""
    return meta.get("documents", {})
