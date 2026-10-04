#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Fail when the release version is restated differently anywhere.

Single source of truth: ``version`` in ``pyproject.toml``. The same string
must appear in ``CITATION.cff``, as a ``## [X.Y.Z]`` heading in
``CHANGELOG.md``, in ``glama.json`` (``version``), and in ``server.json``
(``version`` and every ``packages[].version``).

Usage: python3 scripts/verify_versions.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("pyproject.toml has no version field")
    return match.group(1)


def _changelog_versions() -> set[str]:
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        return set()
    return set(
        re.findall(
            r"^## \[(\d+\.\d+\.\d+)\]",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )


def _citation_version() -> str | None:
    path = ROOT / "CITATION.cff"
    if not path.exists():
        return None
    match = re.search(r'^version:\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def _json(name: str) -> dict | None:
    path = ROOT / name
    return (
        json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    )


def main() -> int:
    """Compare every restatement of the version and report."""
    expected = _pyproject_version()
    problems: list[str] = []
    print(f"  pyproject.toml version = {expected}")
    cff = _citation_version()
    if cff is not None:
        print(f"  CITATION.cff           = {cff}")
        if cff != expected:
            problems.append(f"CITATION.cff has {cff} != {expected}")
    changelog = _changelog_versions()
    if changelog and expected not in changelog:
        problems.append(f"CHANGELOG.md has no [{expected}] heading")
    glama = _json("glama.json")
    if glama is not None:
        print(f"  glama.json             = {glama.get('version')}")
        if glama.get("version") != expected:
            problems.append("glama.json version differs")
    server = _json("server.json")
    if server is not None:
        pkg_versions = [p.get("version") for p in server.get("packages", [])]
        print(
            f"  server.json            = {server.get('version')} (packages {pkg_versions})"
        )
        if server.get("version") != expected or any(
            v != expected for v in pkg_versions
        ):
            problems.append("server.json version differs")
    for problem in problems:
        print(f"ERROR: {problem}")
    if problems:
        return 1
    print("OK: every source agrees on", expected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
