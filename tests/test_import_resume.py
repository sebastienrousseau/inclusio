# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""JSON Resume importer tests (Sprint 5, #6).

Covers:
  - field-by-field mapping (basics, work, volunteer, education,
    skills, languages, awards, publications)
  - date-range normalisation
  - location flattening
  - name splitting (single, multi-part)
  - missing-field tolerance
  - unknown-field pass-through under `_jsonresume_extras`
  - CLI: stdout default, file output, error paths
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from euxis_publisher.cli import import_resume as imp

CANONICAL = {
    "basics": {
        "name": "Jane Doe",
        "label": "Senior Backend Engineer",
        "email": "jane@example.com",
        "phone": "+44 7000 000000",
        "url": "https://janedoe.dev",
        "summary": "Builds payments rails for tier-1 banks.",
        "location": {"city": "London", "region": "England", "countryCode": "UK"},
        "profiles": [{"network": "GitHub", "url": "https://github.com/jd"}],
    },
    "work": [
        {
            "name": "BigBank",
            "position": "VP, Payments",
            "location": "London",
            "startDate": "2024-01-01",
            "endDate": "2026-05-01",
            "summary": "Tier-1 retail bank.",
            "highlights": [
                "Owned the API gateway roadmap",
                "Closed $5M ARR",
            ],
        }
    ],
    "education": [
        {
            "institution": "Imperial College",
            "studyType": "MSc",
            "area": "Computer Science",
            "location": "London",
            "startDate": "2008-09-01",
            "endDate": "2010-06-30",
            "score": "Distinction",
        }
    ],
    "skills": [
        {
            "name": "API strategy",
            "level": "Master",
            "keywords": ["REST", "GraphQL", "gRPC"],
        }
    ],
    "languages": [
        {"language": "English", "fluency": "Native"},
        {"language": "French", "fluency": "Conversational"},
    ],
    "awards": [
        {
            "title": "Innovator of the Year",
            "awarder": "BigBank",
            "date": "2025-01-01",
            "summary": "For API gateway rollout.",
        }
    ],
    "publications": [
        {
            "name": "API Gateway Patterns",
            "publisher": "ACM",
            "releaseDate": "2024-06-01",
            "url": "https://acm.example/paper",
        }
    ],
}


# ── _split_name ──────────────────────────────────────────────────────


def test_split_name_full():
    assert imp._split_name("Jane Doe") == {"first": "Jane", "last": "Doe"}


def test_split_name_three_parts():
    assert imp._split_name("Jane Mary Doe") == {"first": "Jane", "last": "Mary Doe"}


def test_split_name_single():
    assert imp._split_name("Cher") == {"first": "Cher", "last": ""}


def test_split_name_empty():
    assert imp._split_name("") == {"first": "", "last": ""}


def test_split_name_strips_whitespace():
    assert imp._split_name("  Jane  Doe  ") == {"first": "Jane", "last": "Doe"}


# ── _format_location ─────────────────────────────────────────────────


def test_format_location_full():
    assert (
        imp._format_location({"city": "London", "region": "England", "countryCode": "UK"})
        == "London, England, UK"
    )


def test_format_location_partial():
    assert imp._format_location({"city": "Berlin"}) == "Berlin"


def test_format_location_empty():
    assert imp._format_location({}) == ""
    assert imp._format_location(None) == ""


# ── _format_date_range ───────────────────────────────────────────────


def test_format_date_range_full_iso():
    assert imp._format_date_range("2024-01-01", "2026-05-01") == "01/2024 – 05/2026"


def test_format_date_range_year_only():
    assert imp._format_date_range("2024", "2026") == "2024 – 2026"


def test_format_date_range_open_ended():
    assert imp._format_date_range("2024-01-01", None) == "01/2024 – Present"


def test_format_date_range_both_missing():
    assert imp._format_date_range(None, None) == "Present"


# ── _convert_basics ──────────────────────────────────────────────────


def test_convert_basics_full():
    out = imp._convert_basics(CANONICAL["basics"])
    assert out["name"] == {"first": "Jane", "last": "Doe"}
    assert out["role"] == "Senior Backend Engineer"
    assert out["contact"]["email"] == "jane@example.com"
    assert out["contact"]["phone"] == "+44 7000 000000"
    assert out["contact"]["url"] == "https://janedoe.dev"
    assert out["contact"]["location"] == "London, England, UK"
    assert out["contact"]["profiles"][0]["network"] == "GitHub"
    assert "summary" in out


def test_convert_basics_promotes_long_summary_to_executive_profile():
    basics = {"name": "X", "summary": "x" * 300}
    out = imp._convert_basics(basics)
    assert "executive_profile" in out
    assert "summary" not in out


def test_convert_basics_label_fallback_to_headline():
    out = imp._convert_basics({"name": "X", "headline": "Hacker"})
    assert out["role"] == "Hacker"


# ── _convert_work / _convert_volunteer ──────────────────────────────


def test_convert_work_preserves_highlights_as_bullets():
    out = imp._convert_work(CANONICAL["work"])
    assert len(out) == 1
    job = out[0]
    assert job["company"] == "BigBank"
    assert job["title"] == "VP, Payments"
    assert job["dates"] == "01/2024 – 05/2026"
    assert job["bullets"] == ["Owned the API gateway roadmap", "Closed $5M ARR"]
    assert job["context"] == "Tier-1 retail bank."


def test_convert_work_empty_returns_empty_list():
    assert imp._convert_work(None) == []
    assert imp._convert_work([]) == []


def test_convert_volunteer_flags_volunteer_true():
    volunteer = [
        {
            "organization": "Open-source project",
            "position": "Maintainer",
            "startDate": "2020-01-01",
            "highlights": ["Triaged 500 issues"],
        }
    ]
    out = imp._convert_volunteer(volunteer)
    assert len(out) == 1
    assert out[0]["volunteer"] is True
    assert out[0]["company"] == "Open-source project"


# ── _convert_education ───────────────────────────────────────────────


def test_convert_education_concatenates_studytype_and_area():
    out = imp._convert_education(CANONICAL["education"])
    assert len(out) == 1
    e = out[0]
    assert e["institution"] == "Imperial College"
    assert e["degree"] == "MSc Computer Science"
    assert e["location"] == "London"
    assert e["gpa"] == "Distinction"


def test_convert_education_falls_back_to_study_type_only():
    out = imp._convert_education([{"institution": "Uni", "studyType": "BA"}])
    assert out[0]["degree"] == "BA"


# ── _convert_skills ──────────────────────────────────────────────────


def test_convert_skills_joins_keywords():
    out = imp._convert_skills(CANONICAL["skills"])
    assert out[0]["title"] == "API strategy"
    assert "REST" in out[0]["description"]
    assert "GraphQL" in out[0]["description"]


def test_convert_skills_uses_level_when_no_keywords():
    out = imp._convert_skills([{"name": "Leadership", "level": "Expert"}])
    assert out[0]["description"] == "Expert"


# ── _convert_languages ───────────────────────────────────────────────


def test_convert_languages_formats_fluency():
    out = imp._convert_languages(CANONICAL["languages"])
    assert "English (Native)" in out
    assert "French (Conversational)" in out


def test_convert_languages_empty():
    assert imp._convert_languages(None) == ""


# ── _convert_awards_and_publications ─────────────────────────────────


def test_awards_and_publications_fold_into_innovation():
    out = imp._convert_awards_and_publications(CANONICAL["awards"], CANONICAL["publications"])
    assert any("Innovator of the Year" in line for line in out)
    assert any("API Gateway Patterns" in line for line in out)


# ── convert (end-to-end) ─────────────────────────────────────────────


def test_convert_full_round_trip():
    out = imp.convert(CANONICAL)
    assert out["name"]["first"] == "Jane"
    assert out["role"] == "Senior Backend Engineer"
    assert out["contact"]["email"] == "jane@example.com"
    assert len(out["experience"]) == 1
    assert len(out["education"]) == 1
    assert "competencies" in out
    assert "innovation" in out
    assert "languages" in out


def test_convert_preserves_unknown_keys_under_extras():
    resume = {
        "basics": {"name": "X"},
        "custom_block": {"key": "value"},
    }
    out = imp.convert(resume)
    assert "_jsonresume_extras" in out
    assert out["_jsonresume_extras"]["custom_block"] == {"key": "value"}


def test_convert_minimal_resume():
    out = imp.convert({"basics": {"name": "Solo"}})
    assert out["name"] == {"first": "Solo", "last": ""}
    assert "experience" not in out
    assert "education" not in out


# ── load_json_resume ────────────────────────────────────────────────


def test_load_json_resume_parses_file(tmp_path):
    src = tmp_path / "resume.json"
    src.write_text(json.dumps(CANONICAL))
    out = imp.load_json_resume(src)
    assert out["basics"]["name"] == "Jane Doe"


def test_load_json_resume_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        imp.load_json_resume(tmp_path / "missing.json")


def test_load_json_resume_invalid_json_raises(tmp_path):
    src = tmp_path / "bad.json"
    src.write_text("not json")
    with pytest.raises(ValueError, match="not valid JSON"):
        imp.load_json_resume(src)


# ── dump_yaml ────────────────────────────────────────────────────────


def test_dump_yaml_writes_block_style(tmp_path):
    out = tmp_path / "out.yaml"
    imp.dump_yaml({"role": "Senior Engineer", "contact": {"email": "a@b"}}, out)
    assert out.exists()
    text = out.read_text()
    # Block style — no `{}` flow mappings.
    assert "{" not in text


def test_dump_yaml_creates_parent_dir(tmp_path):
    out = tmp_path / "nested" / "deep" / "out.yaml"
    imp.dump_yaml({"x": 1}, out)
    assert out.exists()


# ── CLI: main ────────────────────────────────────────────────────────


def test_cli_writes_to_stdout_by_default(tmp_path, capsys):
    src = tmp_path / "resume.json"
    src.write_text(json.dumps(CANONICAL))
    rc = imp.main([str(src)])
    assert rc == 0
    captured = capsys.readouterr()
    parsed = yaml.safe_load(captured.out)
    assert parsed["name"]["first"] == "Jane"


def test_cli_writes_to_file_when_output_given(tmp_path, capsys):
    src = tmp_path / "resume.json"
    src.write_text(json.dumps(CANONICAL))
    out = tmp_path / "cv-data.yaml"
    rc = imp.main([str(src), "-o", str(out)])
    assert rc == 0
    assert out.exists()
    assert "Wrote " in capsys.readouterr().out


def test_cli_missing_input_exits_one(tmp_path, capsys):
    rc = imp.main([str(tmp_path / "ghost.json")])
    assert rc == 1
    assert "not found" in capsys.readouterr().err


def test_cli_invalid_json_exits_one(tmp_path, capsys):
    src = tmp_path / "bad.json"
    src.write_text("not json")
    rc = imp.main([str(src)])
    assert rc == 1
    assert "not valid JSON" in capsys.readouterr().err
