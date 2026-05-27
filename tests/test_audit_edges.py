# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 5 edge-case tests for `euxis_publisher.cli.audit`.

Complements `tests/test_eaa.py` (Sprint 3 unit tests) by exercising
the failure / boundary paths the audit CLI exposes to CI:

  - malformed veraPDF output (no newline, no PASS/FAIL prefix)
  - empty veraPDF stdout (early-return path)
  - registry filter on a YAML missing the `documents:` block
  - registry filter on a YAML with a non-dict doc entry
  - --flavours subset honoured
  - audit() with explicit timeout propagates to subprocess
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from euxis_publisher.cli import audit as audit_mod


def _make_pdf(path: Path, content: bytes = b"%PDF-1.7\n%dummy\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# ── _verapdf: parse-failure paths ──────────────────────────────────────


def test_verapdf_classifies_non_pass_non_fail_as_error(tmp_path, monkeypatch):
    """Output like a JVM stack trace must register as ERROR, not PASS."""
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda _x: "/usr/bin/verapdf")

    def fake_run(*_args, **_kwargs):
        return mock.MagicMock(
            returncode=1,
            stdout="java.lang.NoClassDefFoundError\n",
            stderr="JVM crashed",
        )

    monkeypatch.setattr(audit_mod.subprocess, "run", fake_run)
    result = audit_mod._verapdf(pdf, "ua2")
    assert result["status"] == "ERROR"
    assert "JVM crashed" in result["error"]


def test_verapdf_classifies_empty_stdout_as_error(tmp_path, monkeypatch):
    """Empty stdout (no first line) must not crash on indexing."""
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda _x: "/usr/bin/verapdf")

    monkeypatch.setattr(
        audit_mod.subprocess,
        "run",
        lambda *a, **k: mock.MagicMock(returncode=0, stdout="", stderr=""),
    )
    result = audit_mod._verapdf(pdf, "ua2")
    assert result["status"] == "ERROR"
    assert result["line"] == ""


# ── _registry_stems: boundary YAML shapes ──────────────────────────────


def test_registry_stems_yaml_without_documents_block_returns_empty(tmp_path):
    meta = tmp_path / "meta.yaml"
    meta.write_text("author:\n  name: Solo\n", encoding="utf-8")
    assert audit_mod._registry_stems(meta) == set()


def test_registry_stems_skips_non_dict_doc_entries(tmp_path):
    """A `foo:` with no body parses as `{"foo": None}` — must not crash."""
    meta = tmp_path / "meta.yaml"
    meta.write_text(
        "documents:\n  foo:\n  bar:\n    src: src/papers/bar.tex\n",
        encoding="utf-8",
    )
    stems = audit_mod._registry_stems(meta)
    assert "foo" in stems
    assert "bar" in stems
    assert "bar" in stems  # also via src path stem


def test_registry_stems_invalid_yaml_returns_empty(tmp_path):
    """Malformed YAML must degrade to empty, not raise."""
    meta = tmp_path / "meta.yaml"
    meta.write_text("not:\n  - a:\n  -bad\nmix\n", encoding="utf-8")
    assert audit_mod._registry_stems(meta) == set()


# ── audit(): flavour subset + timeout propagation ──────────────────────


def test_audit_with_flavour_subset(tmp_path, monkeypatch):
    """--flavours ua2 must produce 1 check per PDF, not 3."""
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda _x: "/usr/bin/verapdf")
    monkeypatch.setattr(
        audit_mod.subprocess,
        "run",
        lambda *a, **k: mock.MagicMock(returncode=0, stdout="PASS\n", stderr=""),
    )
    report = audit_mod.audit([pdf], flavours=[("ua2", "PDF/UA-2", True)])
    assert report["summary"]["checks"] == 1
    assert report["summary"]["pass"] == 1
    assert len(report["flavours"]) == 1


def test_audit_timeout_propagates_to_subprocess(tmp_path, monkeypatch):
    """audit(..., timeout=42) must pass timeout=42 to subprocess.run."""
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda _x: "/usr/bin/verapdf")
    captured = {}

    def fake_run(_cmd, *_args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return mock.MagicMock(returncode=0, stdout="PASS\n", stderr="")

    monkeypatch.setattr(audit_mod.subprocess, "run", fake_run)
    audit_mod.audit([pdf], timeout=42)
    assert captured["timeout"] == 42


# ── main(): report file paths ──────────────────────────────────────────


def test_main_writes_to_custom_json_and_markdown_paths(tmp_path, monkeypatch):
    """--json and --markdown flags must override the default audit dir."""
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda _x: "/usr/bin/verapdf")
    monkeypatch.setattr(
        audit_mod.subprocess,
        "run",
        lambda *a, **k: mock.MagicMock(returncode=0, stdout="PASS\n", stderr=""),
    )
    monkeypatch.setattr(audit_mod, "DEFAULT_AUDIT_DIR", tmp_path / ".audit-default")

    custom_json = tmp_path / "out" / "rep.json"
    custom_md = tmp_path / "out" / "rep.md"
    rc = audit_mod.main(
        [
            str(pdf),
            "--all",
            "--json",
            str(custom_json),
            "--markdown",
            str(custom_md),
        ]
    )
    assert rc == 0
    assert custom_json.exists()
    assert custom_md.exists()
    report = json.loads(custom_json.read_text())
    assert report["tool"] == "euxis-audit"
    # Markdown report carries the audit header and per-PDF table.
    md = custom_md.read_text()
    assert "Euxis EAA / Accessibility Audit Report" in md
    assert "p.pdf" in md
