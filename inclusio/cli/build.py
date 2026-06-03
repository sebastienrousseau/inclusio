#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
build.py — Unified build orchestrator for Publications.

Replaces 5× latex-build.mk (2,925 lines) + 5× project Makefiles.

Usage:
    python -m inclusio.cli.build build [--mode draft|submission|camera-ready] [--doc DOC]
    python -m inclusio.cli.build assets
    python -m inclusio.cli.build lint
    python -m inclusio.cli.build clean
    python -m inclusio.cli.build list
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

# Re-exports from the v0.0.4 `inclusio.pdf` sub-package — preserves the
# legacy underscore-prefixed names so tests that patch
# `build._post_process_pdf` (and the `build_document` call site below)
# keep working. Canonical home is now `inclusio.pdf.post_process`; new
# code should import from there.
from inclusio.pdf.post_process import (
    apply_encryption as _apply_encryption,  # noqa: F401  back-compat alias
)
from inclusio.pdf.post_process import (
    build_xmp_xml as _build_xmp_xml,  # noqa: F401  back-compat alias
)
from inclusio.pdf.post_process import (
    post_process_pdf as _post_process_pdf,
)

# ── Paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_SUBPROCESS_TIMEOUT = int(os.environ.get("EUXIS_SUBPROCESS_TIMEOUT", "300"))
AUTO_TAILOR_USE_AI = os.environ.get("EUXIS_AUTO_TAILOR_AI", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# CONTENT_ROOT: where content lives (data/, src/, templates/, build/).
# Defaults to PROJECT_ROOT; overridden by INCLUSIO_CONTENT_DIR env var or
# --content-dir CLI flag for split-repo workflows.
#
# Legacy `EUXIS_CONTENT_DIR` is honoured for one minor cycle (until
# inclusio v0.3) with a DeprecationWarning, so content repositories
# pinned to the old name keep working through the rename window.
_env_content = os.environ.get("INCLUSIO_CONTENT_DIR")
if _env_content is None:
    _legacy_content = os.environ.get("EUXIS_CONTENT_DIR")
    if _legacy_content is not None:
        import warnings

        warnings.warn(
            "EUXIS_CONTENT_DIR is deprecated; use INCLUSIO_CONTENT_DIR. "
            "Legacy support will be removed in inclusio v0.3.",
            DeprecationWarning,
            stacklevel=2,
        )
        _env_content = _legacy_content
CONTENT_ROOT = Path(_env_content).resolve() if _env_content else PROJECT_ROOT

META_FILE = CONTENT_ROOT / "data" / "meta.yaml"
BUILD_DIR = CONTENT_ROOT / "build"
CACHE_DIR = BUILD_DIR / ".cache"
RENDERED_DIR = CACHE_DIR / "rendered"
JOBS_DIR = CONTENT_ROOT / "data" / "jobs"
TAILORED_DIR = CONTENT_ROOT / "data" / "tailored"


def _resolve_content_paths(root):
    """Re-bind content-path globals to *root* (a Path).

    Called when --content-dir is provided on the CLI, after argparse runs.
    """
    global CONTENT_ROOT, META_FILE, BUILD_DIR, CACHE_DIR, RENDERED_DIR
    global JOBS_DIR, TAILORED_DIR
    CONTENT_ROOT = Path(root).resolve()
    META_FILE = CONTENT_ROOT / "data" / "meta.yaml"
    BUILD_DIR = CONTENT_ROOT / "build"
    CACHE_DIR = BUILD_DIR / ".cache"
    RENDERED_DIR = CACHE_DIR / "rendered"
    JOBS_DIR = CONTENT_ROOT / "data" / "jobs"
    TAILORED_DIR = CONTENT_ROOT / "data" / "tailored"


def load_meta():
    """Load and return the document manifest from data/meta.yaml."""
    if not META_FILE.exists():
        print(f"ERROR: {META_FILE} not found", file=sys.stderr)
        sys.exit(1)
    with open(META_FILE) as f:
        return yaml.safe_load(f)


def _import_render_module():
    """Import the render module with a fallback for direct wrapper execution."""
    try:
        return __import__("render")
    except ModuleNotFoundError:
        from inclusio.cli import render as render_module

        return render_module


def _import_tailor_module():
    """Import the tailor module with a fallback for direct wrapper execution."""
    try:
        return __import__("tailor")
    except ModuleNotFoundError:
        from inclusio.cli import tailor as tailor_module

        return tailor_module


def check_tool(name):
    """Check if a tool is available on PATH."""
    return shutil.which(name) is not None


def check_tools():
    """Verify required build tools are installed.

    LuaLaTeX is hard-required (decision D3, 2026-05-23): tagged-PDF and
    PDF/UA-2 work depends on tagpdf's LuaLaTeX-only code paths.
    """
    required = ["lualatex", "bibtex"]
    missing = [t for t in required if not check_tool(t)]
    if missing:
        print(f"ERROR: Missing tools: {', '.join(missing)}", file=sys.stderr)
        print("Install TeX Live 2024+ or use 'nix develop' / Docker.", file=sys.stderr)
        sys.exit(1)


def mode_to_option(mode):
    """Convert build mode string to LaTeX class option."""
    mapping = {
        "draft": "draft",
        "submission": "submission",
        "camera-ready": "final",
        "final": "final",
    }
    return mapping.get(mode, "draft")


def texinputs_env(doc_dir, extra_dir=None):
    """Build the TEXINPUTS environment variable for a document."""
    paths = [
        str(PROJECT_ROOT / "core" / "cls"),
        str(PROJECT_ROOT / "core" / "sty"),
        str(doc_dir),
    ]
    if extra_dir and str(extra_dir) != str(doc_dir):
        paths.append(str(extra_dir))
    paths.append(str(CONTENT_ROOT / "assets"))
    if CONTENT_ROOT != PROJECT_ROOT:
        paths.append(str(PROJECT_ROOT / "assets"))
    paths += [
        str(CONTENT_ROOT),
        str(PROJECT_ROOT),
        "",  # trailing colon for system default
    ]
    sep = ":" if os.name != "nt" else ";"
    return sep.join(paths)


def _content_hash(path):
    """Return SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_cached(doc_id, tex_path):
    """Check if a document's source is unchanged since last build."""
    cache_file = CACHE_DIR / "hashes" / f"{doc_id}.sha256"
    if not cache_file.exists():
        return False
    return cache_file.read_text().strip() == _content_hash(tex_path)


def _write_cache(doc_id, tex_path):
    """Store the content hash for a successfully built document."""
    hash_dir = CACHE_DIR / "hashes"
    hash_dir.mkdir(parents=True, exist_ok=True)
    (hash_dir / f"{doc_id}.sha256").write_text(_content_hash(tex_path))


SUPPORTED_BRIEF_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rtf",
    ".doc",
    ".docx",
    ".odt",
    ".html",
}
JOB_TYPE_ALIASES = {
    "cv": "cv",
    "cvs": "cv",
    "resume": "cv",
    "resumes": "cv",
    "whitepaper": "paper",
    "whitepapers": "paper",
    "paper": "paper",
    "papers": "paper",
    "patent": "patent",
    "patents": "patent",
    "faq": "faq",
    "faqs": "faq",
    "guide": "guide",
    "guides": "guide",
    "user-guide": "guide",
    "user-guides": "guide",
}


def _infer_job_doc_type(brief_path):
    """Infer document type from job folder structure or filename prefix."""
    rel_parts = [part.lower() for part in brief_path.relative_to(JOBS_DIR).parts[:-1]]
    for part in rel_parts:
        if part in JOB_TYPE_ALIASES:
            return JOB_TYPE_ALIASES[part]

    stem = brief_path.stem.lower()
    for prefix, doc_type in JOB_TYPE_ALIASES.items():
        if stem == prefix or stem.startswith(f"{prefix}-") or stem.startswith(f"{prefix}_"):
            return doc_type

    return "cv"


def _sync_jobs_to_tailored(meta, force=False, selected_output_ids=None):
    """Generate tailored YAML for supported briefs in data/jobs/."""
    if not JOBS_DIR.exists():
        return

    tailor = _import_tailor_module()
    template_entries = meta.get("templates", {})

    for brief_path in sorted(JOBS_DIR.rglob("*")):
        if not brief_path.is_file():
            continue
        if brief_path.suffix.lower() not in SUPPORTED_BRIEF_EXTENSIONS:
            continue

        output_id = brief_path.stem
        if selected_output_ids and output_id not in selected_output_ids:
            continue
        doc_type = _infer_job_doc_type(brief_path)
        template_entry = template_entries.get(output_id, {})
        if template_entry.get("sync_from_jobs", True) is False:
            continue
        target_relpath = template_entry.get("data")
        if target_relpath:
            tailored_path = CONTENT_ROOT / "data" / target_relpath
        else:
            tailored_path = TAILORED_DIR / f"{output_id}.yaml"
        if tailored_path.exists():
            with open(tailored_path) as f:
                existing = yaml.safe_load(f)
            normalised = existing
            if isinstance(existing, dict) and ("experience" in existing or "skills" in existing):
                normalised = tailor._optimise_cv_for_ats(normalised)
                normalised = tailor._clean_cv_language(normalised)
            normalised = tailor._escape_latex_strings(normalised)
            if normalised != existing:
                TAILORED_DIR.mkdir(parents=True, exist_ok=True)
                with open(tailored_path, "w") as f:
                    yaml.dump(
                        normalised,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                print(f"  NORMALIZE {output_id} <- data/tailored/{output_id}.yaml")

        is_stale = force or (
            not tailored_path.exists() or brief_path.stat().st_mtime > tailored_path.stat().st_mtime
        )
        if not is_stale:
            continue

        TAILORED_DIR.mkdir(parents=True, exist_ok=True)
        print(f"  TAILOR {output_id} <- {brief_path.relative_to(CONTENT_ROOT)}")
        tailor.generate(
            brief_path,
            doc_type,
            output_id,
            None,
            use_ai=AUTO_TAILOR_USE_AI,
            output_path=tailored_path,
        )


def _artifact_subdir(doc_id, doc_config):
    """Derive the domain subfolder for a document's output.

    Maps src path to output domain:
      src/cvs/...     -> cvs/
      src/papers/...  -> papers/
      src/patents/... -> patents/
      src/faqs/...    -> faqs/
      src/guides/...  -> guides/
      (tailored)      -> jobs/

    When a per-job document declares `job_folder: <slug>`, the output is
    routed to `jobs/<slug>/` so each application's artefacts can be grouped
    in their own folder rather than the flat `jobs/` directory.
    """
    if doc_config.get("tailored"):
        subdir = "jobs"
    else:
        src = doc_config.get("src", "")
        subdir = ""
        if src.startswith("src/"):
            parts = src.split("/")
            if len(parts) >= 2:
                subdir = parts[1]  # cvs, papers, patents, faqs, guides
        elif "build/rendered" in src or doc_config.get("description", "").startswith("Tailored"):
            subdir = "jobs"

    job_folder = doc_config.get("job_folder")
    if subdir == "jobs" and job_folder:
        return f"jobs/{job_folder}"
    return subdir


def _discover_tailored(meta):
    """Discover tailored documents in data/tailored/ and render them.

    Scans for YAML files (excluding .gitkeep), renders each through the
    appropriate Jinja2 template, copies the result to
    src/{category}/{doc_id}/ (a unique subfolder), and returns a dict of
    synthetic doc_configs.  Skips any doc_id that matches a registered
    document in meta.yaml (e.g. 'cv' is the base CV, not a tailored job).
    """
    if not TAILORED_DIR.exists():
        return {}

    registered = set(meta.get("documents", {}).keys())
    templates = meta.get("templates", {})
    tailored_docs = {}

    # Map doc_type → category folder under src/
    type_to_category = {
        "cv": "cvs",
        "paper": "papers",
        "patent": "patents",
        "faq": "faqs",
        "guide": "guides",
    }

    for yaml_file in sorted(TAILORED_DIR.glob("*.yaml")):
        doc_id = yaml_file.stem
        if doc_id in registered:
            continue  # skip base documents (e.g. cv.yaml overrides base CV)

        # Determine template type from the data
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if not data:
            continue

        # Prefer explicit type metadata from the tailoring step.
        metadata = data.get("_publisher", {}) if isinstance(data, dict) else {}
        doc_type = metadata.get("doc_type")
        if not doc_type:
            if "experience" in data or "skills" in data:
                doc_type = "cv"
            else:
                doc_type = "paper"

        template_entry = templates.get(doc_type, {})
        template_name = template_entry.get("template", f"{doc_type}.tex.j2")

        # Render through Jinja2 template
        try:
            render_module = _import_render_module()
            render_latex = render_module.render_latex
            _generate_xmpdata = render_module._generate_xmpdata
            data["build_mode"] = data.get("build_mode", "draft")
            output = render_latex(template_name, data)
            RENDERED_DIR.mkdir(parents=True, exist_ok=True)
            rendered_path = RENDERED_DIR / f"{doc_id}.tex"
            rendered_path.write_text(output, encoding="utf-8")
            _generate_xmpdata(doc_id, data, meta)
        except Exception as exc:
            print(f"  WARN: Could not render tailored {doc_id}: {exc}", file=sys.stderr)
            continue

        # Copy rendered .tex, .xmpdata, and shared figures into
        # src/{category}/{doc_id}/ so every file needed to compile
        # lives in one self-contained directory.
        category = type_to_category.get(doc_type, f"{doc_type}s")
        src_subdir = CONTENT_ROOT / "src" / category / doc_id
        src_subdir.mkdir(parents=True, exist_ok=True)
        src_tex = src_subdir / f"{doc_id}.tex"
        src_tex.write_text(output, encoding="utf-8")
        xmpdata_rendered = RENDERED_DIR / f"{doc_id}.xmpdata"
        if xmpdata_rendered.exists():
            shutil.copy2(xmpdata_rendered, src_subdir / f"{doc_id}.xmpdata")

        # Copy shared figures from parent category directory
        figures_dir = CONTENT_ROOT / "src" / category / "figures"
        target_figures = src_subdir / "figures"
        if figures_dir.exists() and not target_figures.exists():
            shutil.copytree(figures_dir, target_figures)

        # The src config points to the new source location.
        # figures_src tracks the parent category dir for shared figures.
        src_rel = f"src/{category}/{doc_id}/{doc_id}.tex"

        tailored_docs[doc_id] = {
            "class": f"pub-{doc_type}",
            "src": src_rel,
            "figures_src": f"src/{category}",
            "title": data.get("title", f"Tailored {doc_type.upper()} — {doc_id}"),
            "version": "1.0",
            "description": f"Tailored {doc_type} for {doc_id}",
            "subject": data.get("subject", f"Tailored {doc_type.upper()}"),
            "keywords": data.get("keywords", ""),
            "tailored": True,
        }

    return tailored_docs


def _expand_ats_pairs(meta):
    """Synthesize ATS sibling document + template entries.

    For every pub-cv document with `ats_pair: true`, add a sibling document
    `<doc-id>-orc` (and matching templates entry) so the publisher emits
    both the design and the ATS-optimised variant in one build call.
    Convention-based: the sibling template is `<base>-orc.tex.j2` rendered
    against the same YAML data file. Explicit per-doc registrations win:
    if `<doc-id>-orc` is already in meta, the synthesised entry is skipped.

    Returns a fresh meta dict when any expansion happens; otherwise returns
    the original meta unchanged so callers that compare by identity
    (e.g. mock assertions) continue to pass.
    """
    if not any(c.get("ats_pair") for c in meta.get("documents", {}).values()):
        return meta

    expanded = dict(meta)
    documents = dict(expanded.get("documents", {}))
    templates = dict(expanded.get("templates", {}))

    for doc_id, config in list(documents.items()):
        if not config.get("ats_pair"):
            continue
        if config.get("class") != "pub-cv":
            continue
        orc_id = f"{doc_id}-orc"
        if orc_id in documents:
            continue  # explicit registration wins

        orc_config = dict(config)
        orc_config.pop("ats_pair", None)
        if config.get("src"):
            # The rendered source path follows the doc_id naming convention.
            orc_config["src"] = config["src"].replace(f"{doc_id}.tex", f"{orc_id}.tex")
        # Mark the sibling so downstream consumers (tests, judges) can spot it.
        orc_config["ats_orc_of"] = doc_id
        documents[orc_id] = orc_config

        if doc_id in templates and orc_id not in templates:
            base_tmpl = dict(templates[doc_id])
            template_name = base_tmpl.get("template", "")
            if template_name.endswith(".tex.j2"):
                base_tmpl["template"] = template_name[: -len(".tex.j2")] + "-orc.tex.j2"
            templates[orc_id] = base_tmpl

    expanded["documents"] = documents
    expanded["templates"] = templates
    return expanded


def build_document(doc_id, doc_config, mode, meta, force=False):
    """Compile a single document."""
    src_path = CONTENT_ROOT / doc_config["src"]
    original_src_dir = src_path.parent

    if doc_config.get("render_from_template"):
        try:
            render_module = _import_render_module()
            render_module.render_document(
                doc_id, fmt="latex", build_mode=mode, content_root=CONTENT_ROOT, meta=meta
            )
            src_path = RENDERED_DIR / f"{doc_id}.tex"
            original_src_dir = src_path.parent
        except ImportError:
            print("ERROR: Jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
            return False

    # Use rendered template if available (but not for tailored docs whose
    # source already lives under src/{category}/{doc_id}/).
    if not doc_config.get("tailored"):
        rendered = RENDERED_DIR / f"{doc_id}.tex"
        if rendered.exists():
            src_path = rendered

    if not src_path.exists():
        print(f"  SKIP {doc_id}: {src_path} not found")
        return False

    # Skip non-standalone files
    if doc_config.get("note", "").startswith("This is an input file"):
        print(f"  SKIP {doc_id}: input file (not standalone)")
        return True

    # Cache check — skip if unchanged and not forced
    if not force and _is_cached(doc_id, src_path):
        print(f"  CACHED {doc_id}")
        return True

    doc_dir = src_path.parent
    tex_file = src_path.name
    build_dir = CACHE_DIR / "intermediates" / doc_id
    build_dir.mkdir(parents=True, exist_ok=True)
    subdir = _artifact_subdir(doc_id, doc_config)
    artifact_dir = BUILD_DIR / subdir
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale PDF before compilation to prevent copying an old
    # artifact if this build fails but a previous PDF lingers.
    pdf_name = Path(tex_file).stem + ".pdf"
    stale_pdf = build_dir / pdf_name
    if stale_pdf.exists():
        stale_pdf.unlink()

    # Build environment — include both rendered dir and original source dir
    # so that assets (figures/) referenced with relative paths are found.
    env = os.environ.copy()
    env["TEXINPUTS"] = texinputs_env(doc_dir, original_src_dir)
    # Tailored docs live in src/{category}/{doc_id}/ — add the parent
    # category dir so shared figures/ are found.
    figures_src = doc_config.get("figures_src", "")
    if figures_src:
        fig_dir = str(CONTENT_ROOT / figures_src)
        sep = ":" if os.name != "nt" else ";"
        env["TEXINPUTS"] = fig_dir + sep + env["TEXINPUTS"]

    # Compiler settings from meta. Default is LuaLaTeX (decision D3,
    # 2026-05-23): hard-required for tagpdf + PDF/UA-2 reliability.
    # `max_passes` and `bib_engine` are read by the latexmk path below
    # via a fresh meta.get(...) lookup; pre-binding them here is dead
    # code from a pre-2026 prototype.
    compiler = meta.get("build", {}).get("compiler", "lualatex")

    # Use latexmk for multi-pass compilation
    if check_tool("latexmk"):
        cmd = [
            "latexmk",
            f"-{compiler}",
            f"-output-directory={build_dir}",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            tex_file,
        ]
        if force:
            cmd.insert(1, "-g")
    else:
        # Fallback: manual multi-pass
        cmd = [
            compiler,
            f"-output-directory={build_dir}",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            tex_file,
        ]

    print(f"  BUILD {doc_id} [{mode}] → {build_dir}")

    # Run compilation
    result = subprocess.run(
        cmd,
        cwd=str(doc_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )

    if result.returncode != 0:
        print(f"  FAIL {doc_id}")
        # Show last 20 lines of log for debugging
        log_lines = result.stdout.strip().split("\n")
        for line in log_lines[-20:]:
            print(f"    | {line}")
        return False

    # Copy only the PDF to artifacts
    built_pdf = build_dir / pdf_name
    if built_pdf.exists():
        dest = artifact_dir / pdf_name
        shutil.copy2(built_pdf, dest)
        _post_process_pdf(dest, doc_id, doc_config, meta)
        _write_cache(doc_id, src_path)
        print(f"  OK   {doc_id} → {dest}")
    else:
        print(f"  WARN {doc_id}: compiled but no PDF produced at {built_pdf}")
        return False

    return True


def cmd_build(args, meta):
    """Build documents."""
    check_tools()
    mode = args.mode
    # `mode_to_option(mode)` is computed inside `build_document` for
    # each doc; pre-binding it here was dead code.
    force = getattr(args, "force", False)
    jobs = getattr(args, "jobs", 1)
    jobs_only = getattr(args, "jobs_only", False)

    # Expand ats_pair: true entries into synthesised ORC siblings so the
    # publisher emits both variants from a single registration.
    meta = _expand_ats_pairs(meta)
    documents = meta.get("documents", {})

    # Promote supported briefs from data/jobs/ into data/tailored/
    selected_output_ids = {args.doc} if args.doc else None
    _sync_jobs_to_tailored(
        meta,
        force=force,
        selected_output_ids=selected_output_ids,
    )

    # Discover tailored documents from data/tailored/
    tailored = _discover_tailored(meta)
    if jobs_only:
        documents = {
            doc_id: config for doc_id, config in documents.items() if config.get("jobs_only")
        }

    all_documents = {**documents, **tailored}

    if args.doc:
        if args.doc not in all_documents:
            print(f"ERROR: Unknown document '{args.doc}'", file=sys.stderr)
            print(f"Available: {', '.join(all_documents.keys())}", file=sys.stderr)
            sys.exit(1)
        docs_to_build = {args.doc: all_documents[args.doc]}
        # Include the synthesised ATS sibling automatically when the user
        # selects only the design doc (so a single --doc call still emits
        # both PDFs).
        orc_id = f"{args.doc}-orc"
        if orc_id in all_documents and all_documents[orc_id].get("ats_orc_of") == args.doc:
            docs_to_build[orc_id] = all_documents[orc_id]
    else:
        docs_to_build = all_documents

    print(f"Building {len(docs_to_build)} document(s) in {mode} mode (jobs={jobs})...\n")

    success = 0
    fail = 0
    skip = 0

    if jobs == 1:
        # Sequential build (backward compatible, useful for debugging)
        for doc_id, doc_config in docs_to_build.items():
            result = build_document(doc_id, doc_config, mode, meta, force=force)
            if result is True:
                success += 1
            elif result is False:
                fail += 1
            else:
                skip += 1
    else:
        # Parallel build
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(build_document, doc_id, config, mode, meta, force): doc_id
                for doc_id, config in docs_to_build.items()
            }
            for future in as_completed(futures):
                result = future.result()
                if result is True:
                    success += 1
                elif result is False:
                    fail += 1
                else:
                    skip += 1

    print(f"\nResults: {success} ok, {fail} failed, {skip} skipped")
    if fail > 0:
        sys.exit(1)


def cmd_assets(args, meta):
    """Run asset pipeline."""
    script = PROJECT_ROOT / "scripts" / "asset-pipeline.sh"
    if not script.exists():
        print(f"ERROR: {script} not found", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["INCLUSIO_CONTENT_DIR"] = str(CONTENT_ROOT)
    result = subprocess.run(
        ["bash", str(script)],
        cwd=str(CONTENT_ROOT),
        env=env,
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )
    sys.exit(result.returncode)


def cmd_lint(args, meta):
    """Run quality checks."""
    errors = 0
    env = os.environ.copy()
    env["INCLUSIO_CONTENT_DIR"] = str(CONTENT_ROOT)

    # 1. Semantic check
    print("Running semantic check...")
    check_script = PROJECT_ROOT / "scripts" / "check-semantic.sh"
    if check_script.exists():
        result = subprocess.run(
            ["bash", str(check_script)],
            cwd=str(CONTENT_ROOT),
            env=env,
            timeout=DEFAULT_SUBPROCESS_TIMEOUT,
        )
        if result.returncode != 0:
            errors += 1
    else:
        print("  SKIP: check-semantic.sh not found")

    # 2. chktex
    if check_tool("chktex"):
        print("\nRunning chktex...")
        src_dir = CONTENT_ROOT / "src"
        if src_dir.exists():
            for tex_file in src_dir.rglob("*.tex"):
                result = subprocess.run(
                    ["chktex", "-q", str(tex_file)],
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_SUBPROCESS_TIMEOUT,
                )
                if result.stdout.strip():
                    print(f"  {tex_file.relative_to(CONTENT_ROOT)}: warnings found")
                    errors += 1
    else:
        print("  SKIP: chktex not installed")

    # 3. Vale
    if check_tool("vale"):
        print("\nRunning vale...")
        result = subprocess.run(
            ["vale", "src/"],
            cwd=str(CONTENT_ROOT),
            capture_output=True,
            text=True,
            timeout=DEFAULT_SUBPROCESS_TIMEOUT,
        )
        if result.returncode != 0:
            print(result.stdout)
            errors += 1
    else:
        print("  SKIP: vale not installed")

    if errors > 0:
        print(f"\nLint: {errors} issue(s) found")
        sys.exit(1)
    else:
        print("\nLint: all checks passed")


def cmd_render(args, meta):
    """Render Jinja2 templates to output format."""
    try:
        render_module = _import_render_module()
    except ImportError:
        print("ERROR: Jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
        sys.exit(1)

    doc_id = args.doc
    fmt = getattr(args, "format", "latex")
    mode = getattr(args, "mode", "draft")
    render_module.render_document(doc_id, fmt, mode, content_root=CONTENT_ROOT)


def cmd_fix(args, meta):
    """Auto-fix semantic violations in source files.

    Delegates to the packaged `inclusio.tools.fix_semantic` module
    via the Python interpreter — the same surface as `python -m
    inclusio.tools.fix_semantic`. The historical
    `scripts/fix-semantic.py` shim was removed in v0.0.3.
    """
    cmd = [sys.executable, "-m", "inclusio.tools.fix_semantic", "src/"]
    if getattr(args, "dry_run", False):
        cmd.append("--dry-run")
    if getattr(args, "verbose", False):
        cmd.append("--verbose")
    env = os.environ.copy()
    env["INCLUSIO_CONTENT_DIR"] = str(CONTENT_ROOT)
    result = subprocess.run(
        cmd,
        cwd=str(CONTENT_ROOT),
        env=env,
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )
    sys.exit(result.returncode)


def cmd_sitemap(args, meta):
    """Generate semantic search metadata.

    Delegates to the packaged `inclusio.cli.sitemap` module via the
    Python interpreter — the same surface as `python -m
    inclusio.cli.sitemap`. The historical `scripts/sitemap.py` shim
    was removed in v0.0.3.
    """
    cmd = [sys.executable, "-m", "inclusio.cli.sitemap"]
    if getattr(args, "pretty", False):
        cmd.append("--pretty")
    if getattr(args, "stdout", False):
        cmd.append("--stdout")
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )
    sys.exit(result.returncode)


def cmd_blog(args, meta):
    """Render blog posts to Jekyll-compatible Markdown."""
    try:
        render_module = _import_render_module()
    except ImportError:
        print("ERROR: Jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
        sys.exit(1)

    blog_entries = meta.get("blog", {})
    if not blog_entries:
        print("No blog entries registered in meta.yaml")
        return

    if args.doc:
        if args.doc not in blog_entries:
            print(f"ERROR: Unknown blog post '{args.doc}'", file=sys.stderr)
            print(f"Available: {', '.join(blog_entries.keys())}", file=sys.stderr)
            sys.exit(1)
        entries = {args.doc: blog_entries[args.doc]}
    else:
        entries = blog_entries

    # Check pandoc availability only if convert-type entries exist
    convert_entries = {k: v for k, v in entries.items() if v.get("type") == "convert"}
    if convert_entries and not check_tool("pandoc"):
        print(
            "ERROR: pandoc is required for 'convert' blog posts but is not installed.",
            file=sys.stderr,
        )
        print("Install pandoc or use only type: jinja2 posts.", file=sys.stderr)
        sys.exit(1)

    print(f"Rendering {len(entries)} blog post(s)...\n")

    for blog_id, config in entries.items():
        render_module.render_blog(blog_id, config, CONTENT_ROOT)

    print(f"\nBlog: {len(entries)} post(s) rendered")


def cmd_clean(args, meta):
    """Remove build directory (intermediates, artifacts, cache)."""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"Removed {BUILD_DIR}")
    else:
        print("Nothing to clean")


# Dev artifacts that accumulate outside build/ and artifacts/
_DEV_ARTIFACTS = [".coverage", ".pytest_cache"]


def cmd_distclean(args, meta):
    """Remove build output and dev environment artifacts."""
    cmd_clean(args, meta)
    for name in _DEV_ARTIFACTS:
        target = PROJECT_ROOT / name
        if target.is_file():
            target.unlink()
            print(f"Removed {target}")
        elif target.is_dir():
            shutil.rmtree(target)
            print(f"Removed {target}")


def cmd_list(args, meta):
    """List registered documents."""
    documents = meta.get("documents", {})
    tailored = _discover_tailored(meta)
    all_docs = {**documents, **tailored}
    print(f"{'ID':<20} {'Class':<15} {'Source':<55} {'Description'}")
    print("-" * 120)
    for doc_id, config in all_docs.items():
        desc = config.get("description", "")
        src = config.get("src", "")
        if config.get("tailored"):
            src = f"data/tailored/{doc_id}.yaml [tailored]"
        print(f"{doc_id:<20} {config['class']:<15} {src:<55} {desc}")


def cmd_import_resume(args, meta):  # noqa: ARG001 (meta unused, dispatcher signature)
    """Convert a JSON Resume document to Euxis CV YAML (Sprint 5, #6)."""
    from inclusio.cli import import_resume

    cmd = [args.input]
    if args.output:
        cmd += ["--output", args.output]
    rc = import_resume.main(cmd)
    if rc:
        sys.exit(rc)


def cmd_provenance(args, meta):
    """Embed C2PA Content Credentials in a registered document's PDF (S8).

    Reads metadata from `meta.documents.<doc_id>` (title, author,
    publisher, ai_disclosure), builds a minimal C2PA manifest, and
    invokes `c2patool` to embed it.

    Without `--cert` + `--key`, falls back to c2patool's built-in
    test cert and warns — fine for development, NOT publication.
    """
    from inclusio.provenance import c2pa as c2pa_mod

    documents = meta.get("documents", {}) or {}
    if args.doc not in documents:
        print(
            f"ERROR: {args.doc} not in documents: in meta.yaml",
            file=sys.stderr,
        )
        sys.exit(2)
    doc = documents[args.doc]
    src_rel = doc.get("src", "")
    if not src_rel:
        print(f"ERROR: {args.doc} has no `src:` in meta", file=sys.stderr)
        sys.exit(2)

    # The PDF path follows `_artifact_subdir(doc_id, doc)/{stem}.pdf`,
    # mirroring how cmd_build resolves outputs.
    artefact_subdir = _artifact_subdir(args.doc, doc)
    pdf_stem = Path(src_rel).stem
    pdf_path = BUILD_DIR / artefact_subdir / f"{pdf_stem}.pdf"
    if not pdf_path.exists():
        print(
            f"ERROR: {pdf_path} not found. Run `make publish` (or "
            "`inclusio build --mode camera-ready`) first.",
            file=sys.stderr,
        )
        sys.exit(1)

    author_block = meta.get("author", {}) or {}
    manifest_json = c2pa_mod.build_manifest_json(
        title=doc.get("title", args.doc),
        author=author_block.get("name", ""),
        publisher=author_block.get("publisher", "Inclusio"),
        date_published=doc.get("filing_date") or None,
        ai_disclosure=doc.get("ai_disclosure") or meta.get("ai_disclosure") or "",
    )

    cert = Path(args.cert) if args.cert else None
    key = Path(args.key) if args.key else None
    try:
        result = c2pa_mod.embed_manifest(pdf_path, manifest_json, cert_path=cert, key_path=key)
    except c2pa_mod.C2PAMissing as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(
            f"ERROR: c2patool exit {exc.returncode}: {(exc.stderr or '').strip()[:300]}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"  OK   {args.doc} → {result.pdf_path}")
    print(f"  manifest bytes: {result.manifest_bytes}")
    if result.signed_with_test_cert:
        print(
            "  WARN: signed with c2patool's test cert (development only). "
            "Pass --cert + --key for publication-ready signatures."
        )
    if args.strict and result.signed_with_test_cert:
        sys.exit(1)


def cmd_judge(args, meta):
    """Run an LLM/heuristic judge against a rendered document (Sprint 7).

    Today the only registered judge is `ats` — Workday/Greenhouse/Lever
    conformance scoring for CV variants. It runs against the
    `render_text` plain-text shadow, so the same content path that
    feeds ATS pipelines is scored.

    Future judges (citations via ScholarCopilot pattern, local llama.cpp
    re-score) plug into the same dispatch table.
    """
    from inclusio.cli import render as render_module
    from inclusio.judge import JUDGES

    judge_inst = JUDGES.get(args.judge)
    if judge_inst is None:
        print(
            f"ERROR: unknown judge {args.judge!r} (expected one of {sorted(JUDGES)})",
            file=sys.stderr,
        )
        sys.exit(2)

    doc_id = args.doc

    if args.judge == "jd_fit":
        # Sprint 7 (S7.4): score how well doc_id (a CV template) fits
        # the brief at --brief. Renders the CV to text first, then
        # reads the brief as plain text (passes through any txt / md /
        # rtf the brief promotion supports — Markdown is the common case).
        if not args.brief:
            print(
                "ERROR: --judge jd_fit requires --brief <path-to-job-description>",
                file=sys.stderr,
            )
            sys.exit(2)
        brief_path = Path(args.brief)
        if not brief_path.exists():
            print(f"ERROR: brief not found at {brief_path}", file=sys.stderr)
            sys.exit(1)
        jd_text = brief_path.read_text(encoding="utf-8")

        templates = meta.get("templates", {}) or {}
        if doc_id not in templates:
            print(
                f"ERROR: {doc_id} is not a registered template (see `templates:` in meta.yaml)",
                file=sys.stderr,
            )
            sys.exit(2)
        doc_type = templates[doc_id].get("type", doc_id)
        if doc_type != "cv":
            print(
                f"ERROR: jd_fit judge only scores CVs; {doc_id} has type {doc_type!r}",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            render_module.render_document(
                doc_id, fmt="text", build_mode="draft", content_root=CONTENT_ROOT
            )
        except SystemExit:
            raise
        cv_path = CONTENT_ROOT / "build" / ".cache" / "rendered" / f"{doc_id}.txt"
        if not cv_path.exists():
            print(f"ERROR: render produced no {cv_path}", file=sys.stderr)
            sys.exit(1)
        cv_text = cv_path.read_text(encoding="utf-8")
        if args.llm_url:
            from inclusio.judge import local_llm

            llm = local_llm.LocalLLM(base_url=args.llm_url, timeout=args.llm_timeout)
            report = judge_inst.score_with_llm(llm, jd_text=jd_text, cv_text=cv_text)
        else:
            report = judge_inst.score(jd_text=jd_text, cv_text=cv_text)
        _print_and_persist_report(report, doc_id, args)
        return

    if args.judge == "citations":
        # Sprint 7 (S7.2): score `\cite` / `\bibitem` consistency.
        # Citations judge reads the .tex source directly — no Jinja2
        # render step required. Accept either a registered document
        # in meta.documents (uses its `src:`) or a raw .tex path
        # via --src-path.
        documents = meta.get("documents", {}) or {}
        if doc_id in documents:
            src_rel = documents[doc_id].get("src")
            if not src_rel:
                print(f"ERROR: {doc_id} in meta has no `src:` field", file=sys.stderr)
                sys.exit(2)
            tex_path = CONTENT_ROOT / src_rel
        else:
            print(
                f"ERROR: {doc_id} not in documents: in meta.yaml. "
                "citations judge needs a .tex source.",
                file=sys.stderr,
            )
            sys.exit(2)
        if not tex_path.exists():
            print(f"ERROR: {tex_path} not found", file=sys.stderr)
            sys.exit(1)
        tex_source = tex_path.read_text(encoding="utf-8")
        if args.llm_url:
            from inclusio.judge import local_llm

            llm = local_llm.LocalLLM(base_url=args.llm_url, timeout=args.llm_timeout)
            report = judge_inst.score_with_llm(llm, tex=tex_source)
        else:
            report = judge_inst.score(tex=tex_source)
        _print_and_persist_report(report, doc_id, args)
        return

    templates = meta.get("templates", {}) or {}
    if doc_id not in templates:
        print(
            f"ERROR: {doc_id} is not a registered template (see `templates:` in meta.yaml)",
            file=sys.stderr,
        )
        sys.exit(2)
    doc_type = templates[doc_id].get("type", doc_id)
    if doc_type != "cv":
        print(
            f"ERROR: ats judge only scores CVs; {doc_id} has type {doc_type!r}",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        render_module.render_document(
            doc_id, fmt="text", build_mode="draft", content_root=CONTENT_ROOT
        )
    except SystemExit:
        raise
    out_path = CONTENT_ROOT / "build" / ".cache" / "rendered" / f"{doc_id}.txt"
    if not out_path.exists():
        print(f"ERROR: render produced no {out_path}", file=sys.stderr)
        sys.exit(1)

    plain_text = out_path.read_text(encoding="utf-8")
    if args.llm_url:
        # Sprint 7 (S7.1 + S7.5): local or cloud LLM rerank. Falls
        # back to heuristic-only when the LLM is unreachable.
        llm = _make_llm(args)
        report = judge_inst.score_with_llm(llm, plain_text=plain_text)
    else:
        report = judge_inst.score(plain_text=plain_text)
    _print_and_persist_report(report, doc_id, args)


def _make_llm(args):
    """Build the right LLM adapter for `args.llm_url`.

    Sprint 7.5: anthropic.com / openai.com URLs route to `CloudLLM`
    (BYO-key via env var); everything else stays on `LocalLLM`
    (llama.cpp HTTP).
    """
    from inclusio.judge import cloud_llm

    return cloud_llm.from_url(
        args.llm_url,
        timeout=args.llm_timeout,
        model=getattr(args, "llm_model", "claude-opus-4-7") or "claude-opus-4-7",
    )


def _print_and_persist_report(report, doc_id, args):
    """Render JudgeReport to stdout + optional JSON path. Shared by ats + citations."""
    judge_label = args.judge.upper()
    print(f"{judge_label} ({doc_id}) — Score: {report.score}/100  Grade: {report.grade}\n")
    for f in report.findings:
        marker = {"block": "✗", "warn": "⚠", "info": "ℹ"}.get(f.severity, "•")
        print(f"  {marker} [{f.severity}] {f.check}: {f.message}  (-{f.deduction})")
    if args.json:
        import json as _json

        Path(args.json).write_text(_json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\nJSON report: {args.json}")
    if args.strict and report.grade in ("D", "F"):
        sys.exit(1)


def cmd_emit(args, meta):
    """Emit HTML / JATS XML from registered documents (Sprint 6 wiring).

    Wraps `inclusio.emit.pandoc.emit_all` with the registry
    filter that the build CLI already uses for `build` / `audit` —
    only documents listed in `data/meta.yaml` `documents:` get emitted.
    """
    try:
        from inclusio.emit import pandoc as emit_pandoc
    except ImportError as exc:  # pragma: no cover - defensive
        print(f"ERROR: emit module unavailable: {exc}", file=sys.stderr)
        sys.exit(1)

    documents = meta.get("documents", {})
    selected = {args.doc: documents[args.doc]} if args.doc else documents
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    invalid = [f for f in formats if f not in emit_pandoc.SUPPORTED_FORMATS]
    if invalid:
        print(
            f"ERROR: unsupported format(s) {invalid}; expected one of "
            f"{list(emit_pandoc.SUPPORTED_FORMATS)}",
            file=sys.stderr,
        )
        sys.exit(2)

    failures = 0
    for doc_id, cfg in selected.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("note", "").startswith("This is an input file"):
            print(f"  SKIP {doc_id}: input fragment")
            continue
        src_rel = cfg.get("src", "")
        if not src_rel:
            print(f"  SKIP {doc_id}: no src in meta.yaml")
            continue
        tex = CONTENT_ROOT / src_rel
        if not tex.exists():
            print(f"  SKIP {doc_id}: {tex} not found")
            continue
        out_dir = BUILD_DIR / _artifact_subdir(doc_id, cfg)
        title = cfg.get("title", doc_id)
        try:
            results = emit_pandoc.emit_all(tex, out_dir, doc_id, formats=formats, title=title)
        except emit_pandoc.PandocMissing as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            failures += 1
            stderr = (exc.stderr or "").strip()
            print(f"  FAIL {doc_id}: pandoc exit {exc.returncode}")
            if stderr:
                print(f"    | {stderr[:300]}", file=sys.stderr)
            continue
        for r in results:
            print(f"  OK   {doc_id} [{r.format}] → {r.output_path}")

    print(f"\nResults: {len(selected) - failures} ok, {failures} failed")
    if failures and getattr(args, "strict", False):
        sys.exit(1)


def cmd_tailor(args, meta):
    """Generate a tailored document from a brief."""
    try:
        tailor = _import_tailor_module()
    except ImportError:
        print("ERROR: tailor module not found", file=sys.stderr)
        sys.exit(1)

    brief_path = Path(args.brief)
    doc_type = args.type
    output_id = args.id or brief_path.stem
    base_path = getattr(args, "base", None)
    mode = getattr(args, "mode", "draft")

    # Generate tailored YAML
    use_ai = not getattr(args, "no_ai", False)
    yaml_path = tailor.generate(brief_path, doc_type, output_id, base_path, use_ai)
    print(f"  TAILOR {output_id} -> {yaml_path}")

    if args.render or args.build:
        try:
            render_module = _import_render_module()

            # Link tailored data so render_document finds it under the
            # template's doc_type ID (e.g. data/tailored/cv.yaml).
            tailored_dir = TAILORED_DIR
            fallback_tailored_dir = PROJECT_ROOT / "data" / "tailored"
            if not tailored_dir.exists() and fallback_tailored_dir.exists():
                tailored_dir = fallback_tailored_dir
            tailored_dir.mkdir(parents=True, exist_ok=True)
            type_link = tailored_dir / f"{doc_type}.yaml"
            if output_id != doc_type:
                shutil.copy2(yaml_path, type_link)

            render_module.render_document(
                doc_type, fmt="latex", build_mode=mode, content_root=CONTENT_ROOT
            )

            # Rename the rendered file to the output_id
            rendered_dir = RENDERED_DIR
            src_tex = rendered_dir / f"{doc_type}.tex"
            dst_tex = rendered_dir / f"{output_id}.tex"
            if src_tex.exists() and output_id != doc_type:
                shutil.copy2(src_tex, dst_tex)
        except ImportError:
            print("ERROR: Jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
            sys.exit(1)

    if args.build:
        # Use the original document's source path so TEXINPUTS resolves
        # assets (figures/) from the correct directory.
        documents = meta.get("documents", {})
        if doc_type in documents:
            original_src = documents[doc_type]["src"]
        else:
            original_src = f"build/.cache/rendered/{output_id}.tex"

        # Load tailored YAML for PDF metadata
        with open(yaml_path) as _f:
            tailored_data = yaml.safe_load(_f)

        # Construct a human-readable title from the data
        if doc_type == "cv":
            name = tailored_data.get("name", {})
            role = tailored_data.get("role", "")
            title = f"{name.get('first', '')} {name.get('last', '')} -- {role}"
        else:
            title = tailored_data.get("title", output_id)

        doc_config = {
            "class": f"pub-{doc_type}",
            "src": original_src,
            "title": title,
            "version": "1.0",
            "description": f"Tailored {doc_type}",
            "subject": tailored_data.get("subject", ""),
            "keywords": tailored_data.get("keywords", ""),
        }
        build_document(output_id, doc_config, mode, meta)


def main(argv=None):
    """Entry point for `python -m inclusio.cli.build`.

    Parses the top-level subcommand (build / render / blog / tailor /
    fix / sitemap / assets / lint / clean / distclean / list / emit /
    judge / provenance / import-resume) and dispatches to the matching
    `cmd_*` handler. With no subcommand, prints help and exits 0.
    """
    parser = argparse.ArgumentParser(
        description="Publications build orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  build     Compile documents (default: all, draft mode)
  render    Render Jinja2 templates to LaTeX/Markdown/JSON
  blog      Render blog posts to Shokunin-compatible Markdown
  tailor    Generate tailored document from a brief/job description
  fix       Auto-fix semantic violations in source files
  sitemap   Generate semantic search metadata (build/site-map.json)
  assets    Run MMD → SVG → PDF/PNG asset pipeline
  lint      Run quality checks (semantic, chktex, vale)
  clean     Remove build/ directory
  distclean Remove build output + dev artifacts (.coverage, .pytest_cache)
  list      Show registered documents
        """,
    )
    parser.add_argument(
        "--content-dir",
        help="External content directory (overrides INCLUSIO_CONTENT_DIR env var)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # build
    build_parser = subparsers.add_parser("build", help="Compile documents")
    build_parser.add_argument(
        "--mode",
        choices=["draft", "submission", "camera-ready"],
        default="draft",
        help="Build mode (default: draft)",
    )
    build_parser.add_argument(
        "--doc",
        help="Build a specific document by ID (see 'list' command)",
    )
    build_parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=1,
        help="Number of parallel build jobs (default: 1)",
    )
    build_parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass content cache and rebuild all",
    )
    build_parser.add_argument(
        "--jobs-only",
        action="store_true",
        help="Build only tailored or job-specific documents",
    )

    # render
    render_parser = subparsers.add_parser("render", help="Render Jinja2 templates")
    render_parser.add_argument(
        "--doc",
        required=True,
        help="Document ID to render",
    )
    render_parser.add_argument(
        "--format",
        choices=["latex", "markdown", "json"],
        default="latex",
        help="Output format (default: latex)",
    )
    render_parser.add_argument(
        "--mode",
        choices=["draft", "submission", "camera-ready"],
        default="draft",
        help="Build mode (default: draft)",
    )

    # fix
    fix_parser = subparsers.add_parser("fix", help="Auto-fix semantic violations")
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    fix_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show each replacement line-by-line",
    )

    # sitemap
    sitemap_parser = subparsers.add_parser("sitemap", help="Generate semantic search metadata")
    sitemap_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    sitemap_parser.add_argument("--stdout", action="store_true", help="Print to stdout")

    # blog
    blog_parser = subparsers.add_parser("blog", help="Render blog posts to Markdown")
    blog_parser.add_argument(
        "--doc",
        help="Render a specific blog post by ID",
    )

    # tailor
    tailor_parser = subparsers.add_parser("tailor", help="Generate tailored document from brief")
    tailor_parser.add_argument("brief", help="Path to brief/job description file")
    tailor_parser.add_argument(
        "--type",
        default="cv",
        choices=["cv", "paper", "patent", "faq", "guide"],
        help="Document type (default: cv)",
    )
    tailor_parser.add_argument("--id", help="Output document ID")
    tailor_parser.add_argument("--base", type=Path, help="Base data file")
    tailor_parser.add_argument(
        "--render",
        action="store_true",
        help="Also render to LaTeX",
    )
    tailor_parser.add_argument(
        "--build",
        action="store_true",
        help="Also compile to PDF",
    )
    tailor_parser.add_argument(
        "--mode",
        default="draft",
        choices=["draft", "submission", "camera-ready"],
        help="Build mode (default: draft)",
    )
    tailor_parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip Claude CLI, use keyword-based tailoring only",
    )

    # assets
    import_parser = subparsers.add_parser(
        "import-resume",
        help="Convert a JSON Resume document to Euxis CV YAML (#6)",
    )
    import_parser.add_argument("input", help="Path to the JSON Resume file (.json).")
    import_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output YAML path. Omit to print to stdout.",
    )

    provenance_parser = subparsers.add_parser(
        "provenance",
        help="Embed C2PA Content Credentials in a registered PDF (S8.x F7)",
    )
    provenance_parser.add_argument(
        "--doc", required=True, help="Registered document id (must already be built)."
    )
    provenance_parser.add_argument(
        "--cert",
        default=None,
        help="Path to PEM-encoded X.509 signing certificate.",
    )
    provenance_parser.add_argument(
        "--key",
        default=None,
        help="Path to the PEM-encoded private key for --cert.",
    )
    provenance_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if the PDF was signed with c2patool's test cert (CI gate).",
    )

    judge_parser = subparsers.add_parser(
        "judge",
        help="Score a registered document against an LLM/heuristic judge (S7.x)",
    )
    judge_parser.add_argument(
        "--doc", required=True, help="Registered template id (must be type=cv for ats)."
    )
    judge_parser.add_argument(
        "--judge",
        default="ats",
        choices=["ats", "citations", "jd_fit"],
        help=(
            "Which judge to run. `ats` scores a CV against Workday/"
            "Greenhouse/Lever heuristics; `citations` checks `\\cite` "
            "/ `\\bibitem` consistency on a paper; `jd_fit` ranks a CV "
            "against a job-description brief. Default: ats."
        ),
    )
    judge_parser.add_argument(
        "--brief",
        default=None,
        help=("Job-description brief path (txt/md). Required when --judge jd_fit."),
    )
    judge_parser.add_argument(
        "--json", default=None, help="Optional path to write the JSON report to."
    )
    judge_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if the grade is D or F (CI gate).",
    )
    judge_parser.add_argument(
        "--llm-url",
        default=None,
        help=(
            "Optional local LLM server URL for ATS rerank "
            "(default off; e.g. http://localhost:8080 for llama.cpp). "
            "Falls back to heuristic-only when unreachable."
        ),
    )
    judge_parser.add_argument(
        "--llm-timeout",
        type=int,
        default=30,
        help="Seconds to wait for the LLM (default 30).",
    )
    judge_parser.add_argument(
        "--llm-model",
        default="claude-opus-4-7",
        help=(
            "Model id for cloud LLMs (Anthropic / OpenAI). Default: "
            "claude-opus-4-7. Ignored for local llama.cpp URLs."
        ),
    )

    emit_parser = subparsers.add_parser(
        "emit",
        help="Emit HTML5 / JATS XML for registered documents (S6.2 + S6.3)",
    )
    emit_parser.add_argument(
        "--doc",
        default=None,
        help="Limit to one document id (default: all registered).",
    )
    emit_parser.add_argument(
        "--formats",
        default="html,jats,epub",
        help="Comma-separated subset of {html, jats, epub}. Default: all three.",
    )
    emit_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any emit fails (CI gate).",
    )

    subparsers.add_parser("assets", help="Run asset pipeline")

    # lint
    subparsers.add_parser("lint", help="Run quality checks")

    # clean
    subparsers.add_parser("clean", help="Remove build/ directory")

    # distclean
    subparsers.add_parser("distclean", help="Clean + remove dev artifacts")

    # list
    subparsers.add_parser("list", help="List registered documents")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Resolve content directory from CLI flag (highest priority)
    if getattr(args, "content_dir", None):
        _resolve_content_paths(args.content_dir)

    meta = load_meta()

    commands = {
        "build": cmd_build,
        "render": cmd_render,
        "blog": cmd_blog,
        "tailor": cmd_tailor,
        "fix": cmd_fix,
        "sitemap": cmd_sitemap,
        "assets": cmd_assets,
        "lint": cmd_lint,
        "clean": cmd_clean,
        "distclean": cmd_distclean,
        "list": cmd_list,
        "emit": cmd_emit,
        "judge": cmd_judge,
        "provenance": cmd_provenance,
        "import-resume": cmd_import_resume,
    }

    commands[args.command](args, meta)


if __name__ == "__main__":  # pragma: no cover
    main()
