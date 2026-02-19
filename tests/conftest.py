"""Shared fixtures for Euxis Publisher tests."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_FILE = PROJECT_ROOT / "data" / "meta.yaml"


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def has_private_content(project_root):
    """Whether a private content pack is present in this checkout."""
    return (project_root / "data" / "meta.yaml").exists()


@pytest.fixture(scope="session")
def meta(has_private_content):
    """Load and return the document manifest when available."""
    if not has_private_content:
        return None
    import yaml
    with open(META_FILE) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def documents(meta):
    """Return the documents dict from meta.yaml when available."""
    if not meta:
        return {}
    return meta.get("documents", {})
