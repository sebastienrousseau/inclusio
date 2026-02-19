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
    """Verify build.py exists and has valid Python syntax."""
    build_py = project_root / "scripts" / "build.py"
    assert build_py.exists(), "scripts/build.py not found"
    source = build_py.read_text(encoding="utf-8")
    compile(source, str(build_py), "exec")


def test_directory_structure(project_root):
    """Verify public engine directory structure exists."""
    expected_dirs = [
        "core/cls",
        "core/sty",
        "scripts",
        "tests",
        ".github/workflows",
    ]
    for d in expected_dirs:
        assert (project_root / d).is_dir(), f"Missing directory: {d}"
