# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Coverage-completion tests for `inclusio.cli.render`.

The Sprint 4 audit pushed render.py to 74% (drop from ~96%) because
the new `render_text` + `_render_cv_text` + `_render_generic_text`
helpers had no targeted tests, AND several long-standing branches in
`_render_cv_markdown` (scope_line, subheadline, nested `roles[]`,
prior_experience, innovation, competencies-as-dict) were uncovered.

This file fills both gaps in one go. Goal: render.py back above 95%.
"""

from __future__ import annotations

from inclusio.cli import render


def _maximal_cv() -> dict:
    """CV data exercising every optional branch in _render_cv_markdown."""
    return {
        "name": {"first": "Maximal", "last": "Author"},
        "role": "Director of Engineering",
        "scope_line": "leading 40 across UK & EU",
        "subheadline": "Payments rails + API platforms",
        "contact": {"phone": "+44 0000", "email": "max@example.com"},
        "executive_profile": "Impact-led product leader.",
        "achievements": [r"Closed \$5M ARR"],
        "experience": [
            {
                "company": "BigBank",
                "location": "London",
                "roles": [
                    {
                        "title": "VP, Payments",
                        "dates": "2024--2026",
                        "bullets": ["Owned roadmap"],
                    },
                    {
                        "title": "Director, APIs",
                        "dates": "2022--2024",
                        "bullets": ["Designed gateway"],
                    },
                ],
                "context": "Tier-1 retail bank, 100M customers.",
            },
            {
                "company": "Acme",
                "title": "Engineer",
                "location": "Remote",
                "dates": "2020--2022",
                "bullets": ["Built prototype"],
            },
        ],
        "prior_experience": [
            {
                "company": "Startup",
                "title": "Founder",
                "location": "London",
                "dates": "2018--2020",
                "bullets": ["Bootstrapped to seed"],
            },
            {
                "company": "Consultancy",
                "title": "Senior Engineer",
                "location": "Paris",
                "dates": "2016--2018",
            },
        ],
        "innovation": [
            "US Patent 10,000,000 — Quantum-safe authentication",
        ],
        "competencies": [
            {"title": "API Strategy", "description": "REST + GraphQL"},
            {"title": "Team Leadership", "description": "40-person org"},
        ],
        "education": [
            {
                "degree": "MSc CS",
                "institution": "Imperial",
                "location": "London",
                "year": "2010",
            }
        ],
        "languages": "English, French",
    }


def test_markdown_renders_scope_line_and_subheadline():
    out = render.render_markdown(_maximal_cv(), "cv")
    assert "*leading 40 across UK & EU*" in out
    assert "Payments rails + API platforms" in out


def test_markdown_renders_nested_roles_with_context():
    out = render.render_markdown(_maximal_cv(), "cv")
    assert "### BigBank — VP, Payments" in out
    assert "### BigBank — Director, APIs" in out
    assert "Tier-1 retail bank, 100M customers." in out


def test_markdown_renders_prior_experience_with_and_without_bullets():
    out = render.render_markdown(_maximal_cv(), "cv")
    assert "### Startup — Founder" in out
    assert "Bootstrapped to seed" in out
    assert "### Consultancy — Senior Engineer" in out


def test_markdown_renders_innovation_section():
    out = render.render_markdown(_maximal_cv(), "cv")
    assert "## Patents & Publications" in out
    assert "US Patent 10,000,000 — Quantum-safe authentication" in out


def test_markdown_renders_competencies_dict_shape():
    out = render.render_markdown(_maximal_cv(), "cv")
    assert "- **API Strategy**: REST + GraphQL" in out
    assert "- **Team Leadership**: 40-person org" in out


def test_markdown_renders_competencies_flat_string_shape():
    data = _maximal_cv()
    data["competencies"] = ["A", "B", "C"]
    out = render.render_markdown(data, "cv")
    assert "A · B · C" in out


def test_markdown_renders_skills_fallback_when_no_competencies():
    data = _maximal_cv()
    data.pop("competencies")
    data["skills"] = [{"title": "Go", "description": "Server\\hbox{-}side."}]
    out = render.render_markdown(data, "cv")
    assert "### Go" in out
    assert "Server-side." in out


def test_markdown_renders_summary_fallback_when_no_executive_profile():
    data = _maximal_cv()
    data.pop("executive_profile")
    data["summary"] = "Pre-2026 summary line."
    out = render.render_markdown(data, "cv")
    assert "## Summary" in out
    assert "Pre-2026 summary line." in out


def test_markdown_lines_dict_path():
    out = render._markdown_lines({"name": "Alice", "age": 30})
    assert "- **Name**: Alice" in out
    assert "- **Age**: 30" in out


def test_markdown_lines_dict_with_nested_dict():
    out = render._markdown_lines({"meta": {"k": "v"}})
    assert any("### Meta" in line for line in out)
    assert any("- **K**: v" in line for line in out)


def test_markdown_lines_list_of_scalars():
    out = render._markdown_lines(["one", "two"])
    assert "- one" in out
    assert "- two" in out


def test_markdown_lines_list_of_dicts():
    out = render._markdown_lines([{"k": "v"}])
    assert any(line.startswith("- ") for line in out)


def test_markdown_lines_none_value():
    assert render._markdown_lines(None) == ["-"]


def test_markdown_lines_scalar_value():
    assert render._markdown_lines(42) == ["42"]


def test_strip_markdown_escapes_passes_non_strings():
    assert render._strip_markdown_escapes(123) == 123


def test_text_cv_renders_summary_fallback_no_executive_profile():
    data = {"name": {"first": "X", "last": "Y"}, "summary": "Old-style summary."}
    out = render.render_text(data, "cv")
    assert "Summary" in out
    assert "Old-style summary." in out
    assert "Executive Profile" not in out


def test_text_cv_renders_with_nested_roles_branch():
    data = {
        "name": {"first": "X", "last": "Y"},
        "experience": [
            {
                "company": "Big",
                "location": "London",
                "roles": [
                    {"title": "Lead", "dates": "2024", "bullets": ["Did stuff"]},
                ],
            }
        ],
    }
    out = render.render_text(data, "cv")
    assert "Big — Lead" in out
    assert "  - Did stuff" in out


def test_text_cv_renders_skills_dict_shape_fallback():
    data = {
        "name": {"first": "X", "last": "Y"},
        "skills": [{"title": "Go", "description": "Backend"}],
    }
    out = render.render_text(data, "cv")
    assert "Skills" in out
    assert "- Go: Backend" in out


def test_generic_text_renders_dict_nested():
    data = {"title": "Doc", "config": {"host": "localhost", "port": 5432}}
    out = render.render_text(data, "paper")
    assert "Doc" in out
    assert "Config" in out
    assert "Host: localhost" in out
    assert "Port: 5432" in out


def test_generic_text_renders_list_of_dicts():
    data = {"title": "Doc", "items": [{"k1": "v1"}, {"k2": "v2"}]}
    out = render.render_text(data, "paper")
    assert "Items" in out
    assert "K1: v1" in out
    assert "K2: v2" in out


def test_generic_text_renders_none_value():
    data = {"title": "Doc", "field": None}
    out = render.render_text(data, "paper")
    assert "Doc" in out
    assert any(line.strip() == "-" for line in out.splitlines())


def test_generic_text_renders_scalar_value():
    data = {"title": "Doc", "version": 3}
    out = render.render_text(data, "paper")
    assert "Version" in out
    assert "3" in out


def test_generic_text_renders_subject_fallback_when_no_title():
    data = {"subject": "From Subject", "body": "hi"}
    out = render.render_text(data, "paper")
    assert "From Subject" in out


def test_generic_text_renders_doc_type_fallback_when_no_title_or_subject():
    out = render.render_text({"body": "hi"}, "user-guide")
    assert "User Guide" in out


def test_strip_text_markup_collapses_double_spaces():
    out = render._strip_text_markup("a\\, b\\enspace c")
    assert "a b c" in out
