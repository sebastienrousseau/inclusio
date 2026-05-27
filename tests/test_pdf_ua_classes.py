"""Sprint 2: per-class tagged-PDF retrofit regression suite.

For every shipped `pub-*.cls`, compile a minimal document with
\\DocumentMetadata + [tagged] and assert the resulting PDF passes
PDF/UA-2 + WTPDF-1.0-Accessibility veraPDF validation.

A class that fails here either (a) needs markup-level retrofit (custom
title page, two-column layout, etc. that confuses the kernel's tagger)
or (b) hits a known PDF/A-4 embedded-file rule that Sprint 2 also
tracks.

The shipped result tells the Sprint 2 deliverables list which classes
are clean and which still need work. Classes marked `xfail` here are
known-broken and tracked in `build/.audit/sprint-02/class-matrix.md`.
"""

import os
import shutil
import subprocess
from textwrap import dedent

import pytest

# Classes to exercise. Tuple format: (class_name, class_options).
CLASSES = [
    ("pub-base", ""),
    ("pub-paper", ""),
    ("pub-arxiv", ""),
    ("pub-preprint", ""),
    ("pub-prime", ""),
    ("pub-bio", ""),
    ("pub-cv", ""),
    ("pub-faq", ""),
    ("pub-guide", ""),
    ("pub-patent", ""),
    # pub-patent-us extends pub-patent — exercise the same surface.
    ("pub-patent-us", ""),
]


def _tex_for(cls, opts):
    opts_block = f"[final,tagged,{opts}]" if opts else "[final,tagged]"
    # PDF/A-4f (not plain a-4) is the right archival target alongside
    # PDF/UA-2: the kernel tagging project embeds two CSS files
    # (latex-list-css.html, latex-align-css.html) that are non-PDF/A,
    # and 4f is the variant explicitly designed to allow such
    # non-conformant embedded payloads.
    return dedent(
        rf"""\DocumentMetadata{{
          pdfversion   = 2.0,
          pdfstandard  = ua-2,
          pdfstandard  = a-4f,
          lang         = en-GB,
          testphase    = {{phase-III, table, math, sec-latex}},
        }}
        \documentclass{opts_block}{{{cls}}}
        \title{{Per-class smoke for {cls}}}
        \author{{Euxis Publisher}}
        \begin{{document}}
        \maketitle
        \section{{First heading}}
        A paragraph with \emph{{emphasis}} and a list:
        \begin{{itemize}}
          \item One
          \item Two
        \end{{itemize}}
        \section{{Second heading}}
        Another paragraph.
        \end{{document}}
        """
    )


def _has(tool):
    return shutil.which(tool) is not None


def _build(cls, opts, tmp_path, project_root):
    tex = tmp_path / f"smoke_{cls}.tex"
    tex.write_text(_tex_for(cls, opts), encoding="utf-8")
    env = os.environ.copy()
    env["TEXINPUTS"] = (
        f"{project_root / 'core' / 'cls'}:"
        f"{project_root / 'core' / 'sty'}:"
        f"{tmp_path}:"
    )
    result = subprocess.run(
        [
            "lualatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex.name,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        combined = (result.stdout + "\n" + result.stderr).lower()
        # Hard skip on environment provisioning issues only.
        infra = [
            "! latex error: file `tagpdf.sty' not found",
            "! latex error: file `latex-lab",
            "font map file",
            "mktexpk",
        ]
        if any(m in combined for m in infra):
            pytest.skip("TeX environment provisioning issue")
        # Otherwise let the assertion below capture the real failure
        # in a readable form.
    return result, tmp_path / f"smoke_{cls}.pdf"


def _verapdf(pdf, flavour):
    r = subprocess.run(
        ["verapdf", "--format", "text", "--flavour", flavour, str(pdf)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    line = (r.stdout or "").splitlines()[0] if r.stdout else ""
    return line.startswith("PASS"), line


@pytest.mark.skipif(not _has("lualatex"), reason="lualatex required")
@pytest.mark.parametrize("cls,opts", CLASSES, ids=lambda x: x if isinstance(x, str) else "opts")
def test_class_compiles_tagged(cls, opts, project_root, tmp_path):
    """[tagged] compile succeeds for {cls}."""
    result, pdf = _build(cls, opts, tmp_path, project_root)
    assert result.returncode == 0, (
        f"{cls} failed to compile with [tagged]:\n"
        + (result.stdout[-1500:] or "")
    )
    assert pdf.exists(), f"{cls}: no PDF produced"


@pytest.mark.skipif(
    not (_has("lualatex") and _has("verapdf")),
    reason="lualatex + verapdf both required",
)
@pytest.mark.parametrize("cls,opts", CLASSES, ids=lambda x: x if isinstance(x, str) else "opts")
def test_class_passes_pdf_ua2(cls, opts, project_root, tmp_path):
    """[tagged] PDF/UA-2 PASS for {cls}."""
    result, pdf = _build(cls, opts, tmp_path, project_root)
    if result.returncode != 0:
        pytest.skip(f"{cls} did not compile (see test_class_compiles_tagged)")
    ok, line = _verapdf(pdf, "ua2")
    assert ok, f"{cls} fails PDF/UA-2: {line}"


@pytest.mark.skipif(
    not (_has("lualatex") and _has("verapdf")),
    reason="lualatex + verapdf both required",
)
@pytest.mark.parametrize("cls,opts", CLASSES, ids=lambda x: x if isinstance(x, str) else "opts")
def test_class_passes_wtpdf_accessibility(cls, opts, project_root, tmp_path):
    """[tagged] WTPDF-Accessibility PASS for {cls}."""
    result, pdf = _build(cls, opts, tmp_path, project_root)
    if result.returncode != 0:
        pytest.skip(f"{cls} did not compile (see test_class_compiles_tagged)")
    ok, line = _verapdf(pdf, "wt1a")
    assert ok, f"{cls} fails WTPDF-Accessibility: {line}"


@pytest.mark.skipif(
    not (_has("lualatex") and _has("verapdf")),
    reason="lualatex + verapdf both required",
)
@pytest.mark.parametrize("cls,opts", CLASSES, ids=lambda x: x if isinstance(x, str) else "opts")
def test_class_passes_pdf_a_4f(cls, opts, project_root, tmp_path):
    """[tagged] PDF/A-4f PASS for {cls} (archival with embedded files)."""
    result, pdf = _build(cls, opts, tmp_path, project_root)
    if result.returncode != 0:
        pytest.skip(f"{cls} did not compile (see test_class_compiles_tagged)")
    ok, line = _verapdf(pdf, "4f")
    assert ok, f"{cls} fails PDF/A-4f: {line}"
