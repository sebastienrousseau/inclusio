"""Sprint 3: EAA / accessibility audit CLI tests.

Covers `euxis_publisher.cli.audit`:

  - argument parsing
  - registry-filtered PDF collection (default behaviour skips
    recruiter input briefs co-located in build/jobs/)
  - --all opt-out from registry filtering
  - veraPDF result classification (PASS / FAIL / SKIP / ERROR)
  - JSON + Markdown report shape
  - --strict exit-code semantics

The tests do NOT require veraPDF to be installed on the runner —
the verapdf subprocess is mocked. A separate CI job
(.github/workflows/verapdf.yml) runs the audit CLI for real against
the public-fixture documents.
"""

import json
import sys
from pathlib import Path
from unittest import mock

# Ensure the cli module is importable.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from euxis_publisher.cli import audit as audit_mod

# ── Helpers ─────────────────────────────────────────────────────────────


def _make_pdf(path, content=b"%PDF-1.7\n%dummy\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _fake_subprocess_run(pass_for=("ua2", "wt1a", "4f")):
    """Build a fake subprocess.run that returns PASS for the given flavours."""

    def runner(cmd, *args, **kwargs):
        flavour = cmd[cmd.index("--flavour") + 1]
        pdf = cmd[-1]
        verdict = "PASS" if flavour in pass_for else "FAIL"
        return mock.MagicMock(
            returncode=0,
            stdout=f"{verdict} {pdf} {flavour}\n",
            stderr="",
        )

    return runner


# ── collect_pdfs ────────────────────────────────────────────────────────


def test_collect_single_pdf(tmp_path):
    pdf = _make_pdf(tmp_path / "foo.pdf")
    out = audit_mod.collect_pdfs(pdf, tmp_path)
    assert out == [pdf.resolve()]


def test_collect_directory_skips_cache_and_audit(tmp_path):
    _make_pdf(tmp_path / "build" / "papers" / "a.pdf")
    _make_pdf(tmp_path / "build" / ".cache" / "intermediates" / "x.pdf")
    _make_pdf(tmp_path / "build" / ".audit" / "old.pdf")
    out = audit_mod.collect_pdfs(tmp_path, tmp_path)
    out_names = [p.name for p in out]
    assert "a.pdf" in out_names
    assert "x.pdf" not in out_names
    assert "old.pdf" not in out_names


def test_collect_with_registry_filter(tmp_path):
    """Registry filter keeps only PDFs whose stem is registered."""
    _make_pdf(tmp_path / "build" / "papers" / "registered.pdf")
    _make_pdf(tmp_path / "build" / "jobs" / "recruiter-brief.pdf")
    out = audit_mod.collect_pdfs(tmp_path, tmp_path, registry_stems={"registered"})
    out_names = [p.name for p in out]
    assert out_names == ["registered.pdf"]


def test_collect_empty_registry_filter_returns_all(tmp_path):
    _make_pdf(tmp_path / "a.pdf")
    _make_pdf(tmp_path / "b.pdf")
    out = audit_mod.collect_pdfs(tmp_path, tmp_path, registry_stems=set())
    assert {p.name for p in out} == {"a.pdf", "b.pdf"}


# ── _registry_stems ─────────────────────────────────────────────────────


def test_registry_stems_reads_meta(tmp_path):
    meta = tmp_path / "meta.yaml"
    meta.write_text(
        "documents:\n"
        "  foo:\n    src: src/papers/foo-paper.tex\n"
        "  bar:\n    src: src/cvs/cv.tex\n"
        "  baz:\n",
        encoding="utf-8",
    )
    stems = audit_mod._registry_stems(meta)
    assert "foo-paper" in stems
    assert "cv" in stems
    assert "foo" in stems
    assert "bar" in stems
    assert "baz" in stems


def test_registry_stems_missing_meta_returns_empty(tmp_path):
    assert audit_mod._registry_stems(tmp_path / "absent.yaml") == set()


# ── audit() result shape ────────────────────────────────────────────────


def test_audit_returns_expected_structure(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run())

    report = audit_mod.audit([pdf])
    assert report["tool"] == "euxis-audit"
    assert report["verapdf_present"] is True
    assert set(report["summary"].keys()) == {"pdfs", "checks", "pass", "fail", "skip", "error"}
    assert report["summary"]["pdfs"] == 1
    assert report["summary"]["checks"] == 3  # ua2, wt1a, 4f
    assert report["summary"]["pass"] == 3
    assert report["summary"]["fail"] == 0
    for f in report["flavours"]:
        assert set(f.keys()) == {"id", "label", "blocking"}


def test_audit_records_fail(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run(pass_for=("ua2",)))

    report = audit_mod.audit([pdf])
    assert report["summary"]["pass"] == 1  # only ua2
    assert report["summary"]["fail"] == 2  # wt1a + 4f


def test_audit_skip_when_verapdf_absent(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: None)
    report = audit_mod.audit([pdf])
    assert report["verapdf_present"] is False
    assert report["summary"]["skip"] == 3


def test_audit_records_error_on_timeout(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")

    import subprocess as sp

    def raise_timeout(*args, **kwargs):
        raise sp.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr(audit_mod.subprocess, "run", raise_timeout)
    report = audit_mod.audit([pdf], timeout=1)
    assert report["summary"]["error"] == 3


# ── render_markdown ─────────────────────────────────────────────────────


def test_render_markdown_includes_summary(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run())
    report = audit_mod.audit([pdf])
    md = audit_mod.render_markdown(report)
    assert "# Euxis EAA / Accessibility Audit Report" in md
    assert "## Summary" in md
    assert "## Per-flavour" in md
    assert "## Per-PDF" in md
    assert "p.pdf" in md


# ── _is_blocking ────────────────────────────────────────────────────────


def test_is_blocking_true_on_fail(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run(pass_for=("ua2",)))
    report = audit_mod.audit([pdf])
    assert audit_mod._is_blocking(report) is True


def test_is_blocking_false_on_all_pass(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run())
    report = audit_mod.audit([pdf])
    assert audit_mod._is_blocking(report) is False


# ── main() CLI ──────────────────────────────────────────────────────────


def test_main_no_pdfs_returns_zero_unless_strict(tmp_path, monkeypatch):
    # Empty target
    rc = audit_mod.main([str(tmp_path)])
    assert rc == 0
    rc = audit_mod.main([str(tmp_path), "--strict"])
    assert rc == 1


def test_main_strict_failure_returns_one(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run(pass_for=()))
    monkeypatch.setattr(audit_mod, "DEFAULT_AUDIT_DIR", tmp_path / ".audit")
    rc = audit_mod.main([str(pdf), "--strict", "--all"])
    assert rc == 1


def test_main_strict_without_verapdf_returns_one(tmp_path, monkeypatch):
    """Strict mode + missing veraPDF binary must exit non-zero with a clear
    error, never silently pass on a broken runner."""
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda _x: None)
    monkeypatch.setattr(audit_mod, "DEFAULT_AUDIT_DIR", tmp_path / ".audit")
    rc = audit_mod.main([str(pdf), "--strict", "--all"])
    assert rc == 1


def test_main_writes_json_and_markdown(tmp_path, monkeypatch):
    pdf = _make_pdf(tmp_path / "p.pdf")
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run())
    monkeypatch.setattr(audit_mod, "DEFAULT_AUDIT_DIR", tmp_path / ".audit")
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    rc = audit_mod.main([str(pdf), "--all", "--json", str(json_path), "--markdown", str(md_path)])
    assert rc == 0
    assert json_path.exists()
    assert md_path.exists()
    report = json.loads(json_path.read_text())
    assert report["summary"]["pass"] == 3


def test_main_filters_by_registry_when_no_all(tmp_path, monkeypatch):
    """Default mode applies registry filter, --all bypasses."""
    monkeypatch.setattr(audit_mod.shutil, "which", lambda x: "/usr/bin/verapdf")
    monkeypatch.setattr(audit_mod.subprocess, "run", _fake_subprocess_run())
    monkeypatch.setattr(audit_mod, "DEFAULT_AUDIT_DIR", tmp_path / ".audit")
    _make_pdf(tmp_path / "build" / "papers" / "wanted.pdf")
    _make_pdf(tmp_path / "build" / "jobs" / "unwanted.pdf")
    meta = tmp_path / "meta.yaml"
    meta.write_text(
        "documents:\n  wanted:\n    src: src/papers/wanted.tex\n",
        encoding="utf-8",
    )
    rc = audit_mod.main(
        [
            str(tmp_path / "build"),
            "--meta",
            str(meta),
            "--json",
            str(tmp_path / "r.json"),
            "--markdown",
            str(tmp_path / "r.md"),
        ]
    )
    assert rc == 0
    report = json.loads((tmp_path / "r.json").read_text())
    assert report["summary"]["pdfs"] == 1
    assert "wanted.pdf" in next(iter(report["by_pdf"].keys()))
