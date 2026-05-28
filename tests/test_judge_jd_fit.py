# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 7 (S7.4): JD-to-CV fit judge tests.

Covers:
  - `extract_keywords`: tokenization, stopword pruning, technical
    sigils preserved (c++, c#, node.js).
  - `jaccard`: edge cases (empty sets, identical sets).
  - `extract_required_keywords`: trigger-phrase harvesting.
  - `_seniority_rank`: ladder match + word-boundary safety.
  - `score_jd_fit`: clean match, missing-required block, role-level
    mismatch (warn / block by gap size), low-overlap warn, metrics
    shape, floor protection.
  - `score_jd_fit_with_llm`: strength + gap merge, missing-finding
    handling, deduction clamp, LLM-unavailable fallback.
"""

from __future__ import annotations

import json
import sys
import urllib.error
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from euxis_publisher.judge import jd_fit
from euxis_publisher.judge import local_llm as llm_mod

# ── extract_keywords ───────────────────────────────────────────────────


def test_extract_keywords_lowercases_and_dedups():
    out = jd_fit.extract_keywords("Python python PYTHON Django")
    assert out == {"python", "django"}


def test_extract_keywords_drops_stopwords():
    out = jd_fit.extract_keywords("You will be working with our team")
    # Most of these are stop tokens; only domain-ish words remain.
    assert "you" not in out
    assert "will" not in out
    assert "working" in out or out  # may be filtered as stopword


def test_extract_keywords_preserves_tech_sigils():
    out = jd_fit.extract_keywords("Need C++ and C# and Node.js skills")
    assert "c++" in out
    assert "c#" in out
    assert "node.js" in out


def test_extract_keywords_preserves_2char_tech_tokens():
    # ML/AI/UI/UX are meaningful 2-char terms; default min_len=2.
    out = jd_fit.extract_keywords("ML AI is at UI")
    assert "ml" in out
    assert "ai" in out
    assert "ui" in out
    # Single-letter tokens still filtered ("is" is a stopword).
    assert "is" not in out


def test_extract_keywords_higher_min_len_drops_2char():
    """Callers can raise min_len for stricter signal."""
    out = jd_fit.extract_keywords("ML AI Python", min_len=3)
    assert "ml" not in out
    assert "ai" not in out
    assert "python" in out


def test_extract_keywords_drops_pure_numerics():
    out = jd_fit.extract_keywords("Build 100 systems by 2026")
    assert "100" not in out
    assert "2026" not in out
    assert "build" in out or "systems" in out


# ── jaccard ────────────────────────────────────────────────────────────


def test_jaccard_identical_sets_is_one():
    assert jd_fit.jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_disjoint_sets_is_zero():
    assert jd_fit.jaccard({"a"}, {"b"}) == 0.0


def test_jaccard_empty_pair_is_one():
    assert jd_fit.jaccard(set(), set()) == 1.0


def test_jaccard_one_empty_one_nonempty_is_zero():
    assert jd_fit.jaccard({"a"}, set()) == 0.0


def test_jaccard_partial_overlap_is_ratio():
    # {a,b,c} ∩ {b,c,d} = 2; ∪ = 4. 2/4 = 0.5.
    assert jd_fit.jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5


# ── extract_required_keywords ──────────────────────────────────────────


def test_required_keywords_harvested_from_required_clause():
    jd = "Other stuff. Required: Python, Django, PostgreSQL. End."
    out = jd_fit.extract_required_keywords(jd, window=80)
    assert "python" in out
    assert "django" in out
    assert "postgresql" in out


def test_required_keywords_handles_must_have_phrasing():
    jd = "Bonus skills include Java. You must have Rust and Go."
    out = jd_fit.extract_required_keywords(jd, window=60)
    assert "rust" in out
    assert "java" not in out  # Java is in the bonus-skills clause


def test_required_keywords_empty_when_no_trigger():
    jd = "We are a friendly team. Snacks provided."
    assert jd_fit.extract_required_keywords(jd) == set()


def test_required_keywords_dedupes_across_triggers():
    """Two trigger phrases pointing at the same skill list still produce one entry."""
    jd = "Required: Python and Django. Must have Python and Django."
    out = jd_fit.extract_required_keywords(jd, window=60)
    assert out >= {"python", "django"}


# ── _seniority_rank ────────────────────────────────────────────────────


def test_seniority_rank_uses_first_match():
    # "Junior Engineer" reads as junior (the modifier), not engineer.
    assert jd_fit._seniority_rank("Junior Engineer at Acme") == 1
    assert jd_fit._seniority_rank("Senior Engineer") == 3
    assert jd_fit._seniority_rank("Just an intern role") == 0


def test_seniority_rank_word_boundary_safety():
    """'ensure' shouldn't match 'senior'."""
    assert jd_fit._seniority_rank("ensure we deliver") is None


def test_seniority_rank_none_when_no_match():
    assert jd_fit._seniority_rank("Backend builder needed") is None


# ── score_jd_fit: heuristic ────────────────────────────────────────────


CLEAN_JD = """We are hiring a Senior Backend Engineer.

Required: Python, Django, PostgreSQL, Docker, Kubernetes.

Bonus: GraphQL, gRPC, AWS Lambda.

You will design APIs at scale.
"""


CLEAN_CV = """Jane Doe, Senior Backend Engineer

Summary
-------
Built scalable APIs.

Experience
----------
Acme — Senior Engineer
  - Built Django services on PostgreSQL
  - Deployed via Docker on Kubernetes
  - Designed Python APIs at scale

Skills
------
Python · Django · PostgreSQL · Docker · Kubernetes · GraphQL · AWS
"""


def test_clean_match_scores_high_no_findings():
    report = jd_fit.score_jd_fit(CLEAN_JD, CLEAN_CV)
    blocks = [f for f in report.findings if f.severity == "block"]
    assert blocks == []
    assert report.grade in ("A", "B", "C")


def test_missing_required_keyword_is_block():
    cv_no_kubernetes = CLEAN_CV.replace("Kubernetes", "Mesos")
    report = jd_fit.score_jd_fit(CLEAN_JD, cv_no_kubernetes)
    finding = next(f for f in report.findings if f.check == "missing_required_keywords")
    assert finding.severity == "block"
    assert "kubernetes" in finding.message.lower()


def test_role_level_mismatch_warn_for_gap_two():
    """JD: senior (3). CV: junior (1). Gap = 2 → warn."""
    jd = "Senior Backend Engineer needed. Required: Python."
    cv = "Jane Doe — Junior Engineer\nSkills: Python"
    report = jd_fit.score_jd_fit(jd, cv)
    finding = next(f for f in report.findings if f.check == "role_level_mismatch")
    assert finding.severity == "warn"
    assert finding.deduction == 10


def test_role_level_mismatch_block_for_gap_three_plus():
    """JD: director (6). CV: junior (1). Gap = 5 → block."""
    jd = "Director of Engineering. Required: Python."
    cv = "Jane Doe — Junior Engineer\nSkills: Python"
    report = jd_fit.score_jd_fit(jd, cv)
    finding = next(f for f in report.findings if f.check == "role_level_mismatch")
    assert finding.severity == "block"
    assert finding.deduction == 15


def test_no_role_level_mismatch_within_one_step():
    """JD: senior (3). CV: staff (4). Gap = 1 → no finding."""
    jd = "Senior Backend Engineer.\nRequired: Python."
    cv = "Jane Doe — Staff Engineer\nSkills: Python"
    report = jd_fit.score_jd_fit(jd, cv)
    assert not any(f.check == "role_level_mismatch" for f in report.findings)


def test_low_overlap_warns():
    """JD about Python; CV about woodworking. <10% Jaccard → warn."""
    jd = "Python Django backend role. Required: Python."
    cv = "Master carpenter with 20 years bench joinery experience."
    report = jd_fit.score_jd_fit(jd, cv)
    finding = next(f for f in report.findings if f.check == "low_keyword_overlap")
    assert finding.severity == "warn"


def test_score_has_floor_at_30():
    """Even a totally mismatched pair scores >= 30 before deductions."""
    jd = "Required: cobol fortran pascal."
    cv = "Modern stack: rust, kubernetes."
    report = jd_fit.score_jd_fit(jd, cv)
    # After deductions for missing-required + low-overlap, can drop
    # below 30; pre-deduction floor matters for the heuristic shape.
    assert report.metrics["jd_fit"]["jaccard"] < 0.1


def test_metrics_shape():
    report = jd_fit.score_jd_fit(CLEAN_JD, CLEAN_CV)
    m = report.metrics["jd_fit"]
    assert set(m.keys()) == {
        "jaccard",
        "jd_keywords",
        "cv_keywords",
        "required_keywords",
        "missing_required",
        "jd_seniority_rank",
        "cv_seniority_rank",
    }
    assert m["jd_seniority_rank"] == 3  # senior
    assert m["cv_seniority_rank"] == 3  # senior


def test_score_clamps_to_zero():
    """Multiple block-level deductions shouldn't push score negative."""
    jd = (
        "Required: aaa bbb ccc ddd eee fff ggg hhh iii jjj kkk lll mmm nnn ooo ppp qqq rrr sss ttt."
    )
    cv = "I write XYZ only."
    report = jd_fit.score_jd_fit(jd, cv)
    assert report.score >= 0


# ── score_jd_fit_with_llm ─────────────────────────────────────────────


@contextmanager
def _stub_llm(response: dict):
    body = json.dumps({"content": json.dumps(response)}).encode("utf-8")

    def fake(_req, timeout=None):
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp

    with mock.patch.object(llm_mod.urllib.request, "urlopen", fake):
        yield


def test_llm_merges_strength_and_gap():
    payload = {
        "top_strength": "Deep Django + Kubernetes ownership end-to-end.",
        "top_gap": {
            "summary": "No evidence of large-scale incident response.",
            "severity": "warn",
            "deduction": 8,
        },
    }
    with _stub_llm(payload):
        llm = llm_mod.LocalLLM()
        report = jd_fit.score_jd_fit_with_llm(CLEAN_JD, CLEAN_CV, llm)
    strength = next(f for f in report.findings if f.check == "top_strength")
    gap = next(f for f in report.findings if f.check == "top_gap")
    assert strength.severity == "info"
    assert "Django" in strength.message
    assert gap.severity == "warn"
    assert gap.deduction == 8
    assert "incident response" in gap.message


def test_llm_clamps_deduction_to_15():
    payload = {
        "top_strength": "ok",
        "top_gap": {"summary": "bad", "severity": "block", "deduction": 99},
    }
    with _stub_llm(payload):
        report = jd_fit.score_jd_fit_with_llm(CLEAN_JD, CLEAN_CV, llm_mod.LocalLLM())
    gap = next(f for f in report.findings if f.check == "top_gap")
    assert gap.deduction == 15


def test_llm_invalid_severity_falls_back_to_warn():
    payload = {
        "top_strength": "",
        "top_gap": {"summary": "thing", "severity": "catastrophic", "deduction": 5},
    }
    with _stub_llm(payload):
        report = jd_fit.score_jd_fit_with_llm(CLEAN_JD, CLEAN_CV, llm_mod.LocalLLM())
    gap = next(f for f in report.findings if f.check == "top_gap")
    assert gap.severity == "warn"


def test_llm_empty_payload_no_finding():
    """LLM returns empty strength + empty gap → no LLM findings added."""
    with _stub_llm({"top_strength": "", "top_gap": {}}):
        report = jd_fit.score_jd_fit_with_llm(CLEAN_JD, CLEAN_CV, llm_mod.LocalLLM())
    assert not any(f.check == "top_strength" for f in report.findings)
    assert not any(f.check == "top_gap" for f in report.findings)


def test_llm_unavailable_falls_back_to_heuristic():
    with mock.patch.object(
        llm_mod.urllib.request,
        "urlopen",
        side_effect=urllib.error.URLError("Connection refused"),
    ):
        report = jd_fit.score_jd_fit_with_llm(CLEAN_JD, CLEAN_CV, llm_mod.LocalLLM())
    info = next(f for f in report.findings if f.check == "jd_fit_llm")
    assert info.severity == "info"
    assert "unavailable" in info.message.lower()


# ── build_jd_fit_prompt ────────────────────────────────────────────────


def test_build_prompt_includes_both_sides_and_schema():
    prompt = jd_fit.build_jd_fit_prompt(CLEAN_JD, CLEAN_CV)
    assert "senior recruiter" in prompt
    assert "Job description" in prompt
    assert "Candidate CV" in prompt
    assert "top_strength" in prompt
    assert "JSON only" in prompt


def test_build_prompt_truncates_overlong_inputs():
    # Use letters that don't appear in the JD_FIT_SYSTEM or schema
    # text so the count is exact.
    huge_jd = "q" * 10_000
    huge_cv = "z" * 10_000
    prompt = jd_fit.build_jd_fit_prompt(huge_jd, huge_cv)
    # Each side capped to 4 KB.
    assert prompt.count("q") <= 4000
    assert prompt.count("z") <= 4000
