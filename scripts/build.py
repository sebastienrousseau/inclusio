#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
build.py — Unified build orchestrator for Publications.

Replaces 5× latex-build.mk (2,925 lines) + 5× project Makefiles.

Usage:
    python scripts/build.py build [--mode draft|submission|camera-ready] [--doc DOC]
    python scripts/build.py assets
    python scripts/build.py lint
    python scripts/build.py clean
    python scripts/build.py list
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


# ── Paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
META_FILE = PROJECT_ROOT / "data" / "meta.yaml"
BUILD_DIR = PROJECT_ROOT / "build"
CACHE_DIR = BUILD_DIR / ".cache"
RENDERED_DIR = CACHE_DIR / "rendered"


def load_meta():
    """Load and return the document manifest from data/meta.yaml."""
    if not META_FILE.exists():
        print(f"ERROR: {META_FILE} not found", file=sys.stderr)
        sys.exit(1)
    with open(META_FILE) as f:
        return yaml.safe_load(f)


def check_tool(name):
    """Check if a tool is available on PATH."""
    return shutil.which(name) is not None


def check_tools():
    """Verify required build tools are installed."""
    required = ["pdflatex", "bibtex"]
    missing = [t for t in required if not check_tool(t)]
    if missing:
        print(f"ERROR: Missing tools: {', '.join(missing)}", file=sys.stderr)
        print("Install TeX Live or use 'nix develop' / Docker.", file=sys.stderr)
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
    paths += [
        str(PROJECT_ROOT / "assets"),
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


def _build_xmp_xml(title, author_name, subject, description, keywords,
                   copyright_text, copyright_url, author_role, producer):
    """Build a properly formatted XMP XML packet for Adobe compatibility.

    Uses explicit namespace declarations on rdf:Description and proper
    RDF containers (rdf:Alt for language alternatives, rdf:Seq for
    ordered lists, rdf:Bag for unordered sets) so that Adobe Acrobat
    reads every field correctly.
    """
    from xml.sax.saxutils import escape

    t = escape(title)
    a = escape(author_name)
    s = escape(subject)
    d = escape(description)
    k = escape(keywords)
    cr = escape(copyright_text)
    cu = escape(copyright_url) if copyright_url else ""
    ar = escape(author_role)
    p = escape(producer)

    web_stmt = (f"      <xmpRights:WebStatement>{cu}"
                f"</xmpRights:WebStatement>\n") if cu else ""

    xmp = (
        '<?xpacket begin="\xef\xbb\xbf" '
        'id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        '  <rdf:RDF xmlns:rdf='
        '"http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '    <rdf:Description rdf:about=""\n'
        '        xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        '        xmlns:pdf="http://ns.adobe.com/pdf/1.3/"\n'
        '        xmlns:xmp="http://ns.adobe.com/xap/1.0/"\n'
        '        xmlns:xmpRights='
        '"http://ns.adobe.com/xap/1.0/rights/"\n'
        '        xmlns:photoshop='
        '"http://ns.adobe.com/photoshop/1.0/"\n'
        '        xmlns:pdfuaid='
        '"http://www.aiim.org/pdfua/ns/id/">\n'
        '      <dc:title>\n'
        '        <rdf:Alt>\n'
        f'          <rdf:li xml:lang="x-default">{t}</rdf:li>\n'
        '        </rdf:Alt>\n'
        '      </dc:title>\n'
        '      <dc:creator>\n'
        '        <rdf:Seq>\n'
        f'          <rdf:li>{a}</rdf:li>\n'
        '        </rdf:Seq>\n'
        '      </dc:creator>\n'
        '      <dc:subject>\n'
        '        <rdf:Bag>\n'
        f'          <rdf:li>{s}</rdf:li>\n'
        '        </rdf:Bag>\n'
        '      </dc:subject>\n'
        '      <dc:description>\n'
        '        <rdf:Alt>\n'
        f'          <rdf:li xml:lang="x-default">{d}</rdf:li>\n'
        '        </rdf:Alt>\n'
        '      </dc:description>\n'
        '      <dc:rights>\n'
        '        <rdf:Alt>\n'
        f'          <rdf:li xml:lang="x-default">{cr}</rdf:li>\n'
        '        </rdf:Alt>\n'
        '      </dc:rights>\n'
        f'      <pdf:Keywords>{k}</pdf:Keywords>\n'
        f'      <pdf:Producer>{p}</pdf:Producer>\n'
        '      <xmp:CreatorTool>LaTeX with hyperref'
        '</xmp:CreatorTool>\n'
        '      <xmpRights:Marked>True</xmpRights:Marked>\n'
        f'{web_stmt}'
        f'      <photoshop:AuthorsPosition>{ar}'
        f'</photoshop:AuthorsPosition>\n'
        f'      <photoshop:CaptionWriter>{a}'
        f'</photoshop:CaptionWriter>\n'
        '      <pdfuaid:part>1</pdfuaid:part>\n'
        '    </rdf:Description>\n'
        '  </rdf:RDF>\n'
        '</x:xmpmeta>\n'
        + ' ' * 2048 + '\n'
        '<?xpacket end="w"?>'
    )
    return xmp


def _post_process_pdf(pdf_path, doc_id, doc_config, meta):
    """Apply metadata, accessibility tagging, and encryption in one pass.

    Writes XMP as explicit XML (not via pikepdf's open_metadata) so that
    Adobe Acrobat reads every field — Author Title, Description Writer,
    Copyright Status/Notice/URL, PDF/UA compliance.
    """
    try:
        import pikepdf
    except ImportError:
        return  # pikepdf optional — metadata from hyperref still works

    author = meta.get("author", {})
    author_name = author.get("name", "")
    author_role = author.get("role", "")
    copyright_text = author.get("copyright", "")
    copyright_url = author.get("copyright_url", "")
    producer = author.get("publisher", author_name)
    title = doc_config.get("title", doc_id)
    subject = doc_config.get("subject", "")
    description = doc_config.get("description", "")
    keywords = doc_config.get("keywords", "")

    content_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        # ── 1. XMP metadata as hand-crafted XML ──────────────────────
        xmp_xml = _build_xmp_xml(
            title, author_name, subject, description, keywords,
            copyright_text, copyright_url, author_role, producer,
        )
        pdf.Root["/Metadata"] = pdf.make_indirect(
            pikepdf.Stream(pdf, xmp_xml.encode("utf-8")),
        )
        pdf.Root["/Metadata"]["/Type"] = pikepdf.Name("/Metadata")
        pdf.Root["/Metadata"]["/Subtype"] = pikepdf.Name("/XML")

        # ── 2. Document info dictionary (legacy, read by Adobe) ─────
        pdf.docinfo["/Title"] = title
        pdf.docinfo["/Author"] = author_name
        pdf.docinfo["/Subject"] = subject
        pdf.docinfo["/Keywords"] = keywords
        pdf.docinfo["/Creator"] = "LaTeX with hyperref"
        pdf.docinfo["/Producer"] = producer

        # ── 3. PDF/UA accessibility — catalog entries ───────────────
        # LuaLaTeX + \DocumentMetadata produces these natively; only
        # add them as fallbacks when the compiler didn't.
        if "/MarkInfo" not in pdf.Root:
            pdf.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})
        if "/Lang" not in pdf.Root:
            pdf.Root["/Lang"] = pikepdf.String("en")
        if "/ViewerPreferences" not in pdf.Root:
            pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary({
                "/DisplayDocTitle": True,
            })

        # ── 4. Encryption (AES-256) ────────────────────────────────
        perms = pikepdf.Permissions(
            print_highres=True,
            print_lowres=True,
            extract=False,
            modify_annotation=False,
            modify_form=False,
            modify_assembly=False,
            modify_other=False,
            accessibility=True,
        )

        pdf.save(
            pdf_path,
            encryption=pikepdf.Encryption(
                owner=content_hash,
                user="",
                R=6,
                allow=perms,
                metadata=False,
            ),
        )


TAILORED_DIR = PROJECT_ROOT / "data" / "tailored"


def _artifact_subdir(doc_id, doc_config):
    """Derive the domain subfolder for a document's output.

    Maps src path to output domain:
      src/cvs/...     -> cvs/
      src/papers/...  -> papers/
      src/patents/... -> patents/
      src/faqs/...    -> faqs/
      src/guides/...  -> guides/
      (tailored)      -> jobs/
    """
    if doc_config.get("tailored"):
        return "jobs"
    src = doc_config.get("src", "")
    if src.startswith("src/"):
        parts = src.split("/")
        if len(parts) >= 2:
            return parts[1]  # cvs, papers, patents, faqs, guides
    if "build/rendered" in src or doc_config.get("description", "").startswith("Tailored"):
        return "jobs"
    return ""


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

        # Infer document type — look for CV-specific keys
        if "experience" in data or "skills" in data:
            doc_type = "cv"
        else:
            doc_type = "paper"  # fallback

        template_entry = templates.get(doc_type, {})
        template_name = template_entry.get("template", f"{doc_type}.tex.j2")

        # Render through Jinja2 template
        try:
            from render import render_latex, _generate_xmpdata, TEMPLATE_DIR
            data["build_mode"] = data.get("build_mode", "draft")
            output = render_latex(template_name, data)
            RENDERED_DIR.mkdir(parents=True, exist_ok=True)
            rendered_path = RENDERED_DIR / f"{doc_id}.tex"
            rendered_path.write_text(output, encoding="utf-8")
            _generate_xmpdata(doc_id, data, meta)
        except Exception as exc:
            print(f"  WARN: Could not render tailored {doc_id}: {exc}",
                  file=sys.stderr)
            continue

        # Copy rendered .tex, .xmpdata, and shared figures into
        # src/{category}/{doc_id}/ so every file needed to compile
        # lives in one self-contained directory.
        category = type_to_category.get(doc_type, f"{doc_type}s")
        src_subdir = PROJECT_ROOT / "src" / category / doc_id
        src_subdir.mkdir(parents=True, exist_ok=True)
        src_tex = src_subdir / f"{doc_id}.tex"
        src_tex.write_text(output, encoding="utf-8")
        xmpdata_rendered = RENDERED_DIR / f"{doc_id}.xmpdata"
        if xmpdata_rendered.exists():
            shutil.copy2(xmpdata_rendered,
                         src_subdir / f"{doc_id}.xmpdata")

        # Copy shared figures from parent category directory
        figures_dir = PROJECT_ROOT / "src" / category / "figures"
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


def build_document(doc_id, doc_config, mode, meta, force=False):
    """Compile a single document."""
    src_path = PROJECT_ROOT / doc_config["src"]
    original_src_dir = src_path.parent

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
        fig_dir = str(PROJECT_ROOT / figures_src)
        sep = ":" if os.name != "nt" else ";"
        env["TEXINPUTS"] = fig_dir + sep + env["TEXINPUTS"]

    # Compiler settings from meta
    compiler = meta.get("build", {}).get("compiler", "pdflatex")
    max_passes = meta.get("build", {}).get("max_passes", 5)
    bib_engine = meta.get("build", {}).get("bib_engine", "bibtex")

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
    mode_opt = mode_to_option(mode)
    force = getattr(args, "force", False)
    jobs = getattr(args, "jobs", 1)
    documents = meta.get("documents", {})

    # Discover tailored documents from data/tailored/
    tailored = _discover_tailored(meta)
    all_documents = {**documents, **tailored}

    if args.doc:
        if args.doc not in all_documents:
            print(f"ERROR: Unknown document '{args.doc}'", file=sys.stderr)
            print(f"Available: {', '.join(all_documents.keys())}",
                  file=sys.stderr)
            sys.exit(1)
        docs_to_build = {args.doc: all_documents[args.doc]}
    else:
        docs_to_build = all_documents

    print(f"Building {len(docs_to_build)} document(s) in {mode} mode"
          f" (jobs={jobs})...\n")

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
                pool.submit(
                    build_document, doc_id, config, mode, meta, force
                ): doc_id
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

    result = subprocess.run(["bash", str(script)], cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


def cmd_lint(args, meta):
    """Run quality checks."""
    errors = 0

    # 1. Semantic check
    print("Running semantic check...")
    check_script = PROJECT_ROOT / "scripts" / "check-semantic.sh"
    if check_script.exists():
        result = subprocess.run(["bash", str(check_script)], cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            errors += 1
    else:
        print("  SKIP: check-semantic.sh not found")

    # 2. chktex
    if check_tool("chktex"):
        print("\nRunning chktex...")
        for tex_file in (PROJECT_ROOT / "src").rglob("*.tex"):
            result = subprocess.run(
                ["chktex", "-q", str(tex_file)],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                print(f"  {tex_file.relative_to(PROJECT_ROOT)}: warnings found")
                errors += 1
    else:
        print("  SKIP: chktex not installed")

    # 3. Vale
    if check_tool("vale"):
        print("\nRunning vale...")
        result = subprocess.run(
            ["vale", "src/"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
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
        import render as render_module
    except ImportError:
        print("ERROR: Jinja2 not installed. Run: pip install jinja2",
              file=sys.stderr)
        sys.exit(1)

    doc_id = args.doc
    fmt = getattr(args, "format", "latex")
    mode = getattr(args, "mode", "draft")
    render_module.render_document(doc_id, fmt, mode)


def cmd_fix(args, meta):
    """Auto-fix semantic violations in source files."""
    script = SCRIPT_DIR / "fix-semantic.py"
    if not script.exists():
        print(f"ERROR: {script} not found", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(script), "src/"]
    if getattr(args, "dry_run", False):
        cmd.append("--dry-run")
    if getattr(args, "verbose", False):
        cmd.append("--verbose")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


def cmd_sitemap(args, meta):
    """Generate semantic search metadata."""
    script = SCRIPT_DIR / "sitemap.py"
    if not script.exists():
        print(f"ERROR: {script} not found", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(script)]
    if getattr(args, "pretty", False):
        cmd.append("--pretty")
    if getattr(args, "stdout", False):
        cmd.append("--stdout")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


def cmd_blog(args, meta):
    """Render blog posts to Jekyll-compatible Markdown."""
    try:
        import render as render_module
    except ImportError:
        print("ERROR: Jinja2 not installed. Run: pip install jinja2",
              file=sys.stderr)
        sys.exit(1)

    blog_entries = meta.get("blog", {})
    if not blog_entries:
        print("No blog entries registered in meta.yaml")
        return

    if args.doc:
        if args.doc not in blog_entries:
            print(f"ERROR: Unknown blog post '{args.doc}'", file=sys.stderr)
            print(f"Available: {', '.join(blog_entries.keys())}",
                  file=sys.stderr)
            sys.exit(1)
        entries = {args.doc: blog_entries[args.doc]}
    else:
        entries = blog_entries

    # Check pandoc availability only if convert-type entries exist
    convert_entries = {k: v for k, v in entries.items()
                       if v.get("type") == "convert"}
    if convert_entries and not check_tool("pandoc"):
        print("ERROR: pandoc is required for 'convert' blog posts but "
              "is not installed.", file=sys.stderr)
        print("Install pandoc or use only type: jinja2 posts.",
              file=sys.stderr)
        sys.exit(1)

    print(f"Rendering {len(entries)} blog post(s)...\n")

    for blog_id, config in entries.items():
        render_module.render_blog(blog_id, config, PROJECT_ROOT)

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


def cmd_tailor(args, meta):
    """Generate a tailored document from a brief."""
    try:
        import tailor
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
    yaml_path = tailor.generate(brief_path, doc_type, output_id, base_path,
                                use_ai)
    print(f"  TAILOR {output_id} -> {yaml_path}")

    if args.render or args.build:
        try:
            import render as render_module

            # Link tailored data so render_document finds it under the
            # template's doc_type ID (e.g. data/tailored/cv.yaml).
            tailored_dir = PROJECT_ROOT / "data" / "tailored"
            type_link = tailored_dir / f"{doc_type}.yaml"
            if output_id != doc_type:
                shutil.copy2(yaml_path, type_link)

            render_module.render_document(doc_type, fmt="latex",
                                          build_mode=mode)

            # Rename the rendered file to the output_id
            rendered_dir = RENDERED_DIR
            src_tex = rendered_dir / f"{doc_type}.tex"
            dst_tex = rendered_dir / f"{output_id}.tex"
            if src_tex.exists() and output_id != doc_type:
                shutil.copy2(src_tex, dst_tex)
        except ImportError:
            print("ERROR: Jinja2 not installed. Run: pip install jinja2",
                  file=sys.stderr)
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


def main():
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
        "--jobs", "-j",
        type=int,
        default=1,
        help="Number of parallel build jobs (default: 1)",
    )
    build_parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass content cache and rebuild all",
    )

    # render
    render_parser = subparsers.add_parser(
        "render", help="Render Jinja2 templates"
    )
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
    fix_parser = subparsers.add_parser(
        "fix", help="Auto-fix semantic violations"
    )
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
    sitemap_parser = subparsers.add_parser(
        "sitemap", help="Generate semantic search metadata"
    )
    sitemap_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON"
    )
    sitemap_parser.add_argument(
        "--stdout", action="store_true", help="Print to stdout"
    )

    # blog
    blog_parser = subparsers.add_parser(
        "blog", help="Render blog posts to Markdown"
    )
    blog_parser.add_argument(
        "--doc",
        help="Render a specific blog post by ID",
    )

    # tailor
    tailor_parser = subparsers.add_parser(
        "tailor", help="Generate tailored document from brief"
    )
    tailor_parser.add_argument(
        "brief", help="Path to brief/job description file"
    )
    tailor_parser.add_argument(
        "--type",
        default="cv",
        choices=["cv", "paper", "patent", "faq", "guide"],
        help="Document type (default: cv)",
    )
    tailor_parser.add_argument(
        "--id", help="Output document ID"
    )
    tailor_parser.add_argument(
        "--base", type=Path, help="Base data file"
    )
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
    subparsers.add_parser("assets", help="Run asset pipeline")

    # lint
    subparsers.add_parser("lint", help="Run quality checks")

    # clean
    subparsers.add_parser("clean", help="Remove build/ directory")

    # distclean
    subparsers.add_parser("distclean", help="Clean + remove dev artifacts")

    # list
    subparsers.add_parser("list", help="List registered documents")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

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
    }

    commands[args.command](args, meta)


if __name__ == "__main__":  # pragma: no cover
    main()
