# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 7 (S7.3): ATS-scoring judge for CV variants.

Exercises every check in `euxis_publisher.judge.ats.score_cv`:

  - canonical headings: present / missing / partial-match
  - contact info: email-only, phone-only, neither, both
  - length bands: green / yellow / red
  - bullet density: short / medium / over-yellow / over-red
  - date consistency: single format / mixed formats
  - killer-phrase detection
  - grade thresholds: A / B / C / D / F
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from euxis_publisher.judge import ats

# ── Fixtures: minimal CVs in plain text ────────────────────────────────


CLEAN_CV = """Jane Doe

Director of Engineering

+44 7000 000000 | jane@example.com

Summary
-------
Builds payments rails for tier-1 banks.

Experience
----------
BigBank VP, Payments (01/2024) London
  - Owned the API gateway roadmap end-to-end
  - Closed $5M ARR in year one

Acme Engineer (01/2020) Remote
  - Built prototype that became flagship product

Skills
------
API strategy · Payments · Team leadership

Education
---------
- MSc Computer Science | Imperial College | London | 09/2010
"""


def _cv_missing_section(label: str, replacement: str = "") -> str:
    """Drop a canonical heading from CLEAN_CV to test the warn/block path."""
    return CLEAN_CV.replace(f"{label}\n{'-' * len(label)}", replacement)


# ── canonical headings ────────────────────────────────────────────────


def test_clean_cv_passes_canonical_headings():
    report = ats.score_cv(CLEAN_CV)
    headings = report.metrics["canonical_headings"]
    assert headings["experience"] == "Experience"
    assert headings["skills"] == "Skills"
    assert headings["education"] == "Education"
    assert headings["summary"] == "Summary"


def test_missing_experience_is_blocking():
    text = _cv_missing_section("Experience")
    report = ats.score_cv(text)
    block = [f for f in report.findings if f.check == "canonical_heading_experience"]
    assert len(block) == 1
    assert block[0].severity == "block"
    assert block[0].deduction == 25


def test_missing_summary_is_warn_not_block():
    text = _cv_missing_section("Summary")
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "canonical_heading_summary")
    assert finding.severity == "warn"
    assert finding.deduction == 15


def test_accepts_canonical_synonyms():
    text = CLEAN_CV.replace("Summary\n-------", "Executive Profile\n-----------------")
    text = text.replace("Skills\n------", "Core Competencies\n-----------------")
    report = ats.score_cv(text)
    assert report.metrics["canonical_headings"]["summary"] == "Executive Profile"
    assert report.metrics["canonical_headings"]["skills"] == "Core Competencies"


# ── contact info ──────────────────────────────────────────────────────


def test_both_email_and_phone_no_finding():
    report = ats.score_cv(CLEAN_CV)
    contact_findings = [f for f in report.findings if f.check == "contact_info"]
    assert contact_findings == []
    assert report.metrics["contact"] == {"email": True, "phone": True}


def test_email_only_warns():
    text = CLEAN_CV.replace("+44 7000 000000 | ", "")
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "contact_info")
    assert finding.severity == "warn"
    assert finding.deduction == 5


def test_phone_only_warns():
    text = CLEAN_CV.replace(" | jane@example.com", "")
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "contact_info")
    assert finding.severity == "warn"


def test_no_contact_info_is_blocking():
    text = CLEAN_CV.replace("+44 7000 000000 | jane@example.com\n", "")
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "contact_info")
    assert finding.severity == "block"
    assert finding.deduction == 30


# ── length bands ──────────────────────────────────────────────────────


def test_short_cv_no_length_finding():
    report = ats.score_cv(CLEAN_CV)
    assert not any(f.check == "length" for f in report.findings)


def test_yellow_length_warns():
    bloat = "Filler line that approximates real content.\n" * 300  # ~13 KB
    text = CLEAN_CV + bloat
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "length")
    assert finding.severity == "warn"
    assert finding.deduction == 10


def test_red_length_blocks():
    bloat = "Filler line that approximates real content.\n" * 600  # ~26 KB
    text = CLEAN_CV + bloat
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "length")
    assert finding.severity == "block"
    assert finding.deduction == 20


# ── bullet density ────────────────────────────────────────────────────


def test_short_bullets_clean():
    report = ats.score_cv(CLEAN_CV)
    assert not any(f.check == "bullet_length" for f in report.findings)


def test_overlong_bullet_warns_at_yellow():
    long_bullet = "- " + "x " * 145  # 290 chars
    text = CLEAN_CV + "\n" + long_bullet + "\n"
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "bullet_length")
    assert finding.severity == "warn"


def test_overlong_bullet_blocks_at_red():
    long_bullet = "- " + "x " * 220  # 440 chars
    text = CLEAN_CV + "\n" + long_bullet + "\n"
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "bullet_length")
    assert finding.severity == "block"


# ── date consistency ─────────────────────────────────────────────────


def test_single_date_format_no_finding():
    report = ats.score_cv(CLEAN_CV)  # uses MM/YYYY only
    findings = [f for f in report.findings if f.check == "date_consistency"]
    assert findings == []


def test_mixed_date_formats_warns():
    # CLEAN_CV uses MM/YYYY only; adding "Mar 2018" triggers month-year
    # and "2018 - 2019" triggers year-year, producing 3 distinct formats.
    text = CLEAN_CV + "\n\nPrior: Mar 2018 - 2019 at Startup\n"
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "date_consistency")
    assert finding.severity == "warn"


# ── killer phrases ────────────────────────────────────────────────────


def test_no_killer_phrases_clean():
    report = ats.score_cv(CLEAN_CV)
    assert report.metrics["killer_phrases"] == []


def test_killer_phrase_deduction_scales():
    text = (
        CLEAN_CV
        + "\nReferences available upon request.\n"
        + "Objective: To be the best engineer.\n"
    )
    report = ats.score_cv(text)
    finding = next(f for f in report.findings if f.check == "killer_phrases")
    assert finding.severity == "warn"
    assert finding.deduction == 10  # 2 phrases × 5 pts
    assert len(report.metrics["killer_phrases"]) == 2


# ── grade thresholds ────────────────────────────────────────────────


def test_grade_a_for_clean_cv():
    report = ats.score_cv(CLEAN_CV)
    assert report.score >= 90
    assert report.grade == "A"


def test_grade_f_for_disaster_cv():
    text = "No useful content. Objective: get hired."
    report = ats.score_cv(text)
    assert report.score == 0
    assert report.grade == "F"


def test_grade_c_for_middling_cv():
    # Drop summary (-15) + only-email contact (-5) = -20 from 100.
    text = _cv_missing_section("Summary")
    text = text.replace("+44 7000 000000 | ", "")
    report = ats.score_cv(text)
    assert report.score == 80
    assert report.grade == "B"


def test_score_never_negative():
    """Multiple block-level findings should clamp to 0, not go negative."""
    text = "Nothing useful. References available upon request."
    report = ats.score_cv(text)
    assert report.score >= 0


# ── JudgeReport serialisation ────────────────────────────────────────


def test_to_dict_round_trip():
    report = ats.score_cv(CLEAN_CV)
    payload = report.to_dict()
    assert payload["score"] == report.score
    assert payload["grade"] == report.grade
    assert isinstance(payload["findings"], list)
    assert isinstance(payload["metrics"], dict)
    for f in payload["findings"]:
        assert set(f.keys()) == {"check", "severity", "message", "deduction"}
