#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
render.py — Jinja2 rendering engine for Publications templates.

Renders structured YAML data through Jinja2 templates to produce
LaTeX, Markdown, or JSON output.

Usage:
    python -m inclusio.cli.render --doc cv
    python -m inclusio.cli.render --doc cv --format markdown
    python -m inclusio.cli.render --doc cv --format json
    python -m inclusio.cli.render --doc cv --mode draft
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
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_SUBPROCESS_TIMEOUT = int(os.environ.get("EUXIS_SUBPROCESS_TIMEOUT", "300"))

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
    slug = re.sub(r"[^\w\s-]", "", slug)  # strip non-word chars except -
    slug = re.sub(r"[\s_]+", "-", slug)  # spaces/underscores → hyphens
    slug = re.sub(r"-{2,}", "-", slug)  # collapse multiple hyphens
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

    Supports dedicated CV data and falls back to a generic Markdown renderer
    for other structured document types.
    """
    if doc_type == "cv":
        return _render_cv_markdown(data)
    if doc_type == "blog":
        return render_blog_markdown(data, "blog-post.md.j2")
    return _render_generic_markdown(data, doc_type)


def _render_cv_markdown(data):
    """Render CV data to Workday-friendly Markdown.

    Canonical section headings (Experience / Skills / Education) are used
    instead of marketing variants so Workday's parser maps directly to its
    Experience / Skills / Education fields. Handles both competency shapes
    (flat strings and {title, description} dicts) and optional
    scope_line / subheadline / innovation / prior_experience blocks.
    """
    lines = []
    lines.append(f"# {data['name']['first']} {data['name']['last']}")
    lines.append("")
    lines.append(f"**{_strip_markdown_escapes(data['role'])}**")
    lines.append("")

    scope_line = data.get("scope_line")
    if scope_line:
        lines.append(f"*{_strip_markdown_escapes(scope_line)}*")
        lines.append("")

    subheadline = data.get("subheadline")
    if subheadline:
        lines.append(_strip_markdown_escapes(subheadline))
        lines.append("")

    contact = data.get("contact", {})
    contact_parts = [
        contact.get("phone"),
        contact.get("email"),
        "linkedin.com/in/sebastienrousseau",
        "sebastienrousseau.com",
    ]
    contact_line = " · ".join(p for p in contact_parts if p)
    if contact_line:
        lines.append(contact_line)
        lines.append("")

    summary = data.get("executive_profile") or data.get("summary", "")
    if summary:
        lines.append("## Executive Profile" if data.get("executive_profile") else "## Summary")
        lines.append("")
        lines.append(_strip_markdown_escapes(summary))
        lines.append("")

    achievements = data.get("achievements", [])
    if achievements:
        lines.append("## Selected Impact")
        lines.append("")
        for item in achievements:
            lines.append(f"- {_strip_markdown_escapes(item)}")
        lines.append("")

    lines.append("## Experience")
    lines.append("")
    for job in data.get("experience", []):
        if job.get("roles"):
            for role_entry in job.get("roles", []):
                heading = f"{job['company']} — {role_entry['title']}"
                lines.append(f"### {_strip_markdown_escapes(heading)}")
                details = " | ".join(
                    part
                    for part in (
                        job.get("location"),
                        role_entry.get("dates") or job.get("dates"),
                    )
                    if part
                )
                if details:
                    lines.append(_strip_markdown_escapes(details))
                lines.append("")
                if job.get("context"):
                    lines.append(_strip_markdown_escapes(job["context"]))
                    lines.append("")
                for item in role_entry.get("bullets", []):
                    lines.append(f"- {_strip_markdown_escapes(item)}")
                lines.append("")
            continue

        # Flat-shape job entry (single role, no nested roles[])
        title = job.get("title", "")
        company = job.get("company", "")
        heading = f"{company} — {title}" if company and title else (company or title)
        lines.append(f"### {_strip_markdown_escapes(heading)}")
        details = " | ".join(part for part in (job.get("location"), job.get("dates")) if part)
        if details:
            lines.append(_strip_markdown_escapes(details))
        lines.append("")
        for item in job.get("bullets", []):
            lines.append(f"- {_strip_markdown_escapes(item)}")
        lines.append("")

    prior_experience = data.get("prior_experience", [])
    if prior_experience:
        for prior in prior_experience:
            heading = f"{prior['company']} — {prior['title']}"
            lines.append(f"### {_strip_markdown_escapes(heading)}")
            details = " | ".join(
                part for part in (prior.get("location"), prior.get("dates")) if part
            )
            if details:
                lines.append(_strip_markdown_escapes(details))
            lines.append("")
            for item in prior.get("bullets", []) or []:
                lines.append(f"- {_strip_markdown_escapes(item)}")
            if prior.get("bullets"):
                lines.append("")

    innovation = data.get("innovation", [])
    if innovation:
        lines.append("## Patents & Publications")
        lines.append("")
        for item in innovation:
            lines.append(f"- {_strip_markdown_escapes(item)}")
        lines.append("")

    competencies = data.get("competencies")
    skills = data.get("skills", [])
    if competencies:
        lines.append("## Skills")
        lines.append("")
        # Two supported shapes:
        #   flat strings  -> single middle-dot separated line
        #   {title, description} dicts -> bulleted list
        if competencies and isinstance(competencies[0], str):
            line = " · ".join(_strip_markdown_escapes(c) for c in competencies)
            lines.append(line)
            lines.append("")
        else:
            for item in competencies:
                lines.append(
                    f"- **{_strip_markdown_escapes(item['title'])}**: "
                    f"{_strip_markdown_escapes(item['description'])}"
                )
            lines.append("")
    elif skills:
        lines.append("## Skills")
        lines.append("")
        for skill in skills:
            desc = _strip_markdown_escapes(skill["description"]).replace("\\hbox{-}", "-")
            lines.append(f"### {skill['title']}")
            lines.append("")
            lines.append(desc)
            lines.append("")

    lines.append("## Education")
    lines.append("")
    for edu in data.get("education", []):
        lines.append(
            f"- **{_strip_markdown_escapes(edu['degree'])}** | "
            f"{_strip_markdown_escapes(edu['institution'])}, "
            f"{_strip_markdown_escapes(edu['location'])} | "
            f"{_strip_markdown_escapes(edu['year'])}"
        )
    languages = data.get("languages")
    if languages:
        lines.append(f"- **Languages** | {languages}")
    lines.append("")

    return "\n".join(lines)


def _strip_markdown_escapes(text):
    """Remove LaTeX-oriented markup when emitting Markdown.

    Strips escape sequences (\\$, \\&, \\%, \\_), unwraps \\textbf{...} and
    \\textit{...} into Markdown emphasis, swaps non-breaking ties (~) and
    en-dash digraphs (--) for plain text, and substitutes common LaTeX
    macros (\\textperiodcentered, \\enspace, \\hfill, etc.) with their
    rendered equivalents.
    """
    import re

    if not isinstance(text, str):
        return text
    out = text
    # Unwrap \textbf{...} -> **...**  and \textit{...} -> *...*
    out = re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", out)
    out = re.sub(r"\\textit\{([^{}]*)\}", r"*\1*", out)
    out = re.sub(r"\\emph\{([^{}]*)\}", r"*\1*", out)
    # Macro substitutions
    out = out.replace("\\textperiodcentered{}", "·")
    out = out.replace("\\textperiodcentered", "·")
    out = out.replace("\\enspace{}", " ")
    out = out.replace("\\enspace", " ")
    out = out.replace("\\hfill", " ")
    out = out.replace("\\,", " ")
    out = out.replace("\\ ", " ")
    # Escape sequences
    out = (
        out.replace("\\$", "$")
        .replace("\\&", "&")
        .replace("\\%", "%")
        .replace("\\_", "_")
        .replace("\\#", "#")
    )
    # LaTeX non-breaking tie (~) -> plain space
    out = out.replace("~", " ")
    # LaTeX en-dash digraph (--) and em-dash digraph (---) -> Unicode equivalents
    out = out.replace("---", "—").replace("--", "–")
    # Collapse any leftover double spaces from the substitutions above
    out = re.sub(r" {2,}", " ", out)
    return out


def _render_generic_markdown(data, doc_type):
    """Render arbitrary structured data to a readable Markdown document."""
    title = data.get("title") or data.get("subject") or doc_type.replace("-", " ").title()
    lines = [f"# {title}", ""]

    for key, value in data.items():
        if key.startswith("_") or key in {"title", "build_mode"}:
            continue
        heading = key.replace("_", " ").title()
        lines.append(f"## {heading}")
        lines.append("")
        lines.extend(_markdown_lines(value))
        lines.append("")

    return "\n".join(lines)


def _markdown_lines(value):
    """Convert nested structured values to Markdown lines."""
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            label = key.replace("_", " ").title()
            if isinstance(item, (dict, list)):
                lines.append(f"### {label}")
                lines.append("")
                lines.extend(_markdown_lines(item))
            else:
                lines.append(f"- **{label}**: {item}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                nested = _markdown_lines(item)
                if nested:
                    first, *rest = nested
                    lines.append(f"- {first}")
                    lines.extend(rest)
            else:
                lines.append(f"- {item}")
        return lines
    if value is None:
        return ["-"]
    return [str(value)]


def render_json(data):
    """Render structured data to JSON string."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def render_text(data, doc_type):
    """Render structured data to ATS-safe plain text.

    Some 2026 ATS pipelines (Workday, Greenhouse, Taleo) still extract
    text more reliably from a `.txt` artefact than from a LuaLaTeX-
    generated PDF — particularly when the PDF is tagged with
    PDF/UA-2 structure trees the ATS parser doesn't understand.

    The plain-text shadow is therefore intentionally minimal: ASCII
    where practical, Unicode dashes/middle-dots elsewhere, no
    Markdown emphasis markers, no `*` or `#` decoration. Pre-strips
    LaTeX backslash escapes so artefacts like `\\&` and `\\_` do not
    leak through.
    """
    if doc_type == "cv":
        return _render_cv_text(data)
    return _render_generic_text(data, doc_type)


def _render_cv_text(data):
    """Render CV data to ATS-safe plain text (single canonical layout).

    Section order mirrors the Workday-friendly markdown emitter so the
    same author content reads consistently across `cv.pdf`, `cv.md`,
    and `cv.txt`. Headings are unmarked (no `##`) and bullets use a
    hyphen so naive parsers don't strip them.
    """
    lines: list[str] = []
    name = data.get("name", {}) or {}
    if name.get("first") or name.get("last"):
        lines.append(f"{name.get('first', '')} {name.get('last', '')}".strip())
        lines.append("")

    role = data.get("role")
    if role:
        lines.append(_strip_text_markup(role))
        lines.append("")

    contact = data.get("contact", {}) or {}
    contact_parts = [contact.get("phone"), contact.get("email")]
    contact_line = " | ".join(_strip_text_markup(p) for p in contact_parts if p)
    if contact_line:
        lines.append(contact_line)
        lines.append("")

    summary = data.get("executive_profile") or data.get("summary")
    if summary:
        label = "Executive Profile" if data.get("executive_profile") else "Summary"
        lines.append(label)
        lines.append("-" * len(label))
        lines.append(_strip_text_markup(summary))
        lines.append("")

    achievements = data.get("achievements") or []
    if achievements:
        lines.append("Selected Impact")
        lines.append("-" * 15)
        for item in achievements:
            lines.append(f"- {_strip_text_markup(item)}")
        lines.append("")

    experience = data.get("experience") or []
    if experience:
        lines.append("Experience")
        lines.append("-" * 10)
        for job in experience:
            for role_entry in job.get("roles") or [job]:
                title = role_entry.get("title") or job.get("title", "")
                company = job.get("company", "")
                heading = f"{company} — {title}" if company and title else (company or title)
                dates = role_entry.get("dates") or job.get("dates", "")
                location = job.get("location", "")
                head_line = _strip_text_markup(heading)
                if dates:
                    head_line = f"{head_line} ({_strip_text_markup(dates)})"
                if location:
                    head_line = f"{head_line} — {_strip_text_markup(location)}"
                lines.append(head_line)
                for item in role_entry.get("bullets") or job.get("bullets") or []:
                    lines.append(f"  - {_strip_text_markup(item)}")
                lines.append("")

    competencies = data.get("competencies") or []
    skills = data.get("skills") or []
    if competencies or skills:
        lines.append("Skills")
        lines.append("-" * 6)
        if competencies and isinstance(competencies[0], str):
            lines.append(" · ".join(_strip_text_markup(c) for c in competencies))
        else:
            for item in competencies:
                if isinstance(item, dict):
                    lines.append(
                        f"- {_strip_text_markup(item.get('title', ''))}: "
                        f"{_strip_text_markup(item.get('description', ''))}"
                    )
            for skill in skills:
                if isinstance(skill, dict):
                    lines.append(
                        f"- {_strip_text_markup(skill.get('title', ''))}: "
                        f"{_strip_text_markup(skill.get('description', ''))}"
                    )
        lines.append("")

    education = data.get("education") or []
    if education:
        lines.append("Education")
        lines.append("-" * 9)
        for edu in education:
            parts = [
                edu.get("degree"),
                edu.get("institution"),
                edu.get("location"),
                edu.get("year"),
            ]
            lines.append("- " + " | ".join(_strip_text_markup(p) for p in parts if p))
        lines.append("")

    languages = data.get("languages")
    if languages:
        lines.append("Languages")
        lines.append("-" * 9)
        lines.append(_strip_text_markup(str(languages)))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_generic_text(data, doc_type):
    """Render arbitrary structured data to readable plain text."""
    title = data.get("title") or data.get("subject") or doc_type.replace("-", " ").title()
    lines = [_strip_text_markup(str(title)), "=" * max(len(str(title)), 3), ""]
    for key, value in data.items():
        if key.startswith("_") or key in {"title", "build_mode"}:
            continue
        heading = key.replace("_", " ").title()
        lines.append(heading)
        lines.append("-" * len(heading))
        lines.extend(_plain_text_lines(value, indent=0))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _plain_text_lines(value, indent=0):
    """Recursively flatten *value* into ATS-safe plain-text lines.

    Used by `_render_generic_text` to emit dict / list / scalar /
    None branches with the correct indentation level for nested
    structures.
    """
    pad = "  " * indent
    if isinstance(value, dict):
        out = []
        for k, v in value.items():
            label = k.replace("_", " ").title()
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{label}:")
                out.extend(_plain_text_lines(v, indent + 1))
            else:
                out.append(f"{pad}{label}: {_strip_text_markup(str(v))}")
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, (dict, list)):
                out.extend(_plain_text_lines(item, indent + 1))
            else:
                out.append(f"{pad}- {_strip_text_markup(str(item))}")
        return out
    if value is None:
        return [f"{pad}-"]
    return [f"{pad}{_strip_text_markup(str(value))}"]


def _strip_text_markup(text):
    """Pre-strip LaTeX escapes / markup so plain-text output is ATS-clean.

    Reuses the Markdown stripper's substitution rules but additionally
    flattens Markdown emphasis (`**…**`, `*…*`) so the resulting `.txt`
    has zero markup. The output is intentionally lossy: tables, links,
    and figures are reduced to their text content.
    """
    if not isinstance(text, str):
        return text
    out = _strip_markdown_escapes(text)
    # Flatten any Markdown emphasis the data file may have included.
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", out)
    # Drop residual backticks (inline code), they confuse some parsers.
    out = out.replace("`", "")
    return out


def _generate_xmpdata(doc_id, data, meta, rendered_dir=None):
    """Generate XMP metadata file for PDF/A compliance.

    Writes a .xmpdata file alongside the rendered .tex, used by the
    pdfx package in final (camera-ready) mode. Emits the full set of
    pdfx-supported XMP commands so Adobe's "Description" panel
    populates Copyright Status / Notice / Info and Publisher, not
    just the basic Title/Author/Keywords surfaced via hyperref's
    info dictionary.
    """
    out_dir = rendered_dir if rendered_dir else RENDERED_DIR
    author = meta.get("author", {}) or {}
    author_name = author.get("name", "")
    publisher = author.get("publisher", "")
    copyright_url = author.get("copyright_url", "")
    # pdfx accepts UTF-8 in xmpdata since v1.5 --- pass the © through
    # raw rather than substituting \textcopyright{}, which leaks an
    # empty group into dc:rights ("©{} 2026...").
    copyright_str = data.get("copyright", "") or ""
    # Title precedence: data.title (rare in this codebase) >
    # meta.documents[doc_id].title (the human title set in the
    # manifest) > doc_id slug. Without this, dc:title degrades to
    # the slug whenever the data file omits a title key.
    manifest_title = meta.get("documents", {}).get(doc_id, {}).get("title", "")
    title = data.get("title") or manifest_title or doc_id
    lines = []
    lines.append(f"\\Title{{{title}}}")
    lines.append(f"\\Author{{{author_name}}}")
    lines.append(f"\\Subject{{{data.get('subject', '')}}}")
    lines.append(f"\\Keywords{{{data.get('keywords', '')}}}")
    if copyright_str:
        lines.append(f"\\Copyright{{{copyright_str}}}")
        lines.append("\\Copyrighted{True}")
    if copyright_url:
        lines.append(f"\\CopyrightURL{{{copyright_url}}}")
    if publisher:
        lines.append(f"\\Publisher{{{publisher}}}")
    lines.append("\\CreatorTool{Euxis Publications Build System}")
    lines.append("\\Producer{LuaLaTeX + pdfx}")
    lines.append(f"\\Language{{{data.get('language', 'en')}}}")
    out_dir.mkdir(parents=True, exist_ok=True)
    xmp_path = out_dir / f"{doc_id}.xmpdata"
    xmp_path.write_text("\n".join(lines) + "\n")
    return xmp_path


def render_document(doc_id, fmt="latex", build_mode="draft", content_root=None):
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
        print(f"Available: {', '.join(templates.keys()) or 'none'}", file=sys.stderr)
        sys.exit(1)

    entry = templates[doc_id]
    template_name = entry["template"]
    data_file = root / "data" / entry["data"]
    doc_type = entry.get("type", doc_id)
    allow_tailored_override = entry.get("allow_tailored_override", True)

    # Check for tailored data override
    tailored_data = root / "data" / "tailored" / f"{doc_id}.yaml"
    if allow_tailored_override and tailored_data.exists():
        data_file = tailored_data

    if not data_file.exists():
        print(f"ERROR: Data file {data_file} not found", file=sys.stderr)
        sys.exit(1)

    with open(data_file) as f:
        data = yaml.safe_load(f)

    # Inject build mode --- translate the CLI's "camera-ready" to the
    # LaTeX class option "final" so pub-base's \DeclareOption{final}
    # fires and pdfx engages. Without this, the unknown
    # "camera-ready" option is silently swallowed and no XMP packet
    # is embedded (Adobe's Copyright/Description fields stay empty).
    _mode_to_class_option = {
        "draft": "draft",
        "submission": "submission",
        "camera-ready": "final",
        "final": "final",
    }
    data["build_mode"] = _mode_to_class_option.get(build_mode, "draft")

    # Render
    ext_map = {"latex": "tex", "markdown": "md", "json": "json", "text": "txt"}
    ext = ext_map.get(fmt, "tex")

    if fmt == "latex":
        output = render_latex(template_name, data, template_dir)
        # Generate .xmpdata for PDF/A metadata in final mode
        _generate_xmpdata(doc_id, data, meta, rendered_dir)
    elif fmt == "markdown":
        output = render_markdown(data, doc_type)
    elif fmt == "json":
        output = render_json(data)
    elif fmt == "text":
        output = render_text(data, doc_type)
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
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc conversion failed for {tex_path}: {result.stderr}")

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
        output = convert_latex_to_blog(blog_config["src"], blog_config, root)
    else:
        raise ValueError(f"Unknown blog type: {blog_type}")

    out_dir = root / "build" / "blog"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{post_date}-{slug}.md"
    out_path = out_dir / filename
    out_path.write_text(output, encoding="utf-8")
    print(f"  BLOG {blog_id} → {out_path}")
    return output


def main(argv=None):
    """Entry point for `python -m inclusio.cli.render`.

    Parses `--doc`, `--format`, `--mode`, and renders the matching
    template through Jinja2 to LaTeX / Markdown / JSON / plain-text.
    """
    parser = argparse.ArgumentParser(description="Render Jinja2 templates to LaTeX/Markdown/JSON")
    parser.add_argument(
        "--doc",
        required=True,
        help="Document ID to render (must be registered in meta.yaml templates:)",
    )
    parser.add_argument(
        "--format",
        choices=["latex", "markdown", "json", "text"],
        default="latex",
        help=(
            "Output format. `text` emits an ATS-safe plain-text shadow "
            "(e.g. for Workday/Greenhouse pipelines). Default: latex."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["draft", "submission", "camera-ready"],
        default="draft",
        help="Build mode (default: draft)",
    )
    args = parser.parse_args(argv)
    render_document(args.doc, args.format, args.mode)


if __name__ == "__main__":  # pragma: no cover
    main()
