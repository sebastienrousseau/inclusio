"""test_build.py — Verify public engine infrastructure."""


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


def test_build_script_syntax(project_root):
    """Verify inclusio/cli/build.py exists and has valid Python syntax.

    The historical `scripts/build.py` thin shim was removed in v0.0.3
    (it just re-exported from `inclusio.cli.build`); the canonical
    entry point is now the package module.
    """
    build_py = project_root / "inclusio" / "cli" / "build.py"
    assert build_py.exists(), "inclusio/cli/build.py not found"
    source = build_py.read_text(encoding="utf-8")
    compile(source, str(build_py), "exec")


def test_directory_structure(project_root):
    """Verify public engine directory structure exists.

    The v0.0.3 directory hygiene sprint added `benches/`, `examples/`,
    and `docs/tutorials/`, and removed the `scripts/` Python shims
    (the shell scripts under `scripts/` remain).
    """
    expected_dirs = [
        "core/cls",
        "core/sty",
        "inclusio",
        "tests",
        "benches",
        "examples",
        "docs/tutorials",
        "docs/audit",
        ".github/workflows",
    ]
    for d in expected_dirs:
        assert (project_root / d).is_dir(), f"Missing directory: {d}"
