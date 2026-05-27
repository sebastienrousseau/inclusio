"""Source entrypoint contract tests for public corpus documents."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_FILE = PROJECT_ROOT / "data" / "meta.yaml"

ENTRYPOINTS = {
    "src/cvs/cv.tex": "pub-cv",
    "src/patents/patent/patent.tex": "pub-patent-us",
    "src/papers/prime-paper.tex": "pub-prime",
    "src/papers/arxiv-paper.tex": "pub-arxiv",
    "src/guides/user-guide.tex": "pub-guide",
    "src/papers/preprint-paper.tex": "pub-preprint",
    "src/faqs/faqs.tex": "pub-faq",
    "src/bios/bio.tex": "pub-bio",
}

FRAGMENTS = {
    "src/papers/patent-paper.tex",
}


def test_entrypoint_files_exist():
    for rel in [*ENTRYPOINTS.keys(), *FRAGMENTS]:
        assert (PROJECT_ROOT / rel).exists(), f"Missing source file: {rel}"


def test_entrypoints_use_expected_classes():
    for rel, expected_cls in ENTRYPOINTS.items():
        content = (PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        assert f"\\documentclass{{{expected_cls}}}" in content, (
            f"{rel} does not declare expected class {expected_cls}"
        )


def test_fragment_files_are_non_standalone():
    for rel in FRAGMENTS:
        content = (PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        assert "\\documentclass" not in content, f"{rel} should be a fragment"
        assert "\\section" in content, f"{rel} should contain section content"


def test_meta_documents_reference_entrypoints_and_fragment():
    meta = yaml.safe_load(META_FILE.read_text(encoding="utf-8"))
    docs = meta.get("documents", {})
    src_paths = {cfg.get("src", "") for cfg in docs.values()}

    for rel in ENTRYPOINTS:
        assert rel in src_paths, f"meta.yaml missing document src mapping for {rel}"

    for rel in FRAGMENTS:
        assert rel in src_paths, f"meta.yaml missing fragment src mapping for {rel}"


def test_fragment_is_marked_non_standalone_in_meta():
    meta = yaml.safe_load(META_FILE.read_text(encoding="utf-8"))
    docs = meta.get("documents", {})
    for doc_id, cfg in docs.items():
        if cfg.get("src") == "src/papers/patent-paper.tex":
            note = cfg.get("note", "")
            assert note.startswith("This is an input file"), (
                f"{doc_id} should be marked as non-standalone via note"
            )
            return
    raise AssertionError("No meta document points to src/papers/patent-paper.tex")
