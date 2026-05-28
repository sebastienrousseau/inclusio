# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 7 CLI wiring: tests for `python -m euxis_publisher.cli.build judge`.

Covers both `--judge ats` (uses render --format text path) and
`--judge citations` (reads .tex source directly), plus the shared
report-printing / JSON-persist / --strict exit paths.
"""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from euxis_publisher.cli import build as build_mod
from euxis_publisher.judge import local_llm as llm_mod


@pytest.fixture
def content_root(tmp_path, monkeypatch):
    """Stand up a content tree with one CV template + one paper doc."""
    (tmp_path / "data").mkdir()
    (tmp_path / "src" / "papers").mkdir(parents=True)
    (tmp_path / "templates").mkdir()
    (tmp_path / "data" / "meta.yaml").write_text(
        "author:\n  name: Test\n"
        "documents:\n"
        "  whisper-paper:\n"
        "    class: pub-paper\n"
        "    src: src/papers/whisper.tex\n"
        "    title: Whisper Paper\n"
        "templates:\n"
        "  cv:\n"
        "    template: cv.tex.j2\n"
        "    data: cv-data.yaml\n"
        "    type: cv\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "cv-data.yaml").write_text(
        "name:\n  first: Jane\n  last: Doe\n"
        "role: Engineer\n"
        "contact:\n  email: jane@example.com\n  phone: +44 7000 000000\n"
        "executive_profile: Strong builder.\n"
        "experience:\n"
        "  - company: Acme\n    title: Engineer\n    dates: '01/2024'\n"
        "    location: Remote\n    bullets: [Did the work]\n"
        "competencies: [API, Payments]\n"
        "education:\n  - degree: MSc\n    institution: Uni\n    location: City\n    year: '09/2010'\n"
        "languages: English\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "cv.tex.j2").write_text(r"\documentclass{article}")
    (tmp_path / "src" / "papers" / "whisper.tex").write_text(
        r"""\documentclass{article}
\begin{document}
\section{Intro} Prior work \cite{smith2024} showed X.
\begin{thebibliography}{9}
\bibitem{smith2024} Smith. Work. 2024.
\end{thebibliography}
\end{document}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_mod, "CONTENT_ROOT", tmp_path)
    monkeypatch.setattr(build_mod, "BUILD_DIR", tmp_path / "build")
    monkeypatch.setattr(build_mod, "RENDERED_DIR", tmp_path / "build" / ".cache" / "rendered")
    monkeypatch.setattr(build_mod, "META_FILE", tmp_path / "data" / "meta.yaml")
    return tmp_path


# ── ats path ───────────────────────────────────────────────────────────


def test_judge_ats_renders_then_scores(content_root, capsys):
    """`--judge ats --doc cv` renders the CV to text then scores."""
    build_mod.main(["judge", "--doc", "cv", "--judge", "ats"])
    captured = capsys.readouterr()
    assert "ATS (cv)" in captured.out
    assert "Score:" in captured.out
    assert "Grade:" in captured.out


def test_judge_ats_writes_json_when_requested(content_root, tmp_path, capsys):
    json_path = tmp_path / "report.json"
    build_mod.main(
        ["judge", "--doc", "cv", "--judge", "ats", "--json", str(json_path)]
    )
    captured = capsys.readouterr()
    assert f"JSON report: {json_path}" in captured.out
    assert json_path.exists()
    payload = json.loads(json_path.read_text())
    assert "score" in payload
    assert "grade" in payload


def test_judge_ats_rejects_non_cv_template(content_root, capsys):
    """`--judge ats` only scores CVs."""
    # Add a non-cv template entry
    meta = (content_root / "data" / "meta.yaml").read_text()
    meta += "  paper:\n    template: paper.tex.j2\n    data: paper-data.yaml\n    type: paper\n"
    (content_root / "data" / "meta.yaml").write_text(meta)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["judge", "--doc", "paper", "--judge", "ats"])
    assert excinfo.value.code == 2
    assert "only scores CVs" in capsys.readouterr().err


def test_judge_ats_rejects_unregistered_doc(content_root, capsys):
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["judge", "--doc", "missing", "--judge", "ats"])
    assert excinfo.value.code == 2
    assert "not a registered template" in capsys.readouterr().err


# ── citations path ─────────────────────────────────────────────────────


def test_judge_citations_reads_tex_source(content_root, capsys):
    build_mod.main(["judge", "--doc", "whisper-paper", "--judge", "citations"])
    captured = capsys.readouterr()
    assert "CITATIONS (whisper-paper)" in captured.out
    assert "Grade:" in captured.out


def test_judge_citations_rejects_doc_without_src(content_root, capsys):
    # Add a documents entry with no src.
    meta = (content_root / "data" / "meta.yaml").read_text()
    meta = meta.replace(
        "documents:",
        "documents:\n  shapeless:\n    class: pub-paper\n    title: No Src\n",
    )
    (content_root / "data" / "meta.yaml").write_text(meta)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["judge", "--doc", "shapeless", "--judge", "citations"])
    assert excinfo.value.code == 2
    assert "no `src:`" in capsys.readouterr().err


def test_judge_citations_rejects_unregistered_doc(content_root, capsys):
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["judge", "--doc", "ghost", "--judge", "citations"])
    assert excinfo.value.code == 2
    assert "not in documents" in capsys.readouterr().err


def test_judge_citations_exits_one_when_src_file_missing(content_root, capsys):
    # Re-write meta to point at a non-existent file.
    meta = (content_root / "data" / "meta.yaml").read_text()
    meta = meta.replace("src/papers/whisper.tex", "src/papers/ghost.tex")
    (content_root / "data" / "meta.yaml").write_text(meta)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["judge", "--doc", "whisper-paper", "--judge", "citations"])
    assert excinfo.value.code == 1
    assert "not found" in capsys.readouterr().err


# ── unknown judge ──────────────────────────────────────────────────────


def test_judge_unknown_name_exits_two(content_root, capsys):
    """Argparse choices catches this before main() but the dispatch
    layer has a defence-in-depth check too."""
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["judge", "--doc", "cv", "--judge", "magic"])
    # Argparse error → exit 2.
    assert excinfo.value.code == 2


# ── --strict ───────────────────────────────────────────────────────────


def test_judge_strict_exits_one_on_low_grade(content_root, monkeypatch):
    """Stub render to drop a known-bad text file, so the real score_cv
    returns grade F → --strict exits 1."""

    def fake_render(*_args, **_kwargs):
        rendered = content_root / "build" / ".cache" / "rendered"
        rendered.mkdir(parents=True, exist_ok=True)
        (rendered / "cv.txt").write_text("nothing useful at all")  # → grade F

    from euxis_publisher.cli import render as render_module

    monkeypatch.setattr(render_module, "render_document", fake_render)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["judge", "--doc", "cv", "--judge", "ats", "--strict"])
    assert excinfo.value.code == 1


# ── LLM url path (citations + ats) ─────────────────────────────────────


def _stub_unreachable(monkeypatch):
    """Patch urllib.request.urlopen to always raise ECONNREFUSED."""
    monkeypatch.setattr(
        llm_mod.urllib.request,
        "urlopen",
        mock.Mock(side_effect=urllib.error.URLError("Connection refused")),
    )


def test_judge_citations_llm_url_falls_back_on_unreachable(
    content_root, monkeypatch, capsys
):
    """`--llm-url` set + server down → info breadcrumb, no crash."""
    _stub_unreachable(monkeypatch)
    build_mod.main(
        [
            "judge",
            "--doc",
            "whisper-paper",
            "--judge",
            "citations",
            "--llm-url",
            "http://localhost:8080",
        ]
    )
    captured = capsys.readouterr()
    assert "CITATIONS (whisper-paper)" in captured.out


def test_judge_ats_llm_url_falls_back_on_unreachable(
    content_root, monkeypatch, capsys
):
    _stub_unreachable(monkeypatch)
    build_mod.main(
        [
            "judge",
            "--doc",
            "cv",
            "--judge",
            "ats",
            "--llm-url",
            "http://localhost:8080",
        ]
    )
    captured = capsys.readouterr()
    assert "ATS (cv)" in captured.out
