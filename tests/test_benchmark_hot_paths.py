# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""Hot-path micro-benchmarks (pytest-benchmark).

Run with:
    pytest tests/test_benchmark_hot_paths.py --benchmark-only

Targets the call sites that dominate `make build`, `make audit`, and
`make judge` end-to-end times. The fixtures use representative-but-
synthetic content so the benchmarks are deterministic and don't drift
when real CVs / papers change.

Performance budgets are documented in each test's docstring. We don't
fail CI on regression here — the suite is observational by default;
flip `--benchmark-compare-fail=mean:5%` against a saved baseline when
we want regression-gating.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Skip the whole module when pytest-benchmark isn't installed. The
# Build-Documents workflow intentionally doesn't pull the plugin (it
# only runs the LaTeX-shadow suites); the Engine-Validation workflow
# does. This guard keeps the former green without disabling
# benchmarks on the latter.
pytest.importorskip("pytest_benchmark")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def cv_text() -> str:
    """≈ 6 KB CV text (one page render, typical case)."""
    parts = [
        "Jane Doe",
        "jane.doe@example.com · +44 20 1234 5678 · London, UK",
        "",
        "Summary",
        "-------",
        "Senior platform engineer with 12 years of distributed-systems experience.",
        "",
        "Experience",
        "----------",
    ]
    for i in range(8):
        parts.extend(
            [
                "- Acme Corp · Staff Engineer (01/2020 – Present)",
                f"  - Led {i}-team migration to Kubernetes, cutting P95 latency 40%.",
                "  - Designed event-sourcing pipeline handling 12M events/day.",
                "  - Mentored 4 junior engineers through Senior promotion.",
                "",
            ]
        )
    parts.extend(
        [
            "Skills",
            "------",
            "Python · Go · Rust · Kubernetes · PostgreSQL · Kafka · gRPC · OpenTelemetry",
            "",
            "Education",
            "---------",
            "- MEng Computer Science | Imperial College London | 2013",
        ]
    )
    return "\n".join(parts)


@pytest.fixture(scope="module")
def jd_text() -> str:
    """≈ 1.5 KB job description (realistic Workday/Greenhouse posting)."""
    return (
        "Senior Platform Engineer — London\n\n"
        "We're hiring a senior platform engineer to scale our event "
        "pipeline. You will own infrastructure for our Kubernetes-based "
        "services and lead the team to a 99.95% SLO.\n\n"
        "Required:\n"
        "- 8+ years of backend experience in Python or Go\n"
        "- Production Kubernetes experience (operators, CRDs, autoscaling)\n"
        "- Strong PostgreSQL fundamentals (query plans, indexing strategy)\n"
        "- Distributed-systems intuition (consistency, idempotency, retries)\n\n"
        "Nice to have:\n"
        "- Rust experience\n"
        "- OpenTelemetry / Prometheus operational experience\n"
        "- Open-source contributions to relevant infrastructure\n"
    )


@pytest.fixture(scope="module")
def tex_with_citations() -> str:
    """≈ 4 KB LaTeX source with 12 \\cite + 8 \\bibitem entries."""
    body = "\n".join(f"In section {i}, we cite \\cite{{ref{i}}} for support." for i in range(12))
    bib = "\n".join(
        f"\\bibitem{{ref{i}}} Author {i}, et al. \\emph{{Title {i}}}. Journal {i}, 2024."
        for i in range(8)
    )
    return (
        r"\documentclass{article}"
        r"\begin{document}"
        + body
        + r"\begin{thebibliography}{99}"
        + bib
        + r"\end{thebibliography}\end{document}"
    )


@pytest.fixture(scope="module")
def cv_render_data() -> dict:
    """A canonical CV data structure for `render_text` benchmarking."""
    return {
        "title": "Jane Doe — CV",
        "summary": "Senior platform engineer with 12 years experience.",
        "experience": [
            {
                "company": f"Co{i}",
                "title": "Engineer",
                "location": "London, UK",
                "dates": "01/2020 – Present",
                "bullets": [f"Bullet {j} for company {i}" for j in range(5)],
            }
            for i in range(8)
        ],
        "skills": [{"title": "Python", "description": "12 years"}],
        "education": [{"degree": "MEng", "institution": "Imperial", "year": "2013"}],
    }


# ── Benchmarks ─────────────────────────────────────────────────────────
#
# Soft budgets (mean per call on a modern laptop, indicative only):
#   score_cv:                 < 1 ms
#   score_citations:          < 1 ms
#   extract_keywords (6 KB):  < 0.5 ms
#   jaccard (200 vs 200):     < 0.1 ms
#   build_manifest_json:      < 0.5 ms
#   render_text (CV):         < 5 ms


def test_bench_score_cv(benchmark, cv_text):
    """ATS heuristic scoring — runs on every `make judge` call."""
    from euxis_publisher.judge import ats

    result = benchmark(ats.score_cv, cv_text)
    assert result.score >= 0


def test_bench_score_citations(benchmark, tex_with_citations):
    """Citation grounding — runs on every `make judge JUDGE=citations`."""
    from euxis_publisher.judge import citations

    result = benchmark(citations.score_citations, tex_with_citations)
    assert result.score >= 0


def test_bench_extract_keywords(benchmark, cv_text):
    """Hot loop inside `score_jd_fit` — runs once per judge invocation."""
    from euxis_publisher.judge import jd_fit

    out = benchmark(jd_fit.extract_keywords, cv_text)
    assert isinstance(out, set)
    assert len(out) > 20


def test_bench_jaccard(benchmark):
    """Set similarity — called once per `score_jd_fit`. Tiny but ubiquitous."""
    from euxis_publisher.judge import jd_fit

    a = {f"term{i}" for i in range(200)}
    b = {f"term{i}" for i in range(100, 300)}
    out = benchmark(jd_fit.jaccard, a, b)
    assert 0.0 <= out <= 1.0


def test_bench_parse_citations(benchmark, tex_with_citations):
    """\\cite extraction — runs first in every citations judge pass."""
    from euxis_publisher.judge import citations

    out = benchmark(citations.parse_citations, tex_with_citations)
    assert len(out) >= 12


def test_bench_parse_bibitems(benchmark, tex_with_citations):
    """\\bibitem extraction — paired with parse_citations on every audit."""
    from euxis_publisher.judge import citations

    out = benchmark(citations.parse_bibitems, tex_with_citations)
    assert len(out) >= 8


def test_bench_score_jd_fit(benchmark, jd_text, cv_text):
    """End-to-end JD↔CV fit scoring. Dominant judge cost when present."""
    from euxis_publisher.judge import jd_fit

    result = benchmark(jd_fit.score_jd_fit, jd_text, cv_text)
    assert result.score >= 0


def test_bench_render_text(benchmark, cv_render_data):
    """Plain-text render path — drives ATS-shadow generation on every build."""
    from euxis_publisher.cli import render

    out = benchmark(render.render_text, cv_render_data, "cv")
    assert isinstance(out, str)
    assert "Experience" in out


def test_bench_build_manifest_json(benchmark, tmp_path):
    """C2PA manifest assembly — runs once per camera-ready PDF."""
    from euxis_publisher.provenance import c2pa

    out = benchmark(
        c2pa.build_manifest_json,
        title="Test Document",
        author="Sebastien Rousseau",
        date_published="2026-05-28",
        ai_disclosure="ai-edits-only",
    )
    payload = json.loads(out)
    # Sanity: the manifest carries a claim_generator and the CreativeWork.
    assert "claim_generator" in payload
    assert any(
        a.get("label") == "stds.schema-org.CreativeWork" for a in payload.get("assertions", [])
    )
