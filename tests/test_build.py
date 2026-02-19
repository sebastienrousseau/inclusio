"""test_build.py — Verify build infrastructure is correctly configured."""

import subprocess
import sys

import pytest


def test_meta_yaml_valid(project_root, meta):
    """Verify meta.yaml loads and has required top-level keys."""
    assert "author" in meta, "meta.yaml missing 'author' key"
    assert "documents" in meta, "meta.yaml missing 'documents' key"
    assert "build" in meta, "meta.yaml missing 'build' key"
    assert "assets" in meta, "meta.yaml missing 'assets' key"


def test_documents_have_required_fields(documents):
    """Each document must have at minimum: class, src, title."""
    for doc_id, config in documents.items():
        assert "class" in config, f"{doc_id} missing 'class'"
        assert "src" in config, f"{doc_id} missing 'src'"
        assert "title" in config, f"{doc_id} missing 'title'"


def test_core_classes_exist(project_root):
    """Verify all core class files exist."""
    expected = [
        "core/cls/pub-base.cls",
        "core/cls/pub-cv.cls",
        "core/cls/pub-paper.cls",
        "core/cls/pub-patent.cls",
        "core/cls/pub-faq.cls",
        "core/cls/pub-guide.cls",
    ]
    for path in expected:
        assert (project_root / path).exists(), f"Missing: {path}"


def test_core_styles_exist(project_root):
    """Verify all core style files exist."""
    expected = [
        "core/sty/pub-colors.sty",
        "core/sty/pub-typography.sty",
        "core/sty/pub-buildmodes.sty",
        "core/sty/pub-metadata.sty",
        "core/sty/pub-common.sty",
    ]
    for path in expected:
        assert (project_root / path).exists(), f"Missing: {path}"


def test_build_script_executable(project_root):
    """Verify build.py exists and is parseable."""
    build_py = project_root / "scripts" / "build.py"
    assert build_py.exists(), "scripts/build.py not found"

    result = subprocess.run(
        [sys.executable, str(build_py), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"build.py --help failed: {result.stderr}"


def test_directory_structure(project_root):
    """Verify publisher-grade directory structure exists."""
    expected_dirs = [
        "core/cls",
        "core/sty",
        "data",
        "assets",
        "scripts",
        "src/cvs",
        "src/papers",
        "src/patents/qaas",
        "src/faqs",
        "src/guides",
        "tests",
    ]
    for d in expected_dirs:
        assert (project_root / d).is_dir(), f"Missing directory: {d}"
