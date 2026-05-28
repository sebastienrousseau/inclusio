# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""JSON Resume → Euxis YAML importer (Sprint 5, #6).

JSON Resume (https://jsonresume.org/) is the open standard for CVs;
LinkedIn exports, Wantedly, Resume.io, and most modern CV builders
emit it. This module ingests a JSON Resume document and produces the
Euxis CV YAML schema that `templates/cv.tex.j2` consumes.

Mapping (JSON Resume v1 → Euxis CV YAML):

  - `basics.name` → `name: {first, last}` (split on first space)
  - `basics.label` / `basics.headline` → `role`
  - `basics.summary` → `summary` (or `executive_profile` if longer)
  - `basics.phone` → `contact.phone`
  - `basics.email` → `contact.email`
  - `basics.url` → `contact.url`
  - `basics.location.{city,region,countryCode}` → `contact.location`
  - `basics.profiles[]` → `contact.profiles` (preserved as-is)
  - `work[]` → `experience[]` (company / position / dates / bullets via highlights)
  - `volunteer[]` → folded into `experience[]` with `volunteer: true` flag
  - `education[]` → `education[]` (institution / degree / dates / location)
  - `skills[]` → `competencies[]` (name as title, keywords joined as description)
  - `languages[]` → `languages` (comma-joined)
  - `awards[]` → `innovation[]` (one item per award)
  - `publications[]` → folded into `innovation[]`
  - `projects[]` → optional `projects[]` section

Unknown / unmapped fields are preserved under a top-level
`_jsonresume_extras:` key so authors can hand-edit afterwards.

Importer is offline / stdlib-only. No network calls; no schema
fetch — the rules embedded here match JSON Resume schema v1.0.0.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

# ── Mapping helpers ────────────────────────────────────────────────────


def _split_name(full_name: str) -> dict[str, str]:
    """Split `'Jane Mary Doe'` → `{first: 'Jane', last: 'Mary Doe'}`."""
    full_name = (full_name or "").strip()
    if not full_name:
        return {"first": "", "last": ""}
    parts = full_name.split(maxsplit=1)
    if len(parts) == 1:
        return {"first": parts[0], "last": ""}
    return {"first": parts[0], "last": parts[1]}


def _format_location(loc: dict[str, Any] | None) -> str:
    """Compose a one-line location from JSON Resume's location dict."""
    if not loc:
        return ""
    bits = [loc.get("city"), loc.get("region"), loc.get("countryCode")]
    return ", ".join(b for b in bits if b)


def _format_date_range(start: str | None, end: str | None) -> str:
    """JSON Resume uses ISO `YYYY-MM-DD`. Normalise to MM/YYYY for ATS."""

    def to_mmyyyy(d: str | None) -> str:
        if not d:
            return "Present"
        parts = d.split("-")
        if len(parts) >= 2:
            return f"{parts[1]}/{parts[0]}"
        return parts[0] if parts else ""

    start_fmt = to_mmyyyy(start) if start else ""
    end_fmt = to_mmyyyy(end) if end else "Present"
    if start_fmt and end_fmt:
        return f"{start_fmt} – {end_fmt}"
    return start_fmt or end_fmt


def _convert_basics(basics: dict[str, Any]) -> dict[str, Any]:
    """Map `basics` → Euxis CV header (name, role, contact, summary)."""
    name = _split_name(basics.get("name", ""))
    role = basics.get("label") or basics.get("headline") or ""
    summary = basics.get("summary", "")

    contact: dict[str, Any] = {}
    if basics.get("phone"):
        contact["phone"] = basics["phone"]
    if basics.get("email"):
        contact["email"] = basics["email"]
    if basics.get("url"):
        contact["url"] = basics["url"]
    loc = _format_location(basics.get("location"))
    if loc:
        contact["location"] = loc
    if basics.get("profiles"):
        contact["profiles"] = basics["profiles"]

    out: dict[str, Any] = {"name": name, "role": role, "contact": contact}
    if summary:
        # Heuristic: short summary → `summary`; longer reads like an
        # executive profile.
        key = "executive_profile" if len(summary) > 200 else "summary"
        out[key] = summary
    return out


def _convert_work(work: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Map `work[]` → Euxis `experience[]`."""
    if not work:
        return []
    out = []
    for w in work:
        item: dict[str, Any] = {
            "company": w.get("name") or w.get("company", ""),
            "title": w.get("position", ""),
            "location": w.get("location", ""),
            "dates": _format_date_range(w.get("startDate"), w.get("endDate")),
            "bullets": list(w.get("highlights") or []),
        }
        if w.get("summary"):
            item["context"] = w["summary"]
        if w.get("url"):
            item["url"] = w["url"]
        out.append(item)
    return out


def _convert_volunteer(volunteer: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """JSON Resume's `volunteer[]` overlaps semantically with `work[]`;
    fold into `experience[]` with a `volunteer: true` marker."""
    if not volunteer:
        return []
    out = []
    for v in volunteer:
        item: dict[str, Any] = {
            "company": v.get("organization", ""),
            "title": v.get("position", ""),
            "location": v.get("location", ""),
            "dates": _format_date_range(v.get("startDate"), v.get("endDate")),
            "bullets": list(v.get("highlights") or []),
            "volunteer": True,
        }
        if v.get("summary"):
            item["context"] = v["summary"]
        out.append(item)
    return out


def _convert_education(education: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not education:
        return []
    out = []
    for e in education:
        degree_bits = [
            e.get("studyType"),
            e.get("area"),
        ]
        degree = " ".join(b for b in degree_bits if b).strip()
        out.append(
            {
                "institution": e.get("institution", ""),
                "degree": degree or e.get("studyType", ""),
                "location": e.get("location", ""),
                "year": _format_date_range(e.get("startDate"), e.get("endDate")),
                **({"gpa": e["score"]} if e.get("score") else {}),
            }
        )
    return out


def _convert_skills(skills: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Map `skills[]` → Euxis `competencies[]` (title + description)."""
    if not skills:
        return []
    out = []
    for s in skills:
        title = s.get("name", "")
        keywords = s.get("keywords") or []
        out.append(
            {
                "title": title,
                "description": ", ".join(keywords) if keywords else (s.get("level") or ""),
            }
        )
    return out


def _convert_languages(languages: list[dict[str, Any]] | None) -> str:
    """Comma-join `languages[]` into a single string for the template."""
    if not languages:
        return ""
    bits = []
    for lang in languages:
        name = lang.get("language", "")
        level = lang.get("fluency", "")
        bits.append(f"{name} ({level})" if name and level else name or level)
    return ", ".join(b for b in bits if b)


def _convert_awards_and_publications(
    awards: list[dict[str, Any]] | None,
    publications: list[dict[str, Any]] | None,
) -> list[str]:
    """Awards + Publications both fold into Euxis' `innovation[]` list."""
    out: list[str] = []
    for a in awards or []:
        line = " — ".join(
            b for b in (a.get("title"), a.get("awarder"), (a.get("date") or "").split("-")[0]) if b
        )
        if a.get("summary"):
            line = f"{line}: {a['summary']}" if line else a["summary"]
        if line:
            out.append(line)
    for p in publications or []:
        line = " — ".join(
            b
            for b in (
                p.get("name"),
                p.get("publisher"),
                (p.get("releaseDate") or "").split("-")[0],
            )
            if b
        )
        if p.get("url"):
            line = f"{line} ({p['url']})" if line else p["url"]
        if line:
            out.append(line)
    return out


# ── Public API ─────────────────────────────────────────────────────────


def convert(resume: dict[str, Any]) -> dict[str, Any]:
    """Convert a parsed JSON Resume dict into the Euxis CV YAML schema.

    Args:
        resume: a dict matching the JSON Resume v1 schema.

    Returns:
        A dict ready to dump as YAML and feed `templates/cv.tex.j2`.
    """
    basics = resume.get("basics") or {}
    out: dict[str, Any] = _convert_basics(basics)

    experience = _convert_work(resume.get("work")) + _convert_volunteer(resume.get("volunteer"))
    if experience:
        out["experience"] = experience

    education = _convert_education(resume.get("education"))
    if education:
        out["education"] = education

    competencies = _convert_skills(resume.get("skills"))
    if competencies:
        out["competencies"] = competencies

    languages = _convert_languages(resume.get("languages"))
    if languages:
        out["languages"] = languages

    innovation = _convert_awards_and_publications(resume.get("awards"), resume.get("publications"))
    if innovation:
        out["innovation"] = innovation

    # Pass-through anything we didn't claim so authors can hand-edit.
    known = {
        "basics",
        "work",
        "volunteer",
        "education",
        "skills",
        "languages",
        "awards",
        "publications",
        "projects",
        "interests",
        "references",
        "meta",
    }
    extras = {k: v for k, v in resume.items() if k not in known}
    if resume.get("projects"):
        # Surface projects as a sibling block (template can pick it up).
        out["projects"] = resume["projects"]
    if extras:
        out["_jsonresume_extras"] = extras
    return out


def load_json_resume(path: Path) -> dict[str, Any]:
    """Read + parse a JSON Resume document.

    Raises:
        FileNotFoundError: when *path* is missing.
        ValueError: when the file isn't valid JSON.
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON Resume not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def dump_yaml(data: dict[str, Any], path: Path) -> None:
    """Write *data* to *path* as readable YAML (block style, no aliases)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


# ── CLI entry point ────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="euxis-publisher import",
        description=(
            "Convert a JSON Resume document (jsonresume.org) into the Euxis CV YAML schema."
        ),
    )
    parser.add_argument("input", help="Path to the JSON Resume file (.json).")
    parser.add_argument(
        "--output",
        "-o",
        default="-",
        help="Output YAML path. `-` writes to stdout (default).",
    )
    args = parser.parse_args(argv)

    src = Path(args.input)
    try:
        resume = load_json_resume(src)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    converted = convert(resume)

    if args.output == "-":
        print(yaml.safe_dump(converted, sort_keys=False, allow_unicode=True))
    else:
        dump_yaml(converted, Path(args.output))
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
