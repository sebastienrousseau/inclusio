"""test_semantic.py — Enforce: no raw formatting commands in src/ content files."""

import re

import pytest

# Commands forbidden in src/ .tex files (must use semantic macros instead)
FORBIDDEN_PATTERNS = [
    (r"\\textbf\{", "Use \\keyterm{} instead of \\textbf{}"),
    (r"\\vspace\{", "Remove \\vspace{} — handled by class"),
    (r"\\hspace\{", "Remove \\hspace{} — handled by class"),
    (r"\\fontsize\b", "Remove \\fontsize — handled by class"),
]


# Files that define formatting macros (not pure content) — excluded from check
EXCLUDED_FILES = {
    "patent-paper.tex",  # Shared titling/structure macros, not content
}


def find_tex_files(project_root):
    """Find all .tex files in src/, excluding macro definition files."""
    src_dir = project_root / "src"
    if not src_dir.exists():
        return []
    return [f for f in src_dir.rglob("*.tex") if f.name not in EXCLUDED_FILES]


def test_no_forbidden_commands(project_root):
    """Verify no raw formatting commands exist in src/ .tex files."""
    tex_files = find_tex_files(project_root)
    assert len(tex_files) > 0, "No .tex files found in src/"

    violations = []
    for tex_file in tex_files:
        content = tex_file.read_text(errors="replace")
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("%"):
                continue
            for pattern, msg in FORBIDDEN_PATTERNS:
                if re.search(pattern, line):
                    rel_path = tex_file.relative_to(project_root)
                    violations.append(f"  {rel_path}:{i}: {msg}")

    if violations:
        report = "\n".join(violations[:50])
        pytest.fail(
            f"Found {len(violations)} raw formatting command(s) in src/:\n{report}"
        )


def test_all_documents_have_source(project_root, documents):
    """Verify every document in meta.yaml has a source file."""
    missing = []
    for doc_id, config in documents.items():
        src_path = project_root / config["src"]
        if not src_path.exists():
            missing.append(f"  {doc_id}: {config['src']}")

    if missing:
        pytest.fail("Missing source files:\n" + "\n".join(missing))


def test_all_documents_use_pub_class(project_root, documents):
    """Verify all src/ .tex files reference pub-* classes (not old project classes)."""
    old_classes = ["cv", "faqs", "user-guide", "patent"]
    issues = []

    for doc_id, config in documents.items():
        src_path = project_root / config["src"]
        if not src_path.exists():
            continue

        content = src_path.read_text(errors="replace")
        for old_cls in old_classes:
            # Match \documentclass{old_cls} or \documentclass[...]{old_cls}
            pattern = rf"\\documentclass(\[.*?\])?\{{{old_cls}\}}"
            if re.search(pattern, content):
                issues.append(f"  {doc_id}: still uses \\documentclass{{{old_cls}}}")

    if issues:
        pytest.fail(
            "Documents still referencing old classes:\n" + "\n".join(issues)
        )
