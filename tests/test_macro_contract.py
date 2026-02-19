"""Macro contract tests for public class API stability."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_academic_macro_contract():
    paper = _read("core/cls/pub-paper.cls")
    preprint = _read("core/cls/pub-preprint.cls")
    arxiv = _read("core/cls/pub-arxiv.cls")

    assert "\\newcommand{\\affiliation}" in paper
    assert "\\newcommand{\\keywords}" in paper
    assert "\\newcommand{\\affiliation}" in preprint
    assert "\\newcommand{\\keywords}" in preprint
    assert "\\newcommand{\\correspondingauthor}" in preprint
    assert "\\newcommand{\\arxivid}" in arxiv
    assert "\\providecommand{\\affiliation}" in arxiv
    assert "\\providecommand{\\keywords}" in arxiv


def test_patent_macro_contract():
    patent = _read("core/cls/pub-patent.cls")
    patent_us = _read("core/cls/pub-patent-us.cls")

    assert "\\newcommand{\\patentParagraph}" in patent
    assert "\\newcommand{\\independentClaim}" in patent_us
    assert "\\newcommand{\\dependentClaim}" in patent_us
    assert "\\newcommand{\\priorityClaim}" in patent_us
    assert "\\newcommand{\\inventorDeclaration}" in patent_us


def test_guide_macro_contract():
    guide = _read("core/cls/pub-guide.cls")

    assert "\\newcommand{\\setDocType}" in guide
    assert "\\newcommand{\\setCodeLanguage}" in guide
    assert "\\newcommand{\\setCompanyName}" in guide


def test_bio_macro_contract():
    bio = _read("core/cls/pub-bio.cls")

    assert "\\newcommand{\\bioheader}" in bio
    assert "\\newcommand{\\biocontact}" in bio
    assert "\\newcommand{\\subjectarea}" in bio
