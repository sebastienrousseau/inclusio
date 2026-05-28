#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
sitemap.py — Generate semantic search metadata from meta.yaml.

Produces build/site-map.json containing structured metadata for every
registered document, suitable for static-site search, LLM ingestion,
or CI artifact indexing.

Usage:
    python -m inclusio.cli.sitemap              # write to build/site-map.json
    python -m inclusio.cli.sitemap --pretty     # human-readable JSON
    python -m inclusio.cli.sitemap --stdout     # print to stdout instead of file
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# CONTENT_ROOT: where content lives (data/, build/).
# Defaults to PROJECT_ROOT; overridden by EUXIS_CONTENT_DIR env var.
_env_content = os.environ.get("EUXIS_CONTENT_DIR")
CONTENT_ROOT = Path(_env_content).resolve() if _env_content else PROJECT_ROOT

META_FILE = CONTENT_ROOT / "data" / "meta.yaml"
BUILD_DIR = CONTENT_ROOT / "build"
OUTPUT_FILE = BUILD_DIR / "site-map.json"


def load_meta(meta_path=None):
    """Load document manifest from meta.yaml."""
    path = Path(meta_path) if meta_path else META_FILE
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


def _classify_domain(cls_name):
    """Map a class name to its content domain."""
    mapping = {
        "pub-cv": "cv",
        "pub-paper": "paper",
        "pub-prime": "paper",
        "pub-patent": "patent",
        "pub-patent-us": "patent",
        "pub-faq": "faq",
        "pub-guide": "guide",
        "pub-preprint": "paper",
        "pub-arxiv": "paper",
        "pub-bio": "bio",
    }
    return mapping.get(cls_name, "other")


def _source_exists(src, project_root=None):
    """Check if a source file exists on disk."""
    root = Path(project_root) if project_root else PROJECT_ROOT
    return (root / src).exists()


def _slugify(title):
    """Convert a title string to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def _blog_entries(meta):
    """Extract blog entries from meta.yaml for sitemap inclusion."""
    blog = meta.get("blog", {})
    entries = []
    for blog_id, config in blog.items():
        title = config.get("title", blog_id)
        entries.append(
            {
                "id": blog_id,
                "title": title,
                "class": "blog",
                "domain": "blog",
                "src": config.get("data", config.get("src", "")),
                "version": "",
                "description": config.get("description", ""),
                "source_exists": True,
                "standalone": True,
                "type": config.get("type", "jinja2"),
                "slug": _slugify(title),
                "date": config.get("date", ""),
            }
        )
    return entries


def generate_sitemap(meta, project_root=None):
    """Generate the site-map structure from meta.yaml data."""
    documents = meta.get("documents", {})
    author = meta.get("author", {})

    entries = []
    for doc_id, config in documents.items():
        entry = {
            "id": doc_id,
            "title": config.get("title", ""),
            "class": config.get("class", ""),
            "domain": _classify_domain(config.get("class", "")),
            "src": config.get("src", ""),
            "version": config.get("version", ""),
            "description": config.get("description", ""),
            "source_exists": _source_exists(config.get("src", ""), project_root),
        }

        # Optional fields — only include if present
        if config.get("bib"):
            entry["bib"] = config["bib"]
        if config.get("pdf_a"):
            entry["pdf_a"] = config["pdf_a"]
        if config.get("docket"):
            entry["docket"] = config["docket"]
        if config.get("filing_date"):
            entry["filing_date"] = config["filing_date"]
        if config.get("options"):
            entry["options"] = config["options"]
        if config.get("assets"):
            entry["assets"] = config["assets"]
        if config.get("note"):
            entry["note"] = config["note"]
            entry["standalone"] = not config["note"].startswith("This is an input file")
        else:
            entry["standalone"] = True

        entries.append(entry)

    # Merge blog entries
    entries.extend(_blog_entries(meta))

    # Collect domains
    domains = sorted(set(e["domain"] for e in entries))

    sitemap = {
        "generated": date.today().isoformat(),
        "project": "Publications",
        "author": author.get("name", ""),
        "document_count": len(entries),
        "domains": domains,
        "documents": entries,
    }

    return sitemap


def write_sitemap(sitemap, output_path=None, pretty=False, stdout=False):
    """Write the sitemap to a file or stdout."""
    indent = 2 if pretty else None
    content = json.dumps(sitemap, indent=indent, ensure_ascii=False)

    if stdout:
        print(content)
        return

    path = Path(output_path) if output_path else OUTPUT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n")
    print(f"Written: {path} ({len(sitemap['documents'])} documents)")


def main(argv=None):
    """Entry point for `python -m inclusio.cli.sitemap`.

    Reads `data/meta.yaml`, builds a semantic-search index of every
    registered document, writes JSON to `build/site-map.json` (or
    stdout when `--stdout` is passed).
    """
    parser = argparse.ArgumentParser(description="Generate semantic search metadata from meta.yaml")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of file",
    )
    parser.add_argument("--output", "-o", help="Custom output path (default: build/site-map.json)")

    args = parser.parse_args(argv)

    meta = load_meta()
    sitemap = generate_sitemap(meta)
    write_sitemap(
        sitemap,
        output_path=args.output,
        pretty=args.pretty,
        stdout=args.stdout,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
