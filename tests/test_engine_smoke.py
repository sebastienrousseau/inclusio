"""Smoke test: compile a minimal document through pub-base via TEXINPUTS."""

import os
import shutil
import subprocess

import pytest


def test_pub_base_smoke_compile(project_root, tmp_path):
    # LuaLaTeX is hard-required (decision D3, 2026-05-23).
    compiler = shutil.which("lualatex")
    if compiler is None:
        pytest.skip("LuaLaTeX not found (required since decision D3)")

    tex = tmp_path / "smoke.tex"
    tex.write_text(
        r"""\documentclass{pub-base}
\title{Smoke}
\author{Euxis Publisher}
\date{\today}
\begin{document}
\maketitle
Engine smoke compile.
\end{document}
""",
        encoding="utf-8",
    )

    cache_dir = tmp_path / ".texmf-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["TEXINPUTS"] = (
        f"{project_root / 'core' / 'cls'}:"
        f"{project_root / 'core' / 'sty'}:"
        f"{tmp_path}:"
    )
    env["TEXMFCACHE"] = str(cache_dir)
    env["TEXMFVAR"] = str(cache_dir)
    env["TEXMFSYSVAR"] = str(cache_dir)

    result = subprocess.run(
        [
            compiler,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "smoke.tex",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        combined = (result.stdout + "\n" + result.stderr).lower()
        infra_markers = [
            "no writeable cache path",
            "font map file",
            "font phvr8r",
            "mktexpk",
            "psfonts.map",
        ]
        if any(marker in combined for marker in infra_markers):
            pytest.skip("TeX environment provisioning issue (cache/font maps)")

    assert result.returncode == 0, result.stdout[-1200:] + "\n" + result.stderr[-1200:]
    assert (tmp_path / "smoke.pdf").exists(), "Expected smoke.pdf to be generated"
