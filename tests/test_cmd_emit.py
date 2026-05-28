# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 7 CLI wiring: tests for `python -m euxis_publisher.cli.build emit`.

The dispatch + argument-parsing + registry-filter behaviour is tested
here without invoking pandoc — `emit_all` is monkeypatched. End-to-end
pandoc integration is covered by `tests/test_emit_pandoc.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from euxis_publisher.cli import build as build_mod
from euxis_publisher.emit import pandoc as emit_pandoc


@pytest.fixture
def content_root(tmp_path, monkeypatch):
    """Stand up a minimal content tree with one registered + one fragment doc."""
    (tmp_path / "src" / "papers").mkdir(parents=True)
    (tmp_path / "src" / "papers" / "whisper.tex").write_text(
        r"\documentclass{article}\begin{document}hello\end{document}",
        encoding="utf-8",
    )
    (tmp_path / "src" / "papers" / "frag.tex").write_text(
        r"\section{Background} fragment",
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "meta.yaml").write_text(
        "documents:\n"
        "  whisper-paper:\n"
        "    class: pub-paper\n"
        "    src: src/papers/whisper.tex\n"
        "    title: Whisper Paper\n"
        "  frag-paper:\n"
        "    class: pub-paper\n"
        "    src: src/papers/frag.tex\n"
        "    title: Fragment\n"
        "    note: This is an input file used by another\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_mod, "CONTENT_ROOT", tmp_path)
    monkeypatch.setattr(build_mod, "BUILD_DIR", tmp_path / "build")
    monkeypatch.setattr(build_mod, "META_FILE", tmp_path / "data" / "meta.yaml")
    return tmp_path


@pytest.fixture
def stub_emit(monkeypatch):
    """Replace emit_pandoc.emit_all with a side-effect-free recorder."""
    calls: list[dict] = []

    def fake_emit_all(tex_path, output_dir, doc_id, formats=None, title=""):
        calls.append(
            {
                "tex": tex_path,
                "out_dir": output_dir,
                "doc_id": doc_id,
                "formats": formats,
                "title": title,
            }
        )
        formats = formats or ["html", "jats", "epub"]
        results = []
        for fmt in formats:
            ext = {"html": "html", "jats": "xml", "epub": "epub"}[fmt]
            out_path = output_dir / f"{doc_id}.{ext}"
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(f"stub {fmt}", encoding="utf-8")
            results.append(
                emit_pandoc.EmitResult(
                    doc_id=doc_id,
                    format=fmt,
                    output_path=out_path,
                    bytes=out_path.stat().st_size,
                )
            )
        return results

    monkeypatch.setattr(emit_pandoc, "emit_all", fake_emit_all)
    return calls


# ── Dispatch path ──────────────────────────────────────────────────────


def test_emit_all_registered_docs(content_root, stub_emit, capsys):
    rc = build_mod.main(["emit"])
    assert rc != 1  # main returns None on success
    captured = capsys.readouterr()
    # whisper-paper emitted, frag-paper skipped (input fragment).
    assert "OK   whisper-paper [html]" in captured.out
    assert "OK   whisper-paper [jats]" in captured.out
    assert "SKIP frag-paper: input fragment" in captured.out
    # One emit_all call for whisper-paper; frag-paper short-circuits.
    assert len(stub_emit) == 1
    assert stub_emit[0]["doc_id"] == "whisper-paper"


def test_emit_scoped_to_one_doc(content_root, stub_emit, capsys):
    build_mod.main(["emit", "--doc", "whisper-paper"])
    captured = capsys.readouterr()
    assert "OK   whisper-paper" in captured.out
    assert "frag-paper" not in captured.out
    assert len(stub_emit) == 1


def test_emit_formats_subset_honoured(content_root, stub_emit):
    build_mod.main(["emit", "--doc", "whisper-paper", "--formats", "html"])
    assert stub_emit[0]["formats"] == ["html"]


def test_emit_invalid_format_exits_two(content_root, stub_emit, capsys):
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["emit", "--doc", "whisper-paper", "--formats", "bogus"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "unsupported format" in captured.err


def test_emit_skips_missing_source(content_root, stub_emit, capsys, monkeypatch):
    # Re-write the manifest with one entry whose src doesn't exist.
    (content_root / "data" / "meta.yaml").write_text(
        "documents:\n  ghost:\n    class: pub-paper\n    src: src/missing.tex\n    title: Ghost\n",
        encoding="utf-8",
    )
    build_mod.main(["emit"])
    captured = capsys.readouterr()
    assert "SKIP ghost" in captured.out
    assert len(stub_emit) == 0


def test_emit_skips_entry_without_src(content_root, stub_emit, capsys):
    (content_root / "data" / "meta.yaml").write_text(
        "documents:\n  shapeless:\n    class: pub-paper\n    title: No Src\n",
        encoding="utf-8",
    )
    build_mod.main(["emit"])
    captured = capsys.readouterr()
    assert "SKIP shapeless: no src" in captured.out
    assert len(stub_emit) == 0


def test_emit_propagates_pandoc_missing(content_root, monkeypatch, capsys):
    def raise_missing(*_a, **_k):
        raise emit_pandoc.PandocMissing("pandoc not on PATH (test)")

    monkeypatch.setattr(emit_pandoc, "emit_all", raise_missing)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["emit", "--doc", "whisper-paper"])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "pandoc not on PATH" in captured.err


def test_emit_failure_is_counted_not_fatal_by_default(content_root, monkeypatch, capsys):
    def raise_called(*_a, **_k):
        raise subprocess.CalledProcessError(
            1, ["pandoc"], output="", stderr="latex syntax: unexpected \\foo"
        )

    monkeypatch.setattr(emit_pandoc, "emit_all", raise_called)
    # No SystemExit by default — failures are reported then we continue.
    build_mod.main(["emit", "--doc", "whisper-paper"])
    captured = capsys.readouterr()
    assert "FAIL whisper-paper" in captured.out
    assert "1 ok, 1 failed" in captured.out or "0 ok, 1 failed" in captured.out


def test_emit_strict_mode_exits_one_on_failure(content_root, monkeypatch):
    def raise_called(*_a, **_k):
        raise subprocess.CalledProcessError(1, ["pandoc"], stderr="x")

    monkeypatch.setattr(emit_pandoc, "emit_all", raise_called)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["emit", "--doc", "whisper-paper", "--strict"])
    assert excinfo.value.code == 1


def test_emit_command_registered_in_dispatch(content_root, stub_emit, capsys):
    """The `emit` subcommand must show up in --help."""
    with pytest.raises(SystemExit):
        build_mod.main(["--help"])
    captured = capsys.readouterr()
    assert "emit" in captured.out


def test_emit_passes_title_from_manifest(content_root, stub_emit):
    build_mod.main(["emit", "--doc", "whisper-paper"])
    assert stub_emit[0]["title"] == "Whisper Paper"
