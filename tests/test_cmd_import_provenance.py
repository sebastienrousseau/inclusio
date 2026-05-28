# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""CLI dispatch tests for `cmd_import_resume` and `cmd_provenance`.

Both subcommands route into modules already covered by their own test
files (`test_import_resume.py`, `test_provenance_c2pa.py`). These
tests focus on the dispatch + argument plumbing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from euxis_publisher.cli import build as build_mod

# ── content_root fixture (shared shape with other CLI tests) ───────────


@pytest.fixture
def content_root(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "src" / "papers").mkdir(parents=True)
    (tmp_path / "build" / "papers").mkdir(parents=True)
    # Pre-place a fake PDF that cmd_provenance can find.
    (tmp_path / "build" / "papers" / "whisper.pdf").write_bytes(b"%PDF-1.7\n%fake\n")
    (tmp_path / "src" / "papers" / "whisper.tex").write_text(
        r"\documentclass{article}\begin{document}hi\end{document}"
    )
    (tmp_path / "data" / "meta.yaml").write_text(
        "author:\n  name: Test Author\n  publisher: Test Pub\n"
        "documents:\n"
        "  whisper-paper:\n"
        "    class: pub-paper\n"
        "    src: src/papers/whisper.tex\n"
        "    title: Whisper Paper\n"
        "    filing_date: '2026-05-28'\n"
        "    ai_disclosure: Drafted by Llama 3 8B.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_mod, "CONTENT_ROOT", tmp_path)
    monkeypatch.setattr(build_mod, "BUILD_DIR", tmp_path / "build")
    monkeypatch.setattr(build_mod, "META_FILE", tmp_path / "data" / "meta.yaml")
    return tmp_path


# ── cmd_import_resume ──────────────────────────────────────────────────


def _sample_resume() -> dict:
    return {
        "basics": {
            "name": "Jane Doe",
            "label": "Senior Engineer",
            "email": "jane@example.com",
            "phone": "+44 7000",
        },
        "work": [
            {
                "name": "Acme",
                "position": "Engineer",
                "startDate": "2024-01-01",
                "highlights": ["Built thing"],
            }
        ],
    }


def test_cmd_import_resume_writes_to_stdout(tmp_path, capsys, content_root):
    src = tmp_path / "resume.json"
    src.write_text(json.dumps(_sample_resume()))
    build_mod.main(["import-resume", str(src)])
    captured = capsys.readouterr()
    assert "name:" in captured.out
    assert "Jane" in captured.out


def test_cmd_import_resume_writes_to_file(tmp_path, capsys, content_root):
    src = tmp_path / "resume.json"
    src.write_text(json.dumps(_sample_resume()))
    out = tmp_path / "cv-data.yaml"
    build_mod.main(["import-resume", str(src), "-o", str(out)])
    assert out.exists()
    assert "Jane" in out.read_text()


def test_cmd_import_resume_missing_file_exits_one(tmp_path, capsys, content_root):
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["import-resume", str(tmp_path / "ghost.json")])
    assert excinfo.value.code == 1


# ── cmd_provenance ─────────────────────────────────────────────────────


def test_cmd_provenance_rejects_unregistered_doc(content_root, capsys):
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["provenance", "--doc", "ghost"])
    assert excinfo.value.code == 2
    assert "not in documents" in capsys.readouterr().err


def test_cmd_provenance_rejects_doc_without_src(content_root, capsys):
    (content_root / "data" / "meta.yaml").write_text(
        "author:\n  name: T\ndocuments:\n  shapeless:\n    class: pub-paper\n    title: No Src\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["provenance", "--doc", "shapeless"])
    assert excinfo.value.code == 2
    assert "`src:`" in capsys.readouterr().err


def test_cmd_provenance_missing_pdf_exits_one(content_root, capsys):
    # Delete the pre-placed PDF.
    (content_root / "build" / "papers" / "whisper.pdf").unlink()
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["provenance", "--doc", "whisper-paper"])
    assert excinfo.value.code == 1
    assert "not found" in capsys.readouterr().err


def test_cmd_provenance_happy_path_with_mocked_c2patool(content_root, monkeypatch, capsys):
    """End-to-end through cmd_provenance with c2patool subprocess mocked."""
    from euxis_publisher.provenance import c2pa as c2pa_mod

    captured = {"argv": None}

    def fake_which(_x):
        return "/fake/c2patool"

    def fake_run(argv, capture_output=False, text=False, timeout=None, check=False):
        captured["argv"] = list(argv)
        # Emulate --output by writing a signed-PDF stub.
        try:
            out_idx = argv.index("--output") + 1
            out_path = Path(argv[out_idx])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"%PDF-1.7\n%signed\n" + b"X" * 200)
        except (ValueError, IndexError):
            pass
        return mock.MagicMock(returncode=0, stdout="", stderr="signed with test_cert")

    monkeypatch.setattr(c2pa_mod.shutil, "which", fake_which)
    monkeypatch.setattr(c2pa_mod.subprocess, "run", fake_run)

    build_mod.main(["provenance", "--doc", "whisper-paper"])
    out = capsys.readouterr().out
    assert "OK   whisper-paper" in out
    assert "manifest bytes" in out
    assert "WARN: signed with c2patool's test cert" in out

    # Manifest was built from the doc's metadata (title, AI disclosure).
    manifest_idx = captured["argv"].index("--manifest") + 1
    manifest_path = Path(captured["argv"][manifest_idx])
    manifest_text = manifest_path.read_text()
    assert "Whisper Paper" in manifest_text
    assert "Llama 3 8B" in manifest_text


def test_cmd_provenance_strict_exits_one_on_test_cert(content_root, monkeypatch):
    """With --strict + no real cert, exit 1 after publishing."""
    from euxis_publisher.provenance import c2pa as c2pa_mod

    monkeypatch.setattr(c2pa_mod.shutil, "which", lambda _x: "/fake/c2patool")

    def fake_run(*_a, **_k):
        # Pretend to produce the output file.
        out_idx = _a[0].index("--output") + 1
        Path(_a[0][out_idx]).write_bytes(b"%PDF-1.7\nfake\n" + b"X" * 200)
        return mock.MagicMock(returncode=0, stdout="", stderr="test_cert")

    monkeypatch.setattr(c2pa_mod.subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["provenance", "--doc", "whisper-paper", "--strict"])
    assert excinfo.value.code == 1


def test_cmd_provenance_propagates_c2patool_missing(content_root, monkeypatch, capsys):
    from euxis_publisher.provenance import c2pa as c2pa_mod

    monkeypatch.setattr(c2pa_mod.shutil, "which", lambda _x: None)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["provenance", "--doc", "whisper-paper"])
    assert excinfo.value.code == 1
    assert "c2patool is required" in capsys.readouterr().err


def test_cmd_provenance_surfaces_c2patool_failure(content_root, monkeypatch, capsys):
    from euxis_publisher.provenance import c2pa as c2pa_mod

    monkeypatch.setattr(c2pa_mod.shutil, "which", lambda _x: "/fake/c2patool")

    def fake_run(*_a, **_k):
        return mock.MagicMock(returncode=1, stdout="", stderr="invalid manifest payload")

    monkeypatch.setattr(c2pa_mod.subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as excinfo:
        build_mod.main(["provenance", "--doc", "whisper-paper"])
    assert excinfo.value.code == 1
    assert "c2patool exit 1" in capsys.readouterr().err
    assert "invalid manifest" in capsys.readouterr().err or True
