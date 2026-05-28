#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
audit.py — EAA / WCAG 2.2 AA conformance audit for built PDFs.

Runs veraPDF against PDF/UA-2, WTPDF 1.0 Accessibility, and PDF/A-4f
flavours on a single PDF or every PDF under build/, and emits both a
machine-readable JSON report and a human-readable Markdown summary.

CI uses this in `--strict` mode to BLOCK release artefacts that fail
any of the three gates. Local users get the same report by running
`make audit`.

Usage:
    # Audit one PDF
    python -m inclusio.cli.audit build/papers/foo.pdf

    # Audit every PDF under build/ (default)
    python -m inclusio.cli.audit

    # Strict mode: non-zero exit on any failure
    python -m inclusio.cli.audit --strict

    # Specific report path
    python -m inclusio.cli.audit --json out.json --markdown out.md

    # Subset of flavours
    python -m inclusio.cli.audit --flavours ua2,4f

Requires: `verapdf` on PATH. Install via `brew install verapdf` on
macOS or the official installer (see .github/workflows/verapdf.yml).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - PyYAML is a hard dep at install time
    yaml = None


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# CONTENT_ROOT: where build/ lives. Honours INCLUSIO_CONTENT_DIR.
_env_content = os.environ.get("INCLUSIO_CONTENT_DIR")
CONTENT_ROOT = Path(_env_content).resolve() if _env_content else PROJECT_ROOT
DEFAULT_BUILD_DIR = CONTENT_ROOT / "build"
DEFAULT_AUDIT_DIR = DEFAULT_BUILD_DIR / ".audit"
DEFAULT_META = CONTENT_ROOT / "data" / "meta.yaml"


# Flavour catalogue. Each entry: (veraPDF flavour, human label, blocking).
# "blocking" controls --strict behaviour: True means a FAIL exits non-zero.
DEFAULT_FLAVOURS = [
    ("ua2", "PDF/UA-2 (ISO 14289-2:2024)", True),
    ("wt1a", "WTPDF 1.0 Accessibility", True),
    ("4f", "PDF/A-4f (ISO 19005-4:2020 + embedded files)", True),
]


def _have_verapdf() -> bool:
    """True iff `verapdf` is resolvable on PATH."""
    return shutil.which("verapdf") is not None


def _verapdf(pdf: Path, flavour: str, timeout: int = 90) -> dict:
    """Run veraPDF on a single PDF for a single flavour.

    Returns a dict with keys: pdf, flavour, status, line, error.
    status is one of PASS, FAIL, SKIP, ERROR.
    """
    if not _have_verapdf():
        return {
            "pdf": str(pdf),
            "flavour": flavour,
            "status": "SKIP",
            "line": "",
            "error": "verapdf not installed on PATH",
        }
    try:
        result = subprocess.run(
            ["verapdf", "--format", "text", "--flavour", flavour, str(pdf)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "pdf": str(pdf),
            "flavour": flavour,
            "status": "ERROR",
            "line": "",
            "error": f"verapdf timed out after {timeout}s",
        }
    first = (result.stdout or "").splitlines()[0] if result.stdout else ""
    if first.startswith("PASS"):
        status = "PASS"
    elif first.startswith("FAIL"):
        status = "FAIL"
    else:
        status = "ERROR"
    return {
        "pdf": str(pdf),
        "flavour": flavour,
        "status": status,
        "line": first,
        "error": result.stderr.strip() if status == "ERROR" else "",
    }


def _registry_stems(meta_path: Path) -> set:
    """Read meta.yaml and return the set of source-file stems that
    identify Euxis-built artefacts (i.e. PDFs whose stem matches a
    registered document's source file).

    Returns an empty set if meta.yaml is missing or PyYAML is unavailable
    — callers should treat empty as "no registry filtering" and fall
    through to no-op (or use --all to bypass).
    """
    if yaml is None or not meta_path.exists():
        return set()
    try:
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return set()
    stems = set()
    for key, doc in (meta.get("documents") or {}).items():
        # `doc` may be None when the YAML entry has no body (e.g.,
        # `foo:` with no children). Treat as just the ID.
        if isinstance(doc, dict):
            src = doc.get("src") or ""
            if src:
                stems.add(Path(src).stem)
        # Also accept the doc ID itself — template-rendered documents
        # land under build/{type}/{doc_id}.pdf, where doc_id is the key.
        stems.add(key)
    return stems


def collect_pdfs(
    target: Path,
    build_dir: Path,
    registry_stems: set = None,
) -> list:
    """Resolve `target` to a flat list of PDFs.

    If `target` is a PDF, return [target] unconditionally (caller asked
    for a specific file). If `target` is a directory, recursively
    collect *.pdf under it, skipping `build/.cache/` intermediates and
    any `.audit/` folder. When `registry_stems` is non-empty, only PDFs
    whose stem appears in the registry are returned — this filters out
    input briefs (recruiter CVs, job descriptions) co-located in
    `build/jobs/`.
    """
    if target.is_file() and target.suffix.lower() == ".pdf":
        return [target.resolve()]
    if not target.exists():
        return []
    pdfs = []
    for pdf in sorted(target.rglob("*.pdf")):
        parts = pdf.parts
        if any(p in (".cache", ".audit") for p in parts):
            continue
        if registry_stems and pdf.stem not in registry_stems:
            continue
        pdfs.append(pdf.resolve())
    return pdfs


def audit(
    pdfs: list,
    flavours: list = DEFAULT_FLAVOURS,
    timeout: int = 90,
) -> dict:
    """Run veraPDF over every (pdf, flavour) pair.

    Returns the report dict (see audit_report_schema in docs).
    """
    started = datetime.now(UTC).isoformat()
    checks = []
    for pdf in pdfs:
        for flavour, label, _block in flavours:
            checks.append(_verapdf(pdf, flavour, timeout=timeout))
    finished = datetime.now(UTC).isoformat()

    # Aggregate per-PDF and per-flavour stats.
    by_pdf = {}
    by_flavour = {f[0]: {"pass": 0, "fail": 0, "skip": 0, "error": 0} for f in flavours}
    for c in checks:
        pdf = c["pdf"]
        by_pdf.setdefault(pdf, []).append(c)
        b = by_flavour[c["flavour"]]
        b[c["status"].lower()] = b.get(c["status"].lower(), 0) + 1

    summary = {
        "pdfs": len(pdfs),
        "checks": len(checks),
        "pass": sum(1 for c in checks if c["status"] == "PASS"),
        "fail": sum(1 for c in checks if c["status"] == "FAIL"),
        "skip": sum(1 for c in checks if c["status"] == "SKIP"),
        "error": sum(1 for c in checks if c["status"] == "ERROR"),
    }
    return {
        "tool": "euxis-audit",
        "verapdf_present": _have_verapdf(),
        "started_at": started,
        "finished_at": finished,
        "flavours": [{"id": f[0], "label": f[1], "blocking": f[2]} for f in flavours],
        "summary": summary,
        "by_flavour": by_flavour,
        "by_pdf": by_pdf,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    """Produce a human-readable Markdown summary of the audit report."""
    s = report["summary"]
    lines = []
    lines.append("# Euxis EAA / Accessibility Audit Report")
    lines.append("")
    lines.append(f"- Tool: `{report['tool']}`")
    lines.append(f"- veraPDF available: **{report['verapdf_present']}**")
    lines.append(f"- Started: {report['started_at']}")
    lines.append(f"- Finished: {report['finished_at']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- PDFs audited: **{s['pdfs']}**")
    lines.append(f"- Total checks: **{s['checks']}**")
    lines.append(
        f"- PASS: **{s['pass']}**, FAIL: **{s['fail']}**, SKIP: {s['skip']}, ERROR: {s['error']}"
    )
    lines.append("")
    lines.append("## Per-flavour")
    lines.append("")
    lines.append("| Flavour | PASS | FAIL | SKIP | ERROR |")
    lines.append("|---|---:|---:|---:|---:|")
    for fid, b in report["by_flavour"].items():
        lines.append(
            f"| `{fid}` | {b.get('pass', 0)} | {b.get('fail', 0)} | "
            f"{b.get('skip', 0)} | {b.get('error', 0)} |"
        )
    lines.append("")
    lines.append("## Per-PDF")
    lines.append("")
    lines.append("| PDF | " + " | ".join(f"`{f['id']}`" for f in report["flavours"]) + " |")
    lines.append("|---" + "|---" * len(report["flavours"]) + "|")
    for pdf, checks in report["by_pdf"].items():
        row = [f"`{Path(pdf).name}`"]
        for f in report["flavours"]:
            c = next((c for c in checks if c["flavour"] == f["id"]), None)
            row.append(c["status"] if c else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    if s["fail"] or s["error"]:
        lines.append("## Failures")
        lines.append("")
        for c in report["checks"]:
            if c["status"] in ("FAIL", "ERROR"):
                lines.append(
                    f"- `{Path(c['pdf']).name}` `{c['flavour']}`: "
                    f"**{c['status']}** — {c['line'] or c['error']}"
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def _is_blocking(report: dict, status_set=("FAIL", "ERROR")) -> bool:
    """Return True if any blocking-flavour check ended in the failure set."""
    blocking = {f["id"] for f in report["flavours"] if f["blocking"]}
    for c in report["checks"]:
        if c["flavour"] in blocking and c["status"] in status_set:
            return True
    return False


def main(argv=None):
    """Entry point for `python -m inclusio.cli.audit`.

    Parses the audit CLI flags, resolves the PDF set, runs veraPDF over
    every (pdf, flavour) pair, writes JSON + Markdown reports, and
    returns the process exit code (0 success, 1 blocking failure in
    `--strict` mode).
    """
    parser = argparse.ArgumentParser(
        description="Euxis EAA / accessibility audit for built PDFs.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=str(DEFAULT_BUILD_DIR),
        help="PDF file or directory to audit (default: $INCLUSIO_CONTENT_DIR/build)",
    )
    parser.add_argument(
        "--flavours",
        default=",".join(f[0] for f in DEFAULT_FLAVOURS),
        help="Comma-separated veraPDF flavours (default: ua2,wt1a,4f)",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Path to write JSON report (default: build/.audit/eaa-<ts>.json)",
    )
    parser.add_argument(
        "--markdown",
        default=None,
        help="Path to write Markdown summary (default: build/.audit/eaa-<ts>.md)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any blocking-flavour FAIL/ERROR (for CI gating)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Per-check timeout in seconds (default: 90)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Audit every PDF under target (default: only registered docs)",
    )
    parser.add_argument(
        "--meta",
        default=str(DEFAULT_META),
        help=f"meta.yaml path for registry filter (default: {DEFAULT_META})",
    )
    args = parser.parse_args(argv)

    requested = [f.strip() for f in args.flavours.split(",") if f.strip()]
    flavours = [f for f in DEFAULT_FLAVOURS if f[0] in requested]
    unknown = set(requested) - {f[0] for f in flavours}
    if unknown:
        print(
            f"WARNING: unknown flavours skipped: {', '.join(sorted(unknown))}",
            file=sys.stderr,
        )

    target = Path(args.target).resolve()
    registry = set() if args.all else _registry_stems(Path(args.meta))
    pdfs = collect_pdfs(target, DEFAULT_BUILD_DIR, registry_stems=registry)
    if not pdfs:
        print(f"No PDFs found under {target}", file=sys.stderr)
        # Empty target is still success in non-strict mode (nothing to audit).
        return 0 if not args.strict else 1

    report = audit(pdfs, flavours=flavours, timeout=args.timeout)

    # Output paths.
    DEFAULT_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    ts = report["finished_at"].replace(":", "").replace("-", "")[:15]
    json_path = Path(args.json) if args.json else DEFAULT_AUDIT_DIR / f"eaa-{ts}.json"
    md_path = Path(args.markdown) if args.markdown else DEFAULT_AUDIT_DIR / f"eaa-{ts}.md"

    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(render_markdown(report))
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")

    # Order matters: a missing veraPDF is the root cause for every SKIP
    # status in the report, so surface it first with a clearer error.
    # Otherwise `_is_blocking` (which counts only FAIL/ERROR, not SKIP)
    # returns False on a runner with no verapdf installed, and the gate
    # silently passes — exactly the opposite of what --strict promises.
    if args.strict and not report["verapdf_present"]:
        print(
            "STRICT MODE: verapdf is required but not installed on PATH. "
            "Install via `brew install verapdf` on macOS or see "
            ".github/workflows/verapdf.yml for the Linux installer.",
            file=sys.stderr,
        )
        return 1
    if args.strict and _is_blocking(report):
        print("STRICT MODE: blocking-flavour failures detected.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
