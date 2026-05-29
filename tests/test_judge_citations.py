# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Sprint 7 (S7.2): citation-grounding judge.

Exercises:
  - `parse_citations` / `parse_bibitems` against the canonical
    LaTeX citation variants (\\cite, \\citep, \\citet, \\citeauthor,
    multi-key \\cite{a,b,c}, optional [label] on \\bibitem).
  - heuristic `score_citations` against every documented failure
    mode (dangling, unused, duplicate, missing-bibliography,
    no-citations) and the clean path.
  - LLM-backed `score_citations_with_llm` against:
      - supported citation (no extra finding)
      - mis-attributed citation (warn -5)
      - LLM unavailable (graceful fallback)
      - max_checks cap honoured
"""

from __future__ import annotations

import json
import sys
import urllib.error
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inclusio.judge import citations as cit
from inclusio.judge import local_llm as llm_mod

# ── Fixtures ───────────────────────────────────────────────────────────


CLEAN_PAPER = r"""\documentclass{article}
\begin{document}
\section{Introduction}
Prior work \cite{smith2024} established the foundation; we extend
\citep{jones2025} with a new bound \cite{lee2023,park2024}.

\begin{thebibliography}{9}
\bibitem{smith2024} Smith, J. (2024). Foundation paper. \emph{ACM TOIT}.
\bibitem{jones2025} Jones, A. (2025). Extension. \emph{NeurIPS}.
\bibitem{lee2023} Lee, K. (2023). Bound theorem. \emph{ICML}.
\bibitem{park2024} Park, M. (2024). Tighter bound. \emph{STOC}.
\end{thebibliography}
\end{document}
"""


# ── parse_citations ───────────────────────────────────────────────────


def test_parse_citations_extracts_cite():
    citations = cit.parse_citations(r"See \cite{smith2024} for details.")
    assert [c.key for c in citations] == ["smith2024"]


def test_parse_citations_handles_multi_key():
    citations = cit.parse_citations(r"As shown in \cite{a, b, c}.")
    assert [c.key for c in citations] == ["a", "b", "c"]


def test_parse_citations_handles_citep_citet_variants():
    citations = cit.parse_citations(r"\citep{first} and \citet{second} plus \citeauthor{third}")
    assert [c.key for c in citations] == ["first", "second", "third"]


def test_parse_citations_records_line_numbers():
    tex = "line one\n\\cite{key1}\nline three\n\\cite{key2}"
    citations = cit.parse_citations(tex)
    assert [c.line for c in citations] == [2, 4]


def test_parse_citations_handles_optional_brackets():
    citations = cit.parse_citations(r"\cite[p.~42]{smith}")
    assert citations[0].key == "smith"


def test_parse_citations_captures_context():
    tex = "The seminal result \\cite{smith} proves the bound."
    citations = cit.parse_citations(tex)
    assert "seminal result" in citations[0].context
    assert "proves the bound" in citations[0].context


def test_parse_citations_returns_empty_for_no_cites():
    assert cit.parse_citations(r"No citations here.") == []


# ── parse_bibitems ────────────────────────────────────────────────────


def test_parse_bibitems_extracts_key_and_text():
    tex = r"\bibitem{smith2024} Smith, J. (2024). Paper title."
    items = cit.parse_bibitems(tex)
    assert items[0].key == "smith2024"
    assert "Smith, J. (2024)" in items[0].text


def test_parse_bibitems_handles_label():
    items = cit.parse_bibitems(r"\bibitem[Smith24]{smith2024} Body.")
    assert items[0].key == "smith2024"


def test_parse_bibitems_strips_inline_markup():
    items = cit.parse_bibitems(r"\bibitem{x} \emph{Title} by \textbf{Author}. \textit{Journal}.")
    assert "\\emph" not in items[0].text
    assert "\\textbf" not in items[0].text
    assert "Title" in items[0].text


def test_parse_bibitems_terminates_at_end_of_bibliography():
    tex = (
        r"\begin{thebibliography}{9}"
        r"\bibitem{first} First. \bibitem{second} Second."
        r"\end{thebibliography}"
        r"\section{Closing} Trailing prose with no bibitem."
    )
    items = cit.parse_bibitems(tex)
    assert len(items) == 2
    # The "Trailing prose" must not leak into the second bibitem's text.
    assert "Trailing prose" not in items[1].text


def test_parse_bibitems_multiple_entries_in_order():
    items = cit.parse_bibitems(CLEAN_PAPER)
    keys = [b.key for b in items]
    assert keys == ["smith2024", "jones2025", "lee2023", "park2024"]


# ── score_citations: heuristic ────────────────────────────────────────


def test_clean_paper_scores_high():
    report = cit.score_citations(CLEAN_PAPER)
    assert report.score >= 90
    assert report.grade == "A"


def test_clean_paper_metrics():
    report = cit.score_citations(CLEAN_PAPER)
    m = report.metrics["citation_counts"]
    assert m["total_cites"] == 4
    assert m["unique_keys"] == 4
    assert m["bibitems"] == 4
    assert m["dangling"] == 0
    assert m["unused"] == 0


def test_dangling_citation_is_blocking():
    tex = (
        r"\cite{exists} and \cite{ghost}"
        r"\begin{thebibliography}{9}\bibitem{exists}A.\end{thebibliography}"
    )
    report = cit.score_citations(tex)
    finding = next(f for f in report.findings if f.check == "dangling_citation")
    assert finding.severity == "block"
    assert finding.deduction == cit.DANGLING_BLOCK_DEDUCTION_PER_KEY


def test_dangling_deduction_caps_at_max():
    tex = " ".join(rf"\cite{{ghost{i}}}" for i in range(10))
    report = cit.score_citations(tex)
    finding = next(f for f in report.findings if f.check == "dangling_citation")
    assert finding.deduction == cit.DANGLING_MAX_DEDUCTION


def test_unused_bibitem_warns():
    tex = (
        r"\cite{used}"
        r"\begin{thebibliography}{9}"
        r"\bibitem{used}A.\bibitem{ignored}B."
        r"\end{thebibliography}"
    )
    report = cit.score_citations(tex)
    finding = next(f for f in report.findings if f.check == "unused_bibitem")
    assert finding.severity == "warn"
    assert "ignored" in finding.message


def test_duplicate_bibitem_warns():
    tex = (
        r"\cite{dup}"
        r"\begin{thebibliography}{9}"
        r"\bibitem{dup}First copy.\bibitem{dup}Second copy."
        r"\end{thebibliography}"
    )
    report = cit.score_citations(tex)
    finding = next(f for f in report.findings if f.check == "duplicate_bibitem")
    assert finding.severity == "warn"
    assert finding.deduction == cit.DUPLICATE_DEDUCTION_PER_KEY


def test_missing_bibliography_blocks():
    tex = r"Body with \cite{smith} and \cite{jones} but no bibitems."
    report = cit.score_citations(tex)
    finding = next(f for f in report.findings if f.check == "missing_bibliography")
    assert finding.severity == "block"
    assert finding.deduction == 50


def test_no_citations_no_bibitems_is_info_not_warn():
    report = cit.score_citations(r"Pure review note. No references.")
    finding = next(f for f in report.findings if f.check == "no_citations")
    assert finding.severity == "info"
    assert finding.deduction == 0
    assert report.score == 100  # No deduction.


def test_bibitems_without_citations_warns():
    tex = (
        r"\begin{thebibliography}{9}"
        r"\bibitem{lonely}Lonely.\end{thebibliography}"
    )
    report = cit.score_citations(tex)
    finding = next(f for f in report.findings if f.check == "no_citations")
    assert finding.severity == "warn"
    assert finding.deduction == 10


# ── LLM-backed grounding ───────────────────────────────────────────────


@contextmanager
def _stub_llm_responses(responses: list[dict] | dict):
    """Patch urllib.request.urlopen to walk through *responses* in order."""
    if isinstance(responses, dict):
        responses = [responses]
    counter = {"idx": 0}

    def fake_urlopen(req, timeout=None):
        idx = counter["idx"]
        counter["idx"] += 1
        body = json.dumps({"content": json.dumps(responses[min(idx, len(responses) - 1)])}).encode(
            "utf-8"
        )
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp

    with mock.patch.object(llm_mod.urllib.request, "urlopen", fake_urlopen):
        yield counter


def test_llm_grounding_no_flag_when_all_supported():
    llm = llm_mod.LocalLLM()
    with _stub_llm_responses({"supported": True, "confidence": 0.9, "reason": "ok"}):
        report = cit.score_citations_with_llm(CLEAN_PAPER, llm)
    assert not any(f.check == "citation_grounding" for f in report.findings)


def test_llm_grounding_flags_unsupported_high_confidence():
    llm = llm_mod.LocalLLM()
    with _stub_llm_responses(
        {"supported": False, "confidence": 0.85, "reason": "Bibitem is about X, claim is about Y."}
    ):
        report = cit.score_citations_with_llm(CLEAN_PAPER, llm)
    grounding = [f for f in report.findings if f.check == "citation_grounding"]
    assert len(grounding) >= 1
    assert grounding[0].severity == "warn"
    assert grounding[0].deduction == 5
    assert "Bibitem is about X" in grounding[0].message


def test_llm_grounding_ignores_low_confidence_unsupported():
    """confidence < 0.6 isn't conclusive enough to flag."""
    llm = llm_mod.LocalLLM()
    with _stub_llm_responses({"supported": False, "confidence": 0.4, "reason": "maybe"}):
        report = cit.score_citations_with_llm(CLEAN_PAPER, llm)
    assert not any(f.check == "citation_grounding" for f in report.findings)


def test_llm_grounding_respects_max_checks_cap():
    """Even with 4 citations, max_checks=2 hits LLM twice only."""
    llm = llm_mod.LocalLLM()
    with _stub_llm_responses({"supported": True, "confidence": 0.9, "reason": "ok"}) as ctr:
        cit.score_citations_with_llm(CLEAN_PAPER, llm, max_checks=2)
    assert ctr["idx"] == 2


def test_llm_unavailable_falls_back_gracefully():
    """ECONNREFUSED → info breadcrumb, heuristic preserved."""
    llm = llm_mod.LocalLLM()
    with mock.patch.object(
        llm_mod.urllib.request,
        "urlopen",
        side_effect=urllib.error.URLError("Connection refused"),
    ):
        report = cit.score_citations_with_llm(CLEAN_PAPER, llm)
    info = next(f for f in report.findings if f.check == "citation_grounding_llm")
    assert info.severity == "info"
    assert "unavailable" in info.message.lower()
    # Heuristic score still A.
    assert report.grade == "A"


def test_llm_grounding_dedupes_repeated_citation():
    """A key cited twice that the LLM flags both times scores only one finding."""
    tex = (
        r"First mention \cite{dup} ... second mention \cite{dup}"
        r"\begin{thebibliography}{9}\bibitem{dup}D.\end{thebibliography}"
    )
    llm = llm_mod.LocalLLM()
    with _stub_llm_responses({"supported": False, "confidence": 0.9, "reason": "bad attribution"}):
        report = cit.score_citations_with_llm(tex, llm)
    grounding = [f for f in report.findings if f.check == "citation_grounding"]
    assert len(grounding) == 1


def test_llm_grounding_no_matched_citations_is_noop():
    """Paper with only dangling citations has nothing for the LLM to check."""
    tex = r"\cite{ghost1} \cite{ghost2}"
    llm = llm_mod.LocalLLM()
    with _stub_llm_responses({"supported": True, "confidence": 1.0, "reason": "x"}) as ctr:
        cit.score_citations_with_llm(tex, llm)
    # LLM never called — nothing matched.
    assert ctr["idx"] == 0


# ── build_grounding_prompt ────────────────────────────────────────────


def test_build_grounding_prompt_includes_both_sides():
    citation = cit.Citation(key="smith", context="The bound is tight.", line=42)
    bibitem = cit.BibItem(key="smith", text="Smith. Bound theorem. STOC.", line=99)
    prompt = cit.build_grounding_prompt(citation, bibitem)
    assert "academic citation reviewer" in prompt
    assert "smith" in prompt
    assert "tight" in prompt
    assert "Bound theorem" in prompt
    assert "JSON only" in prompt
