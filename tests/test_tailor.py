"""test_tailor.py — Full coverage tests for scripts/tailor.py."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Import tailor module from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import tailor


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_brief():
    """Sample job description text for testing."""
    return (
        "We are looking for a Senior Product Manager with experience in "
        "payment solutions, API development, and mobile banking. "
        "The ideal candidate has a track record of delivering digital "
        "products at scale, managing cross-functional teams, and driving "
        "strategic growth. Experience with SEPA, PSD2, and Open Banking "
        "is highly desirable. Must have strong stakeholder management "
        "and commercial planning skills."
    )


@pytest.fixture()
def google_brief():
    """A brief for a role quite different from the user's background."""
    return (
        "Senior Outbound Product Manager, Cloud AI. "
        "8 years of experience in product management or related technical "
        "roles. Experience with Generative AI or Large Language Models. "
        "Work cross-functionally to guide products from conception to "
        "launch. Go-to-market strategy and execution. Engage with "
        "customers and partners, gathering feedback. Drive product "
        "roadmap development. Cloud platforms and infrastructure."
    )


@pytest.fixture()
def sample_cv_data():
    """Minimal CV data structure for testing."""
    return {
        "build_mode": "draft",
        "footer_address": "Jane Doe, 1 Main St, London, UK",
        "name": {"first": "Jane", "last": "Doe"},
        "role": "Senior Product Manager, Payments",
        "contact": {"phone": "+1234", "email": "jane@example.com"},
        "summary": "Experienced product manager in payments.",
        "experience": [
            {
                "title": "Product Manager",
                "company": "BigCorp",
                "dates": "2020-2024",
                "logo": "figures/bigcorp.png",
                "bullets": [
                    "Led API development for payment solutions.",
                    "Managed team of designers and copywriters.",
                    "Drove strategic growth across mobile banking channels.",
                    "Organized office holiday party.",
                    "Partnering with sales to drive commercialization "
                    "and market adoption.",
                    "Owned product roadmap development and revenue strategy.",
                ],
            },
            {
                "title": "Junior PM",
                "company": "Startup",
                "dates": "2018-2020",
                "logo": "figures/startup.png",
                "bullets": [
                    "Worked on coffee ordering app.",
                    "Implemented SEPA payment integration.",
                ],
            },
        ],
        "prior_experience": [
            {
                "logo": "figures/old.png",
                "title": "Intern",
                "company": "OldCo, London",
                "location": "",
                "dates": "2017",
            },
        ],
        "skills": [
            {
                "title": "Payment Solutions",
                "description": "API development and mobile banking.",
            },
            {
                "title": "Graphic Design",
                "description": "Adobe Photoshop and Illustrator.",
            },
            {
                "title": "Stakeholder Management",
                "description": "Cross-functional team leadership and planning.",
            },
        ],
        "education": [
            {
                "year": "2018",
                "degree": "BSc CS",
                "institution": "University,",
                "location": "London",
            }
        ],
        "languages": "English (Native), French (Fluent)",
    }


@pytest.fixture()
def brief_file(tmp_path, sample_brief):
    """Create a temporary brief file."""
    f = tmp_path / "job-description.txt"
    f.write_text(sample_brief)
    return f


@pytest.fixture()
def cv_data_file(tmp_path, sample_cv_data):
    """Create a temporary CV data YAML file."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    f = data_dir / "cv-data.yaml"
    with open(f, "w") as fh:
        yaml.dump(sample_cv_data, fh, default_flow_style=False)
    return f


# ── TestLintCvData ─────────────────────────────────────────────────────


class TestLintCvData:
    def test_clean_data_no_warnings(self):
        data = {
            "summary": "Senior PM with 20+ years delivering payment solutions.",
            "experience": [
                {
                    "bullets": [
                        "Delivered £2M revenue increase across 3 markets.",
                        "Led cross-functional team of 12 engineers.",
                    ]
                }
            ],
            "skills": [
                {"description": "API design and cloud infrastructure."}
            ],
        }
        warnings = tailor.lint_cv_data(data)
        assert warnings == []

    def test_detects_banned_phrase_in_summary(self):
        data = {
            "summary": "A passionate about technology leader leveraging AI.",
            "experience": [],
            "skills": [],
        }
        warnings = tailor.lint_cv_data(data)
        phrases = [w["issue"] for w in warnings]
        assert any("passionate about" in p for p in phrases)
        assert any("leveraging" in p for p in phrases)

    def test_detects_banned_phrase_in_bullets(self):
        data = {
            "experience": [
                {
                    "bullets": [
                        "Spearheaded a cutting-edge platform initiative.",
                    ]
                }
            ],
        }
        warnings = tailor.lint_cv_data(data)
        issues = [w["issue"] for w in warnings]
        assert any("spearheaded" in i for i in issues)
        assert any("cutting-edge" in i for i in issues)

    def test_detects_american_ize_spelling(self):
        data = {
            "summary": "Optimized and standardized processes across teams.",
            "experience": [],
            "skills": [],
        }
        warnings = tailor.lint_cv_data(data)
        issues = [w["issue"] for w in warnings]
        assert any("American spelling" in i and "optimized" in i.lower()
                    for i in issues)

    def test_detects_ize_in_bullets(self):
        data = {
            "experience": [
                {
                    "bullets": [
                        "Digitized the customer onboarding process.",
                    ]
                }
            ],
        }
        warnings = tailor.lint_cv_data(data)
        assert any("American spelling" in w["issue"] for w in warnings)

    def test_detects_ize_in_skill_descriptions(self):
        data = {
            "skills": [
                {"description": "Specializing in modernized cloud platforms."}
            ],
        }
        warnings = tailor.lint_cv_data(data)
        assert any("American spelling" in w["issue"] for w in warnings)

    def test_flags_vague_bullets(self):
        data = {
            "experience": [
                {
                    "bullets": [
                        "Worked on various projects across the organisation.",
                    ]
                }
            ],
        }
        warnings = tailor.lint_cv_data(data)
        assert any("vague" in w["issue"] for w in warnings)

    def test_metric_bullet_not_flagged(self):
        data = {
            "experience": [
                {
                    "bullets": [
                        "Improved conversion rate by 35% in Q3 2024.",
                    ]
                }
            ],
        }
        warnings = tailor.lint_cv_data(data)
        assert not any("vague" in w["issue"] for w in warnings)

    def test_impact_verb_bullet_not_flagged(self):
        data = {
            "experience": [
                {
                    "bullets": [
                        "Orchestrated the migration to a new platform.",
                    ]
                }
            ],
        }
        warnings = tailor.lint_cv_data(data)
        assert not any("vague" in w["issue"] for w in warnings)

    def test_currency_symbols_count_as_metrics(self):
        data = {
            "experience": [
                {
                    "bullets": [
                        "Saved £500K annually through process improvements.",
                        "Generated $2.1M in new revenue streams.",
                        "Reduced costs by €300K across European operations.",
                    ]
                }
            ],
        }
        warnings = tailor.lint_cv_data(data)
        assert not any("vague" in w["issue"] for w in warnings)

    def test_empty_data_no_crash(self):
        assert tailor.lint_cv_data({}) == []
        assert tailor.lint_cv_data({"experience": []}) == []
        assert tailor.lint_cv_data({"skills": []}) == []

    def test_multiple_issues_in_one_bullet(self):
        data = {
            "experience": [
                {
                    "bullets": [
                        "Leveraging cutting-edge technology to optimize "
                        "workflows seamlessly.",
                    ]
                }
            ],
        }
        warnings = tailor.lint_cv_data(data)
        issues = [w["issue"] for w in warnings]
        # Should flag leveraging, cutting-edge, optimize, seamlessly, and vague
        assert len(warnings) >= 4

    def test_warning_includes_field_path(self):
        data = {
            "experience": [
                {"bullets": ["Good bullet. Delivered results."]},
                {"bullets": ["Leveraging synergy to drive innovation."]},
            ],
        }
        warnings = tailor.lint_cv_data(data)
        fields = [w["field"] for w in warnings]
        assert any("experience[1].bullets[0]" in f for f in fields)


class TestLintIntegration:
    """Test that lint_cv_data is called during generate()."""

    def test_generate_logs_lint_warnings(self, brief_file, tmp_path,
                                          monkeypatch, capsys):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        # CV data with a banned phrase in a bullet to trigger lint
        cv_data = {
            "name": {"first": "Jane", "last": "Doe"},
            "role": "PM",
            "contact": {"phone": "+1", "email": "j@e.com"},
            "summary": "Experienced product manager.",
            "experience": [
                {
                    "title": "PM",
                    "company": "Co",
                    "dates": "2020-2024",
                    "bullets": [
                        "Leveraging cutting-edge AI to transform workflows.",
                    ],
                }
            ],
            "skills": [],
            "education": [],
            "languages": "English",
        }
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(cv_data, f, default_flow_style=False)

        tailor.generate(brief_file, "cv", "lint-test", use_ai=False)
        err = capsys.readouterr().err
        assert "LINT" in err
        assert "warning" in err


# ── TestExtractYaml ────────────────────────────────────────────────────


class TestExtractYaml:
    def test_clean_yaml(self):
        text = "build_mode: draft\nname:\n  first: Jane\n"
        assert "build_mode: draft" in tailor._extract_yaml(text)

    def test_strips_markdown_fences(self):
        text = "```yaml\nbuild_mode: draft\nname: Jane\n```"
        result = tailor._extract_yaml(text)
        assert "```" not in result
        assert "build_mode: draft" in result

    def test_strips_leading_prose(self):
        text = (
            "Here is the tailored YAML:\n\n"
            "build_mode: draft\nname:\n  first: Jane\n"
        )
        result = tailor._extract_yaml(text)
        assert result.startswith("build_mode:")

    def test_strips_trailing_commentary(self):
        text = (
            "build_mode: draft\nname: Jane\n\n"
            "**Key changes made:**\n- Changed summary\n"
        )
        result = tailor._extract_yaml(text)
        assert "Key changes" not in result
        assert "build_mode: draft" in result

    def test_strips_leading_and_trailing(self):
        text = (
            "I have tailored your CV:\n\n"
            "build_mode: draft\nrole: PM\n\n"
            "Note: I adjusted the summary.\n"
        )
        result = tailor._extract_yaml(text)
        assert result.startswith("build_mode:")
        assert "Note:" not in result

    def test_fenced_yaml_with_surrounding_prose(self):
        text = (
            "Here you go:\n\n"
            "```yml\nbuild_mode: draft\n```\n\n"
            "This should work."
        )
        result = tailor._extract_yaml(text)
        assert result == "build_mode: draft"


# ── TestLoadStopwords ──────────────────────────────────────────────────


class TestLoadStopwords:
    def test_loads_from_file(self):
        words = tailor._load_stopwords()
        assert "the" in words
        assert "and" in words
        assert len(words) > 100

    def test_returns_empty_when_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            tailor, "STOPWORDS_FILE", tmp_path / "nonexistent.txt"
        )
        words = tailor._load_stopwords()
        assert words == set()

    def test_ignores_comments_and_blanks(self, monkeypatch, tmp_path):
        f = tmp_path / "stops.txt"
        f.write_text("# comment\n\nhello\nworld\n")
        monkeypatch.setattr(tailor, "STOPWORDS_FILE", f)
        words = tailor._load_stopwords()
        assert words == {"hello", "world"}


# ── TestCheckTool ──────────────────────────────────────────────────────


class TestCheckTool:
    def test_finds_known_tool(self):
        assert tailor.check_tool("python3") or tailor.check_tool("python")

    def test_returns_false_for_unknown(self):
        assert tailor.check_tool("totally_nonexistent_xyz") is False


# ── TestReadBrief ──────────────────────────────────────────────────────


class TestReadBrief:
    def test_reads_txt(self, brief_file):
        result = tailor.read_brief(brief_file)
        assert "Senior Product Manager" in result

    def test_reads_md(self, tmp_path):
        f = tmp_path / "brief.md"
        f.write_text("# Job Description\n\nLooking for an engineer.")
        result = tailor.read_brief(f)
        assert "engineer" in result

    def test_reads_markdown_ext(self, tmp_path):
        f = tmp_path / "brief.markdown"
        f.write_text("Looking for a developer.")
        result = tailor.read_brief(f)
        assert "developer" in result

    @patch("tailor.check_tool", return_value=True)
    @patch("tailor.subprocess.run")
    def test_docx_calls_pandoc(self, mock_run, mock_check, tmp_path):
        f = tmp_path / "brief.docx"
        f.write_bytes(b"fake docx content")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Pandoc converted text", stderr=""
        )
        result = tailor.read_brief(f)
        assert result == "Pandoc converted text"
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "pandoc" in cmd
        assert "-t" in cmd
        assert "plain" in cmd

    @patch("tailor.check_tool", return_value=True)
    @patch("tailor.subprocess.run")
    def test_rtf_calls_pandoc(self, mock_run, mock_check, tmp_path):
        f = tmp_path / "brief.rtf"
        f.write_text("{\\rtf1 Some content}")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="RTF converted text", stderr=""
        )
        result = tailor.read_brief(f)
        assert result == "RTF converted text"

    @patch("tailor.check_tool", return_value=False)
    def test_unsupported_without_pandoc_exits(self, mock_check, tmp_path):
        f = tmp_path / "brief.docx"
        f.write_bytes(b"fake docx")
        with pytest.raises(SystemExit):
            tailor.read_brief(f)

    @patch("tailor.check_tool", return_value=True)
    @patch("tailor.subprocess.run")
    def test_pandoc_failure_raises(self, mock_run, mock_check, tmp_path):
        f = tmp_path / "brief.docx"
        f.write_bytes(b"fake docx")
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "pandoc", stderr="conversion error"
        )
        with pytest.raises(subprocess.CalledProcessError):
            tailor.read_brief(f)

    def test_missing_file_exits(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        with pytest.raises(SystemExit):
            tailor.read_brief(f)


# ── TestExtractKeywords ────────────────────────────────────────────────


class TestExtractKeywords:
    def test_basic_extraction(self, sample_brief):
        keywords = tailor.extract_keywords(sample_brief)
        assert isinstance(keywords, set)
        assert len(keywords) > 0

    def test_filters_stop_words(self, sample_brief):
        keywords = tailor.extract_keywords(sample_brief)
        assert "the" not in keywords
        assert "and" not in keywords
        assert "for" not in keywords

    def test_case_insensitive(self):
        text = "Payment PAYMENT payment solutions Solutions"
        keywords = tailor.extract_keywords(text)
        assert "payment" in keywords

    def test_empty_text(self):
        assert tailor.extract_keywords("") == set()
        assert tailor.extract_keywords("   ") == set()

    def test_bigrams_extracted(self):
        text = "machine learning deep learning natural language processing"
        keywords = tailor.extract_keywords(text, top_n=20)
        assert "machine learning" in keywords or "deep learning" in keywords

    def test_top_n_limits_results(self):
        text = "alpha bravo charlie delta echo foxtrot " * 10
        keywords = tailor.extract_keywords(text, top_n=3)
        assert len(keywords) <= 3


# ── TestScoreSection ───────────────────────────────────────────────────


class TestScoreSection:
    def test_high_relevance(self):
        keywords = {"payment", "api", "banking"}
        text = "Led API development for payment solutions in banking."
        score = tailor.score_section(text, keywords)
        assert score > 0.5

    def test_no_relevance(self):
        keywords = {"quantum", "physics", "neutrino"}
        text = "Organized office holiday party for the team."
        score = tailor.score_section(text, keywords)
        assert score == 0.0

    def test_partial_match(self):
        keywords = {"payment", "api", "quantum", "design"}
        text = "Built payment API for enterprise clients."
        score = tailor.score_section(text, keywords)
        assert 0.0 < score < 1.0

    def test_empty_keywords(self):
        score = tailor.score_section("some text", set())
        assert score == 0.0


# ── TestExtractThemes ──────────────────────────────────────────────────


class TestExtractThemes:
    def test_detects_payment_theme(self, sample_brief):
        themes = tailor.extract_themes(sample_brief)
        assert "payments" in themes

    def test_detects_ai_theme(self, google_brief):
        themes = tailor.extract_themes(google_brief)
        assert "ai_ml" in themes

    def test_detects_gtm_theme(self, google_brief):
        themes = tailor.extract_themes(google_brief)
        assert "gtm" in themes

    def test_detects_product_theme(self, sample_brief):
        themes = tailor.extract_themes(sample_brief)
        assert "product" in themes

    def test_sorted_by_relevance(self, google_brief):
        themes = tailor.extract_themes(google_brief)
        scores = list(themes.values())
        assert scores == sorted(scores, reverse=True)

    def test_empty_text_returns_empty(self):
        assert tailor.extract_themes("") == {}

    def test_no_matching_themes(self):
        assert tailor.extract_themes("completely irrelevant gibberish xyz") == {}


# ── TestComposeSummary ─────────────────────────────────────────────────


class TestComposeSummary:
    def test_includes_theme_labels(self, sample_brief, sample_cv_data):
        keywords = tailor.extract_keywords(sample_brief)
        summary = tailor._compose_summary(
            sample_brief, keywords, sample_cv_data
        )
        # Should reference relevant themes
        assert "Senior" in summary
        assert "20+" in summary

    def test_includes_company_names(self, sample_brief, sample_cv_data):
        keywords = tailor.extract_keywords(sample_brief)
        summary = tailor._compose_summary(
            sample_brief, keywords, sample_cv_data
        )
        assert "BigCorp" in summary

    def test_includes_top_bullet_highlight(self, sample_brief, sample_cv_data):
        keywords = tailor.extract_keywords(sample_brief)
        summary = tailor._compose_summary(
            sample_brief, keywords, sample_cv_data
        )
        # Should include a results highlight or skills emphasis
        assert "Track record includes" in summary or "Core strengths" in summary

    def test_includes_matching_skills(self, sample_brief, sample_cv_data):
        keywords = tailor.extract_keywords(sample_brief)
        summary = tailor._compose_summary(
            sample_brief, keywords, sample_cv_data
        )
        assert "Core strengths" in summary

    def test_falls_back_when_no_themes(self, sample_cv_data):
        keywords = tailor.extract_keywords("xyz gibberish nothingmatch")
        summary = tailor._compose_summary(
            "xyz gibberish nothingmatch", keywords, sample_cv_data
        )
        assert summary == sample_cv_data["summary"]

    def test_single_company(self):
        data = {
            "role": "Engineer",
            "experience": [
                {"company": "OnlyCo", "bullets": ["Did stuff."]}
            ],
            "skills": [],
        }
        keywords = {"payment", "api"}
        summary = tailor._compose_summary(
            "payment api solutions", keywords, data
        )
        assert "OnlyCo" in summary

    def test_two_companies(self):
        data = {
            "role": "Engineer, Backend",
            "experience": [
                {"company": "AlphaCo", "bullets": ["Led payment API."]},
                {"company": "BetaCo", "bullets": ["Built platform."]},
            ],
            "skills": [],
        }
        keywords = {"payment", "api"}
        summary = tailor._compose_summary(
            "payment api solutions", keywords, data
        )
        assert "AlphaCo" in summary
        assert "BetaCo" in summary

    def test_bullet_without_trailing_period(self):
        data = {
            "role": "PM",
            "experience": [
                {"company": "Co", "bullets": ["Led payment API development"]}
            ],
            "skills": [],
        }
        keywords = {"payment", "api", "development"}
        summary = tailor._compose_summary(
            "payment api development", keywords, data
        )
        # Highlight should get a period appended
        assert summary.endswith(".")

    def test_no_experience(self):
        data = {"role": "PM", "experience": [], "skills": []}
        keywords = {"payment"}
        summary = tailor._compose_summary(
            "payment solutions", keywords, data
        )
        assert "Senior" in summary


# ── TestAdjustRole ─────────────────────────────────────────────────────


class TestAdjustRole:
    def test_extracts_senior_pm(self):
        brief = "Looking for a Senior Product Manager to lead..."
        result = tailor._adjust_role(brief, "Engineer, Payments")
        assert "Senior Product Manager" in result
        assert "Payments" in result

    def test_extracts_outbound_pm(self):
        brief = "As an Outbound Product Manager you will..."
        result = tailor._adjust_role(brief, "PM, Cloud")
        assert "Outbound Product Manager" in result
        assert "Cloud" in result

    def test_keeps_original_when_no_match(self):
        brief = "We need someone great at doing things."
        result = tailor._adjust_role(brief, "My Role, My Domain")
        assert result == "My Role, My Domain"

    def test_no_domain_in_base(self):
        brief = "Senior Product Manager needed"
        result = tailor._adjust_role(brief, "Engineer")
        assert "Senior Product Manager" in result

    def test_head_of_role(self):
        brief = "Head of Product Manager for the team"
        result = tailor._adjust_role(brief, "PM, Payments")
        assert "Head of" in result


# ── TestFilterBullets ──────────────────────────────────────────────────


class TestFilterBullets:
    def test_keeps_max_count(self):
        bullets = [f"Bullet {i}" for i in range(10)]
        keywords = {"bullet"}
        result = tailor._filter_bullets(bullets, keywords, max_count=3)
        assert len(result) == 3

    def test_orders_by_relevance(self):
        bullets = [
            "Organized office holiday party.",
            "Led API payment solutions development.",
            "Managed team of designers.",
        ]
        keywords = {"api", "payment", "solutions", "development"}
        result = tailor._filter_bullets(bullets, keywords, max_count=3)
        # API payment bullet should be first
        assert "API" in result[0]

    def test_empty_bullets(self):
        result = tailor._filter_bullets([], {"keyword"}, max_count=5)
        assert result == []

    def test_fewer_than_max(self):
        bullets = ["One.", "Two."]
        result = tailor._filter_bullets(bullets, {"one"}, max_count=5)
        assert len(result) == 2


# ── TestTailorCv ───────────────────────────────────────────────────────


class TestTailorCv:
    def test_rewrites_summary(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        # Summary should be different from original
        assert result["summary"] != sample_cv_data["summary"]
        assert "20+" in result["summary"]

    def test_adjusts_role(self, google_brief, sample_cv_data):
        result = tailor.tailor_cv(google_brief, sample_cv_data)
        # Should pick up "Outbound Product Manager" or "Senior ... Manager"
        assert result["role"] != sample_cv_data["role"] or \
            "Product Manager" in result["role"]

    def test_filters_bullets(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        # First experience has 6 bullets, should be capped at 5
        assert len(result["experience"][0]["bullets"]) <= 5

    def test_reorders_bullets(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        exp = result["experience"][0]
        # "holiday party" should NOT be first
        assert "holiday party" not in exp["bullets"][0]

    def test_reorders_skills(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        skill_titles = [s["title"] for s in result["skills"]]
        # "Graphic Design" should be last (least relevant to payments)
        assert skill_titles[-1] == "Graphic Design"

    def test_preserves_contact_info(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        assert result["contact"] == sample_cv_data["contact"]
        assert result["name"] == sample_cv_data["name"]

    def test_preserves_education(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        assert result["education"] == sample_cv_data["education"]

    def test_preserves_languages(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        assert result["languages"] == sample_cv_data["languages"]

    def test_preserves_prior_experience(self, sample_brief, sample_cv_data):
        result = tailor.tailor_cv(sample_brief, sample_cv_data)
        assert result["prior_experience"] == sample_cv_data["prior_experience"]

    def test_deep_copy_no_mutation(self, sample_brief, sample_cv_data):
        original_summary = sample_cv_data["summary"]
        original_bullets = copy.deepcopy(
            sample_cv_data["experience"][0]["bullets"]
        )
        tailor.tailor_cv(sample_brief, sample_cv_data)
        # Original data must not be mutated
        assert sample_cv_data["summary"] == original_summary
        assert sample_cv_data["experience"][0]["bullets"] == original_bullets


# ── TestClaudeGenerate ─────────────────────────────────────────────────


class TestClaudeGenerate:
    def test_returns_none_without_cli(self, monkeypatch):
        monkeypatch.setattr(tailor, "check_tool", lambda name: False)
        result = tailor.claude_generate("brief", "cv", {"key": "val"})
        assert result is None

    @patch("tailor.subprocess.run")
    @patch("tailor.check_tool", return_value=True)
    def test_calls_claude_cli(self, mock_check, mock_run):
        yaml_output = "name:\n  first: Tailored\n  last: CV\n"
        mock_run.return_value = MagicMock(
            returncode=0, stdout=yaml_output, stderr=""
        )
        result = tailor.claude_generate("brief text", "cv", {"base": "data"})
        assert result == {"name": {"first": "Tailored", "last": "CV"}}
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "claude"
        assert "-p" in cmd

    @patch("tailor.subprocess.run")
    @patch("tailor.check_tool", return_value=True)
    def test_strips_markdown_fences(self, mock_check, mock_run):
        yaml_output = "```yaml\nname:\n  first: Test\n```"
        mock_run.return_value = MagicMock(
            returncode=0, stdout=yaml_output, stderr=""
        )
        result = tailor.claude_generate("brief", "cv", {})
        assert result == {"name": {"first": "Test"}}

    @patch("tailor.subprocess.run")
    @patch("tailor.check_tool", return_value=True)
    def test_falls_back_on_nonzero_exit(self, mock_check, mock_run, capsys):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error"
        )
        result = tailor.claude_generate("brief", "cv", {})
        assert result is None
        assert "WARN" in capsys.readouterr().err

    @patch("tailor.subprocess.run")
    @patch("tailor.check_tool", return_value=True)
    def test_falls_back_on_timeout(self, mock_check, mock_run, capsys):
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 120)
        result = tailor.claude_generate("brief", "cv", {})
        assert result is None
        assert "timed out" in capsys.readouterr().err

    @patch("tailor.subprocess.run")
    @patch("tailor.check_tool", return_value=True)
    def test_falls_back_on_exception(self, mock_check, mock_run, capsys):
        mock_run.side_effect = OSError("spawn error")
        result = tailor.claude_generate("brief", "cv", {})
        assert result is None
        assert "WARN" in capsys.readouterr().err


# ── TestGenerate ───────────────────────────────────────────────────────


class TestGenerate:
    def test_writes_yaml(self, brief_file, sample_cv_data, tmp_path,
                         monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        data_file = data_dir / "cv-data.yaml"
        with open(data_file, "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        result = tailor.generate(brief_file, "cv", "test-output", use_ai=False)
        assert result.exists()
        assert result.suffix == ".yaml"
        with open(result) as f:
            content = yaml.safe_load(f)
        assert "name" in content

    def test_default_output_id_from_filename(self, brief_file, sample_cv_data,
                                              tmp_path, monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        result = tailor.generate(brief_file, "cv", use_ai=False)
        assert result.name == "job-description.yaml"

    def test_custom_output_id(self, brief_file, sample_cv_data, tmp_path,
                               monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        result = tailor.generate(brief_file, "cv", "my-custom-id", use_ai=False)
        assert result.name == "my-custom-id.yaml"

    def test_creates_tailored_dir(self, brief_file, sample_cv_data, tmp_path,
                                   monkeypatch):
        tailored = tmp_path / "data" / "tailored"
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "TAILORED_DIR", tailored)
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        assert not tailored.exists()
        tailor.generate(brief_file, "cv", "test", use_ai=False)
        assert tailored.exists()

    def test_claude_used_by_default(self, brief_file, sample_cv_data,
                                     tmp_path, monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        ai_data = {"name": {"first": "Claude", "last": "Generated"}}
        with patch.object(tailor, "claude_generate", return_value=ai_data):
            result_path = tailor.generate(brief_file, "cv", "ai-test")
            with open(result_path) as f:
                content = yaml.safe_load(f)
            assert content["name"]["first"] == "Claude"

    def test_no_ai_flag_skips_claude(self, brief_file, sample_cv_data,
                                      tmp_path, monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        with patch.object(tailor, "claude_generate") as mock_claude:
            tailor.generate(brief_file, "cv", "no-ai", use_ai=False)
            mock_claude.assert_not_called()

    def test_non_cv_type_copies_base(self, brief_file, tmp_path, monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        paper_data = {"title": "My Paper", "sections": []}
        with open(data_dir / "paper-data.yaml", "w") as f:
            yaml.dump(paper_data, f, default_flow_style=False)

        result_path = tailor.generate(
            brief_file, "paper", "test-paper", use_ai=False
        )
        with open(result_path) as f:
            content = yaml.safe_load(f)
        assert content["title"] == "My Paper"

    def test_custom_base_path(self, brief_file, sample_cv_data, tmp_path,
                               monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        (tmp_path / "data").mkdir(exist_ok=True)
        custom_base = tmp_path / "custom-cv.yaml"
        with open(custom_base, "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        result_path = tailor.generate(
            brief_file, "cv", "custom-test", base_path=custom_base,
            use_ai=False,
        )
        assert result_path.exists()

    def test_missing_base_data_exits(self, brief_file, tmp_path, monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        with pytest.raises(SystemExit):
            tailor.generate(brief_file, "cv", "fail-test", use_ai=False)


# ── TestTailorMain ─────────────────────────────────────────────────────


class TestTailorMain:
    def test_main_cv(self, brief_file, sample_cv_data, tmp_path, monkeypatch,
                     capsys):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        with patch("sys.argv", ["tailor.py", str(brief_file), "--no-ai"]):
            tailor.main()
        output = capsys.readouterr().out
        assert "TAILOR" in output

    def test_main_with_custom_id(self, brief_file, sample_cv_data, tmp_path,
                                  monkeypatch, capsys):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        with patch("sys.argv", ["tailor.py", str(brief_file),
                                 "--id", "my-cv", "--no-ai"]):
            tailor.main()
        output = capsys.readouterr().out
        assert "my-cv" in output

    def test_main_uses_claude_by_default(self, brief_file, sample_cv_data,
                                          tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        with patch.object(tailor, "claude_generate", return_value=None):
            with patch("sys.argv", ["tailor.py", str(brief_file)]):
                tailor.main()
        output = capsys.readouterr().out
        assert "TAILOR" in output

    def test_main_with_render_flag(self, brief_file, sample_cv_data, tmp_path,
                                    monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        mock_render = MagicMock()
        with patch("sys.argv", ["tailor.py", str(brief_file),
                                 "--render", "--no-ai"]):
            with patch.dict("sys.modules", {"render": mock_render}):
                tailor.main()
        mock_render.render_document.assert_called_once()

    def test_main_with_build_flag(self, brief_file, sample_cv_data, tmp_path,
                                   monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        mock_render = MagicMock()
        mock_build = MagicMock()
        mock_build.load_meta.return_value = {"build": {}}
        with patch("sys.argv", ["tailor.py", str(brief_file),
                                 "--build", "--no-ai"]):
            with patch.dict(
                "sys.modules",
                {"render": mock_render, "build": mock_build},
            ):
                tailor.main()
        mock_render.render_document.assert_called_once()
        mock_build.build_document.assert_called_once()

    def test_main_missing_brief_exits(self):
        with patch("sys.argv", ["tailor.py", "/nonexistent/brief.txt"]):
            with pytest.raises(SystemExit):
                tailor.main()

    def test_main_render_import_error(self, brief_file, sample_cv_data,
                                       tmp_path, monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "render":
                raise ImportError("No module named 'render'")
            return real_import(name, *args, **kwargs)

        with patch("sys.argv", ["tailor.py", str(brief_file),
                                 "--render", "--no-ai"]):
            monkeypatch.setattr(builtins, "__import__", mock_import)
            with pytest.raises(SystemExit):
                tailor.main()

    def test_main_build_import_error(self, brief_file, sample_cv_data,
                                      tmp_path, monkeypatch):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / "cv-data.yaml", "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        mock_render = MagicMock()
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "build":
                raise ImportError("No module named 'build'")
            return real_import(name, *args, **kwargs)

        with patch("sys.argv", ["tailor.py", str(brief_file),
                                 "--build", "--no-ai"]):
            with patch.dict("sys.modules", {"render": mock_render}):
                monkeypatch.setattr(builtins, "__import__", mock_import)
                with pytest.raises(SystemExit):
                    tailor.main()

    def test_main_with_base_flag(self, brief_file, sample_cv_data, tmp_path,
                                  monkeypatch, capsys):
        monkeypatch.setattr(tailor, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(tailor, "CONTENT_ROOT", tmp_path)
        monkeypatch.setattr(
            tailor, "TAILORED_DIR", tmp_path / "data" / "tailored"
        )
        (tmp_path / "data").mkdir(exist_ok=True)
        custom_base = tmp_path / "custom.yaml"
        with open(custom_base, "w") as f:
            yaml.dump(sample_cv_data, f, default_flow_style=False)

        with patch("sys.argv", ["tailor.py", str(brief_file),
                                 "--base", str(custom_base), "--no-ai"]):
            tailor.main()
        output = capsys.readouterr().out
        assert "TAILOR" in output
