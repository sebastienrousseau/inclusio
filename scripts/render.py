#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
render.py — Jinja2 rendering engine for Publications templates.

Renders structured YAML data through Jinja2 templates to produce
LaTeX, Markdown, or JSON output.

Usage:
    python scripts/render.py --doc cv
    python scripts/render.py --doc cv --format markdown
    python scripts/render.py --doc cv --format json
    python scripts/render.py --doc cv --mode draft
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# ── Paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# CONTENT_ROOT: where content lives (data/, templates/, build/).
# Defaults to PROJECT_ROOT; overridden by EUXIS_CONTENT_DIR env var.
_env_content = os.environ.get("EUXIS_CONTENT_DIR")
CONTENT_ROOT = Path(_env_content).resolve() if _env_content else PROJECT_ROOT

META_FILE = CONTENT_ROOT / "data" / "meta.yaml"
TEMPLATE_DIR = CONTENT_ROOT / "templates"
BUILD_DIR = CONTENT_ROOT / "build"
RENDERED_DIR = BUILD_DIR / ".cache" / "rendered"


def slugify(title):
    """Convert a title string to a URL-friendly slug.

    'Bug Discovered in Quantum Algorithm for Lattice-Based Crypto'
    → 'bug-discovered-in-quantum-algorithm-for-lattice-based-crypto'
    """
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)   # strip non-word chars except -
    slug = re.sub(r"[\s_]+", "-", slug)     # spaces/underscores → hyphens
    slug = re.sub(r"-{2,}", "-", slug)      # collapse multiple hyphens
    return slug.strip("-")


def create_jinja_env(template_dir=None):
    """Create a Jinja2 environment with LaTeX-safe custom delimiters.

    Avoids conflicts with LaTeX's {}, %, and # characters:
      - Block:    <% ... %>
      - Variable: << ... >>
      - Comment:  <# ... #>
    """
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def render_latex(template_name, data, template_dir=None):
    """Render a .j2 template with data, returning the LaTeX string."""
    env = create_jinja_env(template_dir)
    template = env.get_template(template_name)
    return template.render(**data)


def render_markdown(data, doc_type):
    """Render structured data to Markdown format.

    Currently supports: cv, blog
    """
    if doc_type == "cv":
        return _render_cv_markdown(data)
    if doc_type == "blog":
        return render_blog_markdown(data, "blog-post.md.j2")
    raise ValueError(f"Unknown document type for Markdown: {doc_type}")


def _render_cv_markdown(data):
    """Render CV data to Markdown."""
    lines = []
    lines.append(f"# {data['name']['first']} {data['name']['last']}")
    lines.append("")
    lines.append(f"**{data['role']}**")
    lines.append("")
    lines.append(f"Phone: {data['contact']['phone']}  ")
    lines.append(f"Email: {data['contact']['email']}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(data["summary"])
    lines.append("")

    lines.append("## Professional Experience")
    lines.append("")
    for job in data.get("experience", []):
        lines.append(f"### {job['title']} — {job['company']}")
        lines.append(f"*{job['dates']}*")
        lines.append("")
        for item in job.get("bullets", []):
            # Strip LaTeX escapes for Markdown
            clean = item.replace("\\$", "$").replace("\\&", "&")
            lines.append(f"- {clean}")
        lines.append("")

    lines.append("## Prior Experience")
    lines.append("")
    for prior in data.get("prior_experience", []):
        lines.append(
            f"- **{prior['title']}**, {prior['company']} "
            f"({prior['dates']})"
        )
    lines.append("")

    lines.append("## Skills")
    lines.append("")
    for skill in data.get("skills", []):
        desc = skill["description"].replace("\\hbox{-}", "-")
        lines.append(f"### {skill['title']}")
        lines.append("")
        lines.append(desc)
        lines.append("")

    lines.append("## Education")
    lines.append("")
    for edu in data.get("education", []):
        lines.append(
            f"- **{edu['degree']}**, {edu['institution']} "
            f"{edu['location']} ({edu['year']})"
        )
    lines.append("")

    lines.append("## Languages")
    lines.append("")
    lines.append(data.get("languages", ""))
    lines.append("")

    return "\n".join(lines)


def render_json(data):
    """Render structured data to JSON string."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def _generate_xmpdata(doc_id, data, meta, rendered_dir=None):
    """Generate XMP metadata file for PDF/A compliance.

    Writes a .xmpdata file alongside the rendered .tex, used by the
    pdfx package in final (camera-ready) mode.
    """
    out_dir = rendered_dir if rendered_dir else RENDERED_DIR
    author_name = meta.get("author", {}).get("name", "")
    lines = []
    lines.append(f"\\Title{{{data.get('title', doc_id)}}}")
    lines.append(f"\\Author{{{author_name}}}")
    lines.append(f"\\Subject{{{data.get('subject', '')}}}")
    lines.append(f"\\Description{{{data.get('description', '')}}}")
    lines.append(f"\\Keywords{{{data.get('keywords', '')}}}")
    lines.append(f"\\Copyright{{{data.get('copyright', '')}}}")
    lines.append("\\Creator{LaTeX with hyperref}")
    lines.append("\\CreatorTool{Publications Build System}")
    lines.append("\\Language{en}")
    out_dir.mkdir(parents=True, exist_ok=True)
    xmp_path = out_dir / f"{doc_id}.xmpdata"
    xmp_path.write_text("\n".join(lines) + "\n")
    return xmp_path


def render_document(doc_id, fmt="latex", build_mode="draft",
                    content_root=None):
    """Look up a template in meta.yaml and render it.

    Writes output to build/rendered/{doc_id}.{ext}

    When *content_root* is provided, all content paths (data/, templates/,
    build/) resolve from it instead of the module-level defaults.
    """
    root = Path(content_root).resolve() if content_root else CONTENT_ROOT
    meta_file = root / "data" / "meta.yaml"
    template_dir = root / "templates"
    rendered_dir = root / "build" / ".cache" / "rendered"

    if not meta_file.exists():
        print(f"ERROR: {meta_file} not found", file=sys.stderr)
        sys.exit(1)

    with open(meta_file) as f:
        meta = yaml.safe_load(f)

    templates = meta.get("templates", {})
    if doc_id not in templates:
        print(f"ERROR: No template registered for '{doc_id}'", file=sys.stderr)
        print(f"Available: {', '.join(templates.keys()) or 'none'}",
              file=sys.stderr)
        sys.exit(1)

    entry = templates[doc_id]
    template_name = entry["template"]
    data_file = root / "data" / entry["data"]
    doc_type = entry.get("type", doc_id)

    # Check for tailored data override
    tailored_data = root / "data" / "tailored" / f"{doc_id}.yaml"
    if tailored_data.exists():
        data_file = tailored_data

    if not data_file.exists():
        print(f"ERROR: Data file {data_file} not found", file=sys.stderr)
        sys.exit(1)

    with open(data_file) as f:
        data = yaml.safe_load(f)

    # Inject build mode
    data["build_mode"] = build_mode

    # Render
    ext_map = {"latex": "tex", "markdown": "md", "json": "json"}
    ext = ext_map.get(fmt, "tex")

    if fmt == "latex":
        output = render_latex(template_name, data, template_dir)
        # Generate .xmpdata for PDF/A metadata in final mode
        _generate_xmpdata(doc_id, data, meta, rendered_dir)
    elif fmt == "markdown":
        output = render_markdown(data, doc_type)
    elif fmt == "json":
        output = render_json(data)
    else:
        print(f"ERROR: Unknown format '{fmt}'", file=sys.stderr)
        sys.exit(1)

    rendered_dir.mkdir(parents=True, exist_ok=True)
    out_path = rendered_dir / f"{doc_id}.{ext}"
    out_path.write_text(output, encoding="utf-8")
    print(f"Rendered {doc_id} → {out_path}")
    return output


def render_blog_markdown(data, template_name, template_dir=None):
    """Render YAML data through a .md.j2 template for blog output."""
    env = create_jinja_env(template_dir)
    template = env.get_template(template_name)
    return template.render(**data)


def convert_latex_to_blog(tex_path, meta_entry, content_root=None):
    """Convert a .tex file to blog Markdown via pandoc with Shokunin frontmatter."""
    root = Path(content_root) if content_root else CONTENT_ROOT
    src = root / tex_path

    result = subprocess.run(
        [
            "pandoc",
            "--from=latex",
            "--to=gfm",
            "--mathjax",
            "--wrap=none",
            str(src),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pandoc conversion failed for {tex_path}: {result.stderr}"
        )

    # Build Shokunin SSG frontmatter from meta_entry
    fm_lines = ["---", ""]
    fm_lines.append("# Front Matter (YAML)")
    fm_lines.append("")
    fm_lines.append(f'author: "{meta_entry.get("author", "")}"')
    fm_lines.append(f'copyright: "{meta_entry.get("copyright", "")}"')
    fm_lines.append(f'date: "{meta_entry.get("date", "")}"')
    fm_lines.append(f'description: "{meta_entry.get("description", "")}"')
    fm_lines.append(f'layout: "{meta_entry.get("layout", "report")}"')
    fm_lines.append(f'name: "{meta_entry.get("name", "")}"')
    fm_lines.append(f'subtitle: "{meta_entry.get("subtitle", "")}"')
    tags = meta_entry.get("tags", [])
    fm_lines.append(f'tags: "{", ".join(tags)}"')
    fm_lines.append(f'title: "{meta_entry["title"]}"')
    fm_lines.append(f'url: "{meta_entry.get("url", "")}"')
    fm_lines.append("")
    fm_lines.append("---")
    fm_lines.append("")

    return "\n".join(fm_lines) + result.stdout


def render_blog(blog_id, blog_config, content_root=None):
    """Orchestrator: render a single blog post (jinja2 or pandoc convert).

    Writes output to build/blog/YYYY-MM-DD-slug.md.
    """
    root = Path(content_root) if content_root else CONTENT_ROOT
    blog_type = blog_config.get("type", "jinja2")
    title = blog_config.get("title", blog_id)
    slug = slugify(title)
    post_date = blog_config.get("date", date.today().isoformat())

    if blog_type == "jinja2":
        data_file = root / "data" / blog_config["data"]
        with open(data_file) as f:
            data = yaml.safe_load(f)
        template_name = blog_config.get("template", "blog-post.md.j2")
        template_dir = root / "templates"
        output = render_blog_markdown(data, template_name, template_dir)
    elif blog_type == "convert":
        output = convert_latex_to_blog(
            blog_config["src"], blog_config, root
        )
    else:
        raise ValueError(f"Unknown blog type: {blog_type}")

    out_dir = root / "build" / "blog"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{post_date}-{slug}.md"
    out_path = out_dir / filename
    out_path.write_text(output, encoding="utf-8")
    print(f"  BLOG {blog_id} → {out_path}")
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Render Jinja2 templates to LaTeX/Markdown/JSON"
    )
    parser.add_argument(
        "--doc",
        required=True,
        help="Document ID to render (must be registered in meta.yaml templates:)",
    )
    parser.add_argument(
        "--format",
        choices=["latex", "markdown", "json"],
        default="latex",
        help="Output format (default: latex)",
    )
    parser.add_argument(
        "--mode",
        choices=["draft", "submission", "camera-ready"],
        default="draft",
        help="Build mode (default: draft)",
    )
    args = parser.parse_args()
    render_document(args.doc, args.format, args.mode)


if __name__ == "__main__":  # pragma: no cover
    main()
