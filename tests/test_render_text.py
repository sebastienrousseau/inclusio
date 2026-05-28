# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Tests for `render.render_text` — ATS-safe plain-text emitter.

The plain-text shadow exists to feed ATS pipelines (Workday,
Greenhouse, Taleo) that parse `.txt` more reliably than tagged
PDFs. These tests document the shadow's contract:

- CV layout: unmarked headings + hyphen bullets, no Markdown
  emphasis markers (`*`, `**`), no backticks, no LaTeX escapes.
- Generic shape: title + section headings underlined by `-`.
"""

from __future__ import annotations

from inclusio.cli import render


def _make_cv_data() -> dict:
    return {
        "name": {"first": "Jane", "last": "Doe"},
        "role": "Senior Product Manager",
        "contact": {"phone": "+44 0000", "email": "jane@example.com"},
        "executive_profile": "Builds payments rails for tier-1 banks.",
        "achievements": [
            "Shipped Citi Payments API in 9 months",
            r"Closed \$5M ARR in year one",
        ],
        "experience": [
            {
                "company": "Citi",
                "title": "VP, Payments",
                "location": "London",
                "dates": "2022--2026",
                "bullets": [
                    r"Led 12\,person team across UK \& EU",
                    "Owned a \\textbf{P\\&L} of \\$50M",
                ],
            },
        ],
        "competencies": ["API strategy", "Payments", "Team leadership"],
        "education": [
            {
                "degree": "MSc Computer Science",
                "institution": "Imperial College",
                "location": "London",
                "year": "2010",
            }
        ],
        "languages": "English, French",
    }


# ── _strip_text_markup ────────────────────────────────────────────────


def test_strip_text_markup_removes_latex_escapes():
    out = render._strip_text_markup(r"\$5M \& \% revenue")
    assert "\\" not in out
    assert "5M & % revenue" in out


def test_strip_text_markup_flattens_markdown_emphasis():
    out = render._strip_text_markup("**bold** and *italic*")
    assert out == "bold and italic"


def test_strip_text_markup_drops_backticks():
    out = render._strip_text_markup("the `foo` macro")
    assert "`" not in out
    assert "foo" in out


def test_strip_text_markup_passes_non_strings_through():
    assert render._strip_text_markup(42) == 42
    assert render._strip_text_markup(None) is None


# ── render_text on CV data ────────────────────────────────────────────


def test_render_text_cv_includes_name_and_role():
    out = render.render_text(_make_cv_data(), "cv")
    assert "Jane Doe" in out
    assert "Senior Product Manager" in out


def test_render_text_cv_has_no_markdown_emphasis():
    out = render.render_text(_make_cv_data(), "cv")
    # No `**`, no isolated `*`, no `#` headings — ATS parsers choke
    # on these in unstructured text.
    assert "**" not in out
    assert "#" not in out


def test_render_text_cv_strips_latex_escapes():
    out = render.render_text(_make_cv_data(), "cv")
    # The data file contains `\$5M`, `\&`, `\textbf{...}` etc.
    # None of these should reach the .txt output.
    assert "\\$" not in out
    assert "\\&" not in out
    assert "\\textbf" not in out
    assert "$5M" in out
    assert "P&L" in out


def test_render_text_cv_section_order_is_canonical():
    out = render.render_text(_make_cv_data(), "cv")
    # Headings should appear in the order: Profile/Summary, Impact,
    # Experience, Skills, Education. ATS pipelines key on this order.
    for i, label in enumerate(
        ["Executive Profile", "Selected Impact", "Experience", "Skills", "Education"]
    ):
        assert label in out, f"Missing heading: {label}"
    profile_at = out.index("Executive Profile")
    impact_at = out.index("Selected Impact")
    exp_at = out.index("Experience")
    skills_at = out.index("Skills")
    edu_at = out.index("Education")
    assert profile_at < impact_at < exp_at < skills_at < edu_at


def test_render_text_cv_uses_hyphen_bullets():
    out = render.render_text(_make_cv_data(), "cv")
    assert "- Shipped Citi Payments API" in out
    assert "  - Led 12 person team" in out


def test_render_text_cv_ends_with_newline():
    out = render.render_text(_make_cv_data(), "cv")
    assert out.endswith("\n")


def test_render_text_cv_competencies_as_middle_dot_list():
    out = render.render_text(_make_cv_data(), "cv")
    assert "API strategy · Payments · Team leadership" in out


# ── render_text on generic data ───────────────────────────────────────


def test_render_text_generic_emits_title_and_sections():
    data = {
        "title": "Whitepaper",
        "abstract": "Short abstract here.",
        "sections": ["Intro", "Method"],
    }
    out = render.render_text(data, "paper")
    assert "Whitepaper" in out
    assert "Abstract" in out  # heading derived from key name
    assert "Sections" in out


def test_render_text_generic_omits_build_mode_metadata():
    data = {"title": "Doc", "build_mode": "draft", "body": "Hi"}
    out = render.render_text(data, "paper")
    assert "build_mode" not in out.lower()


# ── format-routing in render_document ─────────────────────────────────


def test_format_text_maps_to_txt_extension(monkeypatch, tmp_path):
    """Render --format text must write build/.cache/rendered/<id>.txt."""
    import yaml

    (tmp_path / "data").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "data" / "meta.yaml").write_text(
        yaml.safe_dump(
            {
                "templates": {
                    "cv": {
                        "template": "cv.tex.j2",
                        "data": "cv-data.yaml",
                        "type": "cv",
                    }
                }
            }
        )
    )
    (tmp_path / "data" / "cv-data.yaml").write_text(yaml.safe_dump(_make_cv_data()))
    (tmp_path / "templates" / "cv.tex.j2").write_text(r"\documentclass{article}")

    render.render_document("cv", fmt="text", content_root=tmp_path)
    out_path = tmp_path / "build" / ".cache" / "rendered" / "cv.txt"
    assert out_path.exists(), f"Expected {out_path} to exist"
    content = out_path.read_text(encoding="utf-8")
    assert "Jane Doe" in content
    assert "Experience" in content
