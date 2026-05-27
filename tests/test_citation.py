# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Validate CITATION.cff shape.

Minimum-viable structural check against CFF 1.2.0
(https://github.com/citation-file-format/citation-file-format/blob/main/schema-guide.md).
We don't pull in `cffconvert` as a dependency: the few required
fields and the author-block shape are easy to check directly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CFF_PATH = ROOT / "CITATION.cff"

CFF_VERSION_PATTERN = re.compile(r"^1\.2\.\d+$")
ORCID_URI_PATTERN = re.compile(r"^https://orcid\.org/[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")


@pytest.fixture(scope="module")
def cff() -> dict:
    assert CFF_PATH.exists(), f"CITATION.cff not found at {CFF_PATH}"
    return yaml.safe_load(CFF_PATH.read_text(encoding="utf-8"))


def test_citation_cff_parses(cff: dict):
    assert isinstance(cff, dict)


def test_citation_cff_required_fields(cff: dict):
    for key in ("cff-version", "message", "title", "authors", "type"):
        assert key in cff, f"CITATION.cff missing required key: {key}"


def test_citation_cff_version_is_1_2_x(cff: dict):
    assert CFF_VERSION_PATTERN.match(cff["cff-version"]), (
        f"Unexpected cff-version: {cff['cff-version']!r}"
    )


def test_citation_cff_authors_have_names(cff: dict):
    assert cff["authors"], "CITATION.cff has no authors"
    for author in cff["authors"]:
        assert "family-names" in author or "name" in author, (
            f"Author entry needs `family-names` or `name`: {author}"
        )


def test_citation_cff_orcid_well_formed_if_present(cff: dict):
    for author in cff["authors"]:
        if "orcid" in author:
            assert ORCID_URI_PATTERN.match(author["orcid"]), (
                f"Author ORCID is malformed: {author['orcid']!r}"
            )


def test_citation_cff_type_is_software(cff: dict):
    # The engine is published as software; if we later split it
    # into a dataset + software pair, relax this.
    assert cff["type"] == "software", f"Expected type=software, got {cff['type']!r}"


def test_citation_cff_repository_code_is_https_github(cff: dict):
    # Optional field, but if present must point at the canonical repo.
    if "repository-code" in cff:
        assert cff["repository-code"].startswith("https://github.com/"), (
            f"repository-code should be an HTTPS GitHub URL: {cff['repository-code']!r}"
        )
