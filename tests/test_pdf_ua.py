"""Sprint 1+: PDF/UA-2 + WTPDF-1.0 tagged-PDF regression tests.

These tests compile a minimal LaTeX document via the [tagged] class
option + \\DocumentMetadata and require that the resulting PDF passes
veraPDF validation for PDF/UA-2 and the WTPDF 1.0 Accessibility
profile.

The test is skipped when:
  - LuaLaTeX is not installed (decision D3 hard-requires it, but the
    CI matrix may not always include it on every runner)
  - veraPDF is not installed (only present on the audit job)
  - tagpdf.sty is not available (TeX Live 2024+ ships it)

veraPDF is invoked via `verapdf --format text --flavour <flavour>` and
parses the PASS/FAIL prefix on the only output line.
"""

import os
import shutil
import subprocess

import pytest


TAGGED_SMOKE_TEX = r"""\DocumentMetadata{
  pdfversion   = 2.0,
  pdfstandard  = ua-2,
  pdfstandard  = a-4,
  lang         = en-GB,
  testphase    = {phase-III, table, math, sec-latex},
}
\documentclass[final,tagged]{pub-base}
\title{Tagged PDF smoke test}
\author{Euxis Publisher}
\begin{document}
\maketitle
\section{First heading}
A paragraph with \emph{emphasised text} and a list:
\begin{itemize}
  \item One
  \item Two
\end{itemize}
\section{Second heading}
Another paragraph to ensure paragraph-level tagging works across sections.
\end{document}
"""


def _has(tool):
    return shutil.which(tool) is not None


def _build(tmp_path, project_root):
    tex = tmp_path / "tagged_smoke.tex"
    tex.write_text(TAGGED_SMOKE_TEX, encoding="utf-8")

    cache = tmp_path / ".texmf-cache"
    cache.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["TEXINPUTS"] = (
        f"{project_root / 'core' / 'cls'}:"
        f"{project_root / 'core' / 'sty'}:"
        f"{tmp_path}:"
    )
    env["TEXMFCACHE"] = str(cache)
    env["TEXMFVAR"] = str(cache)
    env["TEXMFSYSVAR"] = str(cache)

    result = subprocess.run(
        [
            "lualatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "tagged_smoke.tex",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        combined = (result.stdout + "\n" + result.stderr).lower()
        infra_markers = [
            "no writeable cache path",
            "font map file",
            "mktexpk",
            "psfonts.map",
            "tagpdf.sty",
        ]
        if any(marker in combined for marker in infra_markers):
            pytest.skip(
                "TeX environment provisioning issue (cache/fonts/tagpdf)"
            )

    assert result.returncode == 0, (
        result.stdout[-1500:] + "\n" + result.stderr[-1500:]
    )
    pdf = tmp_path / "tagged_smoke.pdf"
    assert pdf.exists(), "smoke pdf not generated"
    return pdf


def _verapdf_passes(pdf, flavour):
    result = subprocess.run(
        ["verapdf", "--format", "text", "--flavour", flavour, str(pdf)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    first_line = (result.stdout or "").splitlines()[0] if result.stdout else ""
    return first_line.startswith("PASS"), first_line


@pytest.mark.skipif(not _has("lualatex"), reason="lualatex not installed")
def test_tagged_smoke_compiles(project_root, tmp_path):
    """[tagged] + \\DocumentMetadata produces a PDF with structure tagging."""
    pdf = _build(tmp_path, project_root)
    # The kernel writes the tag tree; pdfinfo lacks tagged detection on
    # all platforms, so use pdfinfo when present.
    if not _has("pdfinfo"):
        pytest.skip("pdfinfo not available — skipping Tagged: yes check")
    result = subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, timeout=30
    )
    assert "Tagged:          yes" in result.stdout, (
        "Expected 'Tagged: yes' in pdfinfo output:\n" + result.stdout
    )


@pytest.mark.skipif(
    not (_has("lualatex") and _has("verapdf")),
    reason="lualatex + verapdf both required",
)
def test_tagged_smoke_passes_pdf_ua2(project_root, tmp_path):
    """[tagged] PDF passes PDF/UA-2 conformance (ISO 14289-2:2024)."""
    pdf = _build(tmp_path, project_root)
    ok, line = _verapdf_passes(pdf, "ua2")
    assert ok, f"veraPDF UA-2 did not pass: {line}"


@pytest.mark.skipif(
    not (_has("lualatex") and _has("verapdf")),
    reason="lualatex + verapdf both required",
)
def test_tagged_smoke_passes_wtpdf_accessibility(project_root, tmp_path):
    """[tagged] PDF passes WTPDF 1.0 Accessibility profile."""
    pdf = _build(tmp_path, project_root)
    ok, line = _verapdf_passes(pdf, "wt1a")
    assert ok, f"veraPDF WTPDF-Accessibility did not pass: {line}"


@pytest.mark.skipif(not _has("lualatex"), reason="lualatex not installed")
def test_tagged_without_metadata_errors(project_root, tmp_path):
    """[tagged] without \\DocumentMetadata raises a class error."""
    tex = tmp_path / "missing_meta.tex"
    tex.write_text(
        r"""\documentclass[final,tagged]{pub-base}
\title{Missing meta}
\author{Tester}
\begin{document}\maketitle\end{document}
""",
        encoding="utf-8",
    )
    cache = tmp_path / ".texmf-cache"
    cache.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["TEXINPUTS"] = (
        f"{project_root / 'core' / 'cls'}:"
        f"{project_root / 'core' / 'sty'}:"
        f"{tmp_path}:"
    )
    env["TEXMFCACHE"] = str(cache)
    env["TEXMFVAR"] = str(cache)
    env["TEXMFSYSVAR"] = str(cache)

    result = subprocess.run(
        [
            "lualatex",
            "-interaction=nonstopmode",
            "missing_meta.tex",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined = result.stdout + "\n" + result.stderr
    assert "Class option [tagged] requires" in combined, (
        "Expected loud class error about missing \\DocumentMetadata. "
        "Output was:\n" + combined[-1500:]
    )


@pytest.mark.skipif(not _has("lualatex"), reason="lualatex not installed")
def test_final_untagged_escape_hatch(project_root, tmp_path):
    """[final-untagged] still compiles (legacy pdfx path) without tagging."""
    tex = tmp_path / "untagged.tex"
    tex.write_text(
        r"""\documentclass[final-untagged]{pub-base}
\title{Untagged escape}
\author{Tester}
\begin{document}\maketitle Hello.\end{document}
""",
        encoding="utf-8",
    )
    cache = tmp_path / ".texmf-cache"
    cache.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["TEXINPUTS"] = (
        f"{project_root / 'core' / 'cls'}:"
        f"{project_root / 'core' / 'sty'}:"
        f"{tmp_path}:"
    )
    env["TEXMFCACHE"] = str(cache)
    env["TEXMFVAR"] = str(cache)
    env["TEXMFSYSVAR"] = str(cache)

    result = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "untagged.tex"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        combined = (result.stdout + "\n" + result.stderr).lower()
        if any(m in combined for m in ["pdfx.sty", "font map file"]):
            pytest.skip("pdfx / fontmap not provisioned on this runner")
    assert result.returncode == 0, (
        result.stdout[-1500:] + "\n" + result.stderr[-1500:]
    )
    assert (tmp_path / "untagged.pdf").exists()
