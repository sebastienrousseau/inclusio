# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 5 (S5.1): tests for the AI-disclosure XMP field.

Per the STM Sept-2025 Generative-AI Disclosure classification, scholarly
PDFs should declare whether (and how) AI assisted production. Portals
are expected to begin enforcement 2026-Q4 onward.

The engine accepts `ai_disclosure` either at doc-config level (per
document) or at meta-level (project default). Per-doc wins. The field
is appended to `<dc:description>` in the XMP packet so Adobe's
Description panel renders it without a custom namespace.
"""

from __future__ import annotations

from euxis_publisher.cli import build


def _xmp_kwargs(**overrides):
    base = {
        "title": "T",
        "author_name": "A",
        "subject": "S",
        "description": "Base description.",
        "keywords": "k",
        "copyright_text": "© 2026",
        "copyright_url": "",
        "author_role": "Engineer",
        "producer": "Euxis",
    }
    base.update(overrides)
    return base


def test_xmp_omits_ai_disclosure_when_empty():
    xmp = build._build_xmp_xml(**_xmp_kwargs())
    assert "AI disclosure" not in xmp
    # Base description still emitted intact.
    assert "Base description." in xmp


def test_xmp_appends_ai_disclosure_to_description():
    xmp = build._build_xmp_xml(
        **_xmp_kwargs(),
        ai_disclosure="Drafted by author; spelling assist via local LLM (Llama 3 8B).",
    )
    assert "AI disclosure: Drafted by author" in xmp
    # The base description remains the prefix.
    assert "Base description." in xmp


def test_xmp_ai_disclosure_xml_escaped():
    """Disclosure text containing &, <, > must be XML-escaped."""
    xmp = build._build_xmp_xml(
        **_xmp_kwargs(),
        ai_disclosure="Used <gpt-5> & a local model",
    )
    assert "&lt;gpt-5&gt;" in xmp
    assert "&amp;" in xmp


def test_xmp_ai_disclosure_works_without_base_description():
    xmp = build._build_xmp_xml(
        **_xmp_kwargs(description=""),
        ai_disclosure="AI used for grammar only.",
    )
    assert "AI disclosure: AI used for grammar only." in xmp


def test_post_process_reads_ai_disclosure_from_doc_config(tmp_path, monkeypatch):
    """Per-doc `ai_disclosure:` in meta.documents[id] reaches the XMP packet."""
    pytest = __import__("pytest")
    pikepdf = pytest.importorskip("pikepdf")
    pdf_path = tmp_path / "p.pdf"
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    pdf.save(pdf_path)

    doc_config = {
        "title": "Test",
        "description": "Manuscript.",
        "ai_disclosure": "Llama 3 8B drafted §2; author edited.",
    }
    meta = {"author": {"name": "X"}}
    build._post_process_pdf(pdf_path, "doc", doc_config, meta)

    with pikepdf.open(pdf_path) as out:
        raw = out.Root["/Metadata"].read_bytes().decode("utf-8")
        assert "AI disclosure: Llama 3 8B drafted §2" in raw


def test_post_process_per_doc_overrides_meta_level(tmp_path, monkeypatch):
    """Per-doc ai_disclosure wins over meta-level default."""
    pytest = __import__("pytest")
    pikepdf = pytest.importorskip("pikepdf")
    pdf_path = tmp_path / "p.pdf"
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    pdf.save(pdf_path)

    doc_config = {"title": "T", "ai_disclosure": "PER-DOC"}
    meta = {"author": {"name": "X"}, "ai_disclosure": "META-LEVEL"}
    build._post_process_pdf(pdf_path, "doc", doc_config, meta)

    with pikepdf.open(pdf_path) as out:
        raw = out.Root["/Metadata"].read_bytes().decode("utf-8")
        assert "PER-DOC" in raw
        assert "META-LEVEL" not in raw


def test_post_process_falls_back_to_meta_level(tmp_path, monkeypatch):
    """When doc has no ai_disclosure, meta-level default is used."""
    pytest = __import__("pytest")
    pikepdf = pytest.importorskip("pikepdf")
    pdf_path = tmp_path / "p.pdf"
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    pdf.save(pdf_path)

    doc_config = {"title": "T"}
    meta = {"author": {"name": "X"}, "ai_disclosure": "META-LEVEL"}
    build._post_process_pdf(pdf_path, "doc", doc_config, meta)

    with pikepdf.open(pdf_path) as out:
        raw = out.Root["/Metadata"].read_bytes().decode("utf-8")
        assert "META-LEVEL" in raw
