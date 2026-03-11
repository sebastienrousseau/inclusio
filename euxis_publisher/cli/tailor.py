#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
tailor.py — Tailored document generation from briefs.

Reads job descriptions or briefs in any format (.txt, .md, .rtf, .doc, .docx),
then generates tailored YAML data files to render through the existing
Jinja2 → LaTeX pipeline.

Primary path: Claude CLI (claude -p) for intelligent rewriting.
Fallback: keyword-based theme extraction + template composition.

Usage:
    python -m euxis_publisher.cli.tailor data/jobs/revolut-pm.txt
    python -m euxis_publisher.cli.tailor data/jobs/brief.docx --type cv --id my-cv
    python -m euxis_publisher.cli.tailor data/jobs/brief.md --no-ai
"""

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

# ── Paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_SUBPROCESS_TIMEOUT = int(
    os.environ.get("EUXIS_SUBPROCESS_TIMEOUT", "300")
)

# CONTENT_ROOT: where content lives (data/, src/).
# Defaults to PROJECT_ROOT; overridden by EUXIS_CONTENT_DIR env var.
_env_content = os.environ.get("EUXIS_CONTENT_DIR")
CONTENT_ROOT = Path(_env_content).resolve() if _env_content else PROJECT_ROOT

STOPWORDS_FILE = CONTENT_ROOT / "data" / "stopwords.txt"
TAILORED_DIR = CONTENT_ROOT / "data" / "tailored"


# ── Theme map for domain-aware matching ──────────────────────────────────
THEME_MAP = {
    "ai_ml": {
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "llm", "generative ai", "neural", "nlp", "model training",
            "data science", "computer vision", "genai", "vertex",
        ],
        "label": "technology-driven product innovation and AI/ML solutions",
    },
    "cloud": {
        "keywords": [
            "cloud", "aws", "gcp", "google cloud", "azure", "saas", "paas",
            "infrastructure", "platform", "kubernetes", "devops",
        ],
        "label": "cloud platforms and scalable infrastructure",
    },
    "product": {
        "keywords": [
            "product manager", "product management", "roadmap",
            "product strategy", "product development", "product lifecycle",
            "conception to launch", "ideation", "execution",
        ],
        "label": "product strategy and lifecycle management",
    },
    "gtm": {
        "keywords": [
            "go-to-market", "gtm", "market strategy", "launch",
            "commercialization", "market adoption", "outbound",
            "positioning", "market size", "market insights",
        ],
        "label": "go-to-market strategy and product commercialization",
    },
    "engineering": {
        "keywords": [
            "engineering", "software development", "technical",
            "architecture", "api", "sdk", "system design",
            "technical products", "development",
        ],
        "label": "technical product development and API-driven solutions",
    },
    "payments": {
        "keywords": [
            "payment", "banking", "fintech", "transaction", "sepa", "psd2",
            "open banking", "financial", "merchant",
        ],
        "label": "payment solutions and financial technology",
    },
    "leadership": {
        "keywords": [
            "leadership", "cross-functional", "stakeholder", "executive",
            "team management", "collaboration", "partnership", "influence",
            "cross-functionally",
        ],
        "label": "cross-functional leadership and executive stakeholder management",
    },
    "customer": {
        "keywords": [
            "customer", "client", "partner", "enterprise", "user",
            "feedback", "engagement", "user insights",
        ],
        "label": "customer engagement and partner ecosystem development",
    },
}


def _extract_yaml(text):
    """Extract YAML content from Claude CLI output.

    Handles responses that include markdown fences, leading prose,
    or trailing commentary around the actual YAML.
    """
    text = text.strip()

    # 1. Try extracting from markdown fences first
    fenced = re.search(r"```ya?ml\s*\n(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    # 2. Find where valid YAML starts (first line that looks like a YAML key)
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"^[a-z_][a-z0-9_]*\s*:", line):
            start = i
            break

    # 3. Find where YAML ends (stop at prose/commentary)
    end = len(lines)
    for i in range(start, len(lines)):
        if re.match(r"^\s*(\*\*|Key changes|Rationale|Note:|Here |I |This )",
                    lines[i]):
            end = i
            break

    return "\n".join(lines[start:end]).strip()


def _load_stopwords():
    """Load stop words from data/stopwords.txt."""
    if not STOPWORDS_FILE.exists():
        return set()
    return {
        w.strip().lower()
        for w in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines()
        if w.strip() and not w.strip().startswith("#")
    }


def check_tool(name):
    """Check if a tool is available on PATH."""
    return shutil.which(name) is not None


def read_brief(path):
    """Read a brief/job description from any supported format to plain text.

    Supports .txt/.md/.markdown natively.
    Uses pandoc for .rtf, .doc, .docx, .odt, .html, and other formats.
    """
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Brief file not found: {path}", file=sys.stderr)
        sys.exit(1)
    ext = path.suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return path.read_text(encoding="utf-8")
    # All other formats → pandoc
    if not check_tool("pandoc"):
        print(f"ERROR: pandoc required for {ext} files", file=sys.stderr)
        sys.exit(1)
    result = subprocess.run(
        ["pandoc", str(path), "-t", "plain", "--wrap=none"],
        capture_output=True,
        text=True,
        check=True,
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )
    return result.stdout


def extract_keywords(text, top_n=50):
    """Extract keywords from brief text using frequency analysis.

    Returns a set of lowercase keywords, filtered against common stop words.
    Includes both single words and bigrams for domain terms.
    """
    if not text or not text.strip():
        return set()
    stopwords = _load_stopwords()
    # Tokenize: lowercase, keep only alphanumeric and hyphens
    words = re.findall(r"[a-z][a-z0-9\-]*", text.lower())
    # Filter stop words and very short words
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    # Single-word frequency
    freq = Counter(filtered)
    # Bigrams for multi-word terms
    for i in range(len(filtered) - 1):
        bigram = f"{filtered[i]} {filtered[i + 1]}"
        freq[bigram] += 1
    # Return top N by frequency
    return {term for term, _ in freq.most_common(top_n)}


def score_section(text, keywords):
    """Score how relevant a text snippet is to extracted keywords. 0.0-1.0."""
    if not keywords:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return hits / len(keywords)


# ── Theme-based analysis ─────────────────────────────────────────────────


def extract_themes(text):
    """Extract domain themes from text with relevance scores.

    Returns dict of {theme_name: score} sorted by score descending.
    """
    text_lower = text.lower()
    scores = {}
    for theme, info in THEME_MAP.items():
        hits = sum(1 for kw in info["keywords"] if kw in text_lower)
        if hits > 0:
            scores[theme] = hits / len(info["keywords"])
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def _compose_summary(brief_text, keywords, base_data):
    """Compose a tailored summary from existing CV data.

    Identifies matching themes from the brief and constructs a summary
    that emphasises transferable experience using grounded, British
    professional language.
    """
    themes = extract_themes(brief_text)
    if not themes:
        return base_data.get("summary", "")

    # Core role (before comma), avoid "Senior Senior ..."
    role = base_data.get("role", "Product Manager")
    core_role = role.split(",")[0].strip()
    if core_role.lower().startswith("senior"):
        role_prefix = core_role
    else:
        role_prefix = f"Senior {core_role}"

    # Companies
    companies = [e["company"] for e in base_data.get("experience", [])[:3]]
    if len(companies) >= 2:
        company_str = ", ".join(companies[:-1]) + f" and {companies[-1]}"
    elif companies:
        company_str = companies[0]
    else:
        company_str = ""

    # Top matching theme labels
    top_themes = list(themes.keys())[:3]
    theme_labels = [THEME_MAP[t]["label"] for t in top_themes]
    if len(theme_labels) >= 2:
        theme_str = ", ".join(theme_labels[:-1]) + " and " + theme_labels[-1]
    else:
        theme_str = theme_labels[0]

    # Find most relevant bullet for a concrete achievement
    all_scored = []
    for exp in base_data.get("experience", []):
        for bullet in exp.get("bullets", []):
            s = score_section(bullet, keywords)
            all_scored.append((s, bullet))
    all_scored.sort(reverse=True)

    # Build summary — vary sentence length for natural rhythm
    parts = [
        f"{role_prefix} with 20+ years of experience delivering "
        f"{theme_str} at {company_str}.",
    ]

    # Add a concrete highlight from the top-scoring bullet
    if all_scored and all_scored[0][0] > 0.02:
        bullet = all_scored[0][1]
        bullet = bullet.replace("\\$", "$").replace("\\&", "&")
        lead = bullet[0].lower() + bullet[1:] if bullet[0].isupper() else bullet
        highlight = f"Track record includes {lead}"
        if not highlight.endswith("."):
            highlight += "."
        parts.append(highlight)

    # Add matching skills emphasis — short closing sentence
    top_skills = []
    for skill in base_data.get("skills", []):
        combined = f"{skill.get('title', '')} {skill.get('description', '')}"
        if score_section(combined, keywords) > 0.01:
            top_skills.append(skill["title"])
    if top_skills:
        parts.append(f"Core strengths in {' and '.join(top_skills[:2])}.")

    return " ".join(parts)


def _adjust_role(brief_text, base_role):
    """Adjust role title to better match the target position.

    Extracts the role from the brief and blends it with the candidate's
    domain expertise. Returns the original role if no match is found.
    """
    patterns = [
        r"((?:Senior|Lead|Staff|Principal|Head of|Chief)\s+"
        r"(?:Outbound\s+)?(?:\w+\s+)*?"
        r"(?:Manager|Engineer|Architect|Director|Officer))",
        r"(Outbound\s+Product\s+Manager)",
        r"(Product\s+Manager)",
    ]
    for pattern in patterns:
        match = re.search(pattern, brief_text, re.IGNORECASE)
        if match:
            target_role = match.group(1)
            # Blend: use target role title + candidate's domain expertise
            if "," in base_role:
                base_domain = base_role.split(",", 1)[1].strip()
                return f"{target_role}, {base_domain}"
            return target_role
    return base_role


def _filter_bullets(bullets, keywords, max_count=5):
    """Filter and reorder bullets by relevance, keeping top N.

    Ensures at least min(len(bullets), max_count) bullets are returned.
    """
    scored = [(score_section(b, keywords), b) for b in bullets]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [b for _, b in scored[:max_count]]


# ── Consistency gate ─────────────────────────────────────────────────────

# Words and patterns that signal AI-generated or non-British text
BANNED_PHRASES = [
    "delve into", "leveraging", "leverage", "seamlessly", "robust",
    "proven track record", "passionate about", "cutting-edge",
    "best-in-class", "synergy", "holistic", "ecosystem", "paradigm",
    "innovative", "thought leader", "disruptive", "spearheaded",
    "game-changing", "world-class", "utilize",
]

# American -ize spellings that should be -ise in British English
AMERICAN_IZE_PATTERN = re.compile(
    r"\b(\w*(?:optimi|organi|speciali|recogni|summari|prioriti|standardi|"
    r"centrali|digiti|commerciali|moderni|customi|finali|categori|"
    r"stabili|minimi|maximi|harmoni|authori|visuali|empathi|reali|"
    r"rationali|capitali|revitali|mobili|normali|legali|generali|"
    r"professionali|neutrali|signali|initiali|formali|locali|seriali|"
    r"memori|factori|naturali|liberali|utili))ze"
    r"(s|d|r|rs)?\b",
    re.IGNORECASE,
)


def lint_cv_data(data):
    """Post-generation consistency gate for CV data quality.

    Scans all string values in the tailored data for:
    1. Banned AI-centric phrases
    2. American -ize spellings (should be -ise)
    3. Vague achievement bullets lacking measurable outcomes

    Returns a list of warning dicts: {field, issue, value}.
    """
    warnings = []

    def _scan_string(field, text):
        text_lower = text.lower()
        # Check banned phrases
        for phrase in BANNED_PHRASES:
            if phrase in text_lower:
                warnings.append({
                    "field": field,
                    "issue": f"banned phrase: '{phrase}'",
                    "value": text[:80],
                })
        # Check -ize spellings
        for match in AMERICAN_IZE_PATTERN.finditer(text):
            warnings.append({
                "field": field,
                "issue": f"American spelling: '{match.group()}' → "
                         f"'{match.group().replace('ize', 'ise').replace('ized', 'ised').replace('izer', 'iser').replace('izes', 'ises')}'",
                "value": text[:80],
            })

    # Scan summary
    if "summary" in data and isinstance(data["summary"], str):
        _scan_string("summary", data["summary"])

    # Scan experience bullets
    for i, exp in enumerate(data.get("experience", [])):
        for j, bullet in enumerate(exp.get("bullets", [])):
            _scan_string(f"experience[{i}].bullets[{j}]", bullet)

    # Scan skill descriptions
    for i, skill in enumerate(data.get("skills", [])):
        desc = skill.get("description", "")
        if desc:
            _scan_string(f"skills[{i}].description", desc)

    # Achievement verification: flag vague bullets with no numbers
    for i, exp in enumerate(data.get("experience", [])):
        for j, bullet in enumerate(exp.get("bullets", [])):
            has_metric = bool(re.search(
                r"\d+[%+]?|\$[\d,.]+|£[\d,.]+|€[\d,.]+", bullet
            ))
            has_impact_verb = bool(re.search(
                r"\b(delivered|led|built|designed|orchestrated|streamlined|"
                r"shaped|established|drove|secured|introduced|expanded|"
                r"negotiated|coordinated|defined|reduced|increased|"
                r"achieved|saved|generated|grew|launched|managed)\b",
                bullet, re.IGNORECASE,
            ))
            if not has_metric and not has_impact_verb:
                warnings.append({
                    "field": f"experience[{i}].bullets[{j}]",
                    "issue": "vague: no metric or impact verb found",
                    "value": bullet[:80],
                })

    return warnings


# ── Tailoring engines ────────────────────────────────────────────────────


def tailor_cv(brief_text, base_data):
    """Keyword-based CV tailoring (fallback when Claude CLI unavailable).

    - Composes a tailored summary emphasizing relevant experience
    - Adjusts role title to match target position
    - Filters and reorders experience bullets by relevance (max 5 per role)
    - Reorders skills by relevance
    - Preserves name, contact, education, languages unchanged
    """
    data = copy.deepcopy(base_data)
    keywords = extract_keywords(brief_text)

    # 1. Compose tailored summary
    data["summary"] = _compose_summary(brief_text, keywords, base_data)

    # 2. Adjust role title
    data["role"] = _adjust_role(brief_text, base_data.get("role", ""))

    # 3. Filter and reorder experience bullets
    for exp in data.get("experience", []):
        bullets = exp.get("bullets", [])
        exp["bullets"] = _filter_bullets(bullets, keywords)

    # 4. Reorder skills by relevance
    skills = data.get("skills", [])
    data["skills"] = sorted(
        skills,
        key=lambda s: score_section(
            f"{s.get('title', '')} {s.get('description', '')}", keywords
        ),
        reverse=True,
    )

    return data


def claude_generate(brief_text, doc_type, base_data):
    """Generate tailored content via the Claude CLI (claude -p).

    Uses the locally installed Claude Code CLI — no separate API keys
    or endpoint configuration needed. Falls back to None if the CLI
    is unavailable or the call fails.
    """
    if not check_tool("claude"):
        return None

    base_yaml = yaml.dump(
        base_data, default_flow_style=False,
        allow_unicode=True, sort_keys=False,
    )

    prompt = (
        "You are a specialist British career consultant with 20 years' "
        "experience placing senior professionals in the UK market. Tailor "
        "this CV data for a British audience.\n\n"
        "BRITISH ENGLISH — MANDATORY:\n"
        "- Use -ise spellings throughout (optimise, organise, specialise, "
        "recognise, summarise, prioritise, standardise, centralise).\n"
        "- Use British vocabulary: 'programme' (not program), 'colour' "
        "(not color), 'centre' (not center), 'defence' (not defense), "
        "'licence' (noun) / 'license' (verb), 'labour' (not labor).\n"
        "- Use 'CV' (not Resume/Résumé), 'Mobile' (not Cell), 'Postal "
        "Code' (not Zip Code), 'Notice Period' (not notice).\n"
        "- Use British date formats and conventions where relevant.\n\n"
        "TONE AND VOICE:\n"
        "- Write in a direct, grounded, and quietly confident professional "
        "tone. Avoid corporate hyperbole ('visionary leader,' 'passionate "
        "disruptor,' 'world-class') — replace with evidence-based impact.\n"
        "- BANNED WORDS AND PHRASES (never use these): 'delve into,' "
        "'leveraging,' 'leverage,' 'seamlessly,' 'robust,' 'proven track "
        "record,' 'passionate about,' 'cutting-edge,' 'best-in-class,' "
        "'synergy,' 'holistic,' 'ecosystem,' 'paradigm,' 'innovative,' "
        "'thought leader,' 'disruptive.'\n"
        "- Use high-impact active verbs a senior British professional "
        "would use: 'delivered,' 'led,' 'built,' 'designed,' "
        "'orchestrated,' 'streamlined,' 'shaped,' 'established,' "
        "'drove,' 'secured,' 'introduced,' 'expanded,' 'negotiated,' "
        "'coordinated,' 'defined.'\n"
        "- Vary sentence rhythm: mix short, punchy achievement statements "
        "(8-12 words) with slightly more descriptive ones (15-25 words) "
        "to create a natural reading flow. Avoid monotone bullet points.\n\n"
        "ACHIEVEMENTS:\n"
        "- Structure as 'Accomplished X as measured by Y by doing Z.'\n"
        "- Focus on business value delivered to UK/European stakeholders.\n"
        "- Quantify where possible using the original data (revenue, "
        "users, countries, percentage improvements).\n\n"
        "TAILORING RULES:\n"
        "1. NEVER fabricate experience, companies, dates, or achievements.\n"
        "2. NEVER invent new roles, skills, or qualifications.\n"
        "3. Rewrite the summary to bridge my background with the target "
        "role, emphasising transferable skills and relevant experience.\n"
        "4. Rephrase experience bullets to highlight aspects relevant to "
        "the role — show how my actual work maps to what they need.\n"
        "5. Reorder bullets within each role (most relevant first).\n"
        "6. Keep max 5 bullets per role, drop least relevant ones.\n"
        "7. Reorder skills by relevance to the role.\n"
        "8. Adjust skill descriptions to emphasise transferable capabilities.\n"
        "9. Adjust the role/title field to better match the target position "
        "while keeping it truthful to my actual background.\n"
        "10. Keep name, contact, footer_address, education, languages, "
        "prior_experience, logos, and dates EXACTLY as they are.\n"
        "11. Keep LaTeX escapes (e.g. \\$, \\&) intact.\n\n"
        "OUTPUT FORMAT: Return ONLY the YAML. No markdown fences. "
        "No explanations. No commentary before or after. "
        "Start directly with the first YAML key.\n\n"
        f"JOB DESCRIPTION:\n{brief_text}\n\n"
        f"MY CURRENT CV DATA (YAML):\n{base_yaml}"
    )

    try:
        # Unset CLAUDECODE to allow nested invocation from within
        # a Claude Code session (same pattern as euxis).
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
            env=env,
        )
        if result.returncode != 0:
            print(
                f"WARN: claude CLI returned {result.returncode}, "
                "falling back to keywords",
                file=sys.stderr,
            )
            return None

        content = _extract_yaml(result.stdout)
        return yaml.safe_load(content)

    except subprocess.TimeoutExpired:
        print(
            "WARN: claude CLI timed out, falling back to keywords",
            file=sys.stderr,
        )
        return None
    except Exception as exc:
        print(
            f"WARN: claude CLI failed ({exc}), falling back to keywords",
            file=sys.stderr,
        )
        return None


def generate(brief_path, doc_type="cv", output_id=None, base_path=None,
             use_ai=True):
    """Read brief, tailor data, write YAML, return output path.

    1. Read brief from any format
    2. Try Claude CLI (unless --no-ai); if unavailable, use keyword fallback
    3. Load base data (data/{doc_type}-data.yaml)
    4. Generate tailored YAML -> data/tailored/{output_id}.yaml
    5. Return path to generated YAML
    """
    brief_path = Path(brief_path)
    if output_id is None:
        output_id = brief_path.stem

    # Read brief
    brief_text = read_brief(brief_path)

    # Load base data
    if base_path:
        data_file = Path(base_path)
    else:
        data_file = CONTENT_ROOT / "data" / f"{doc_type}-data.yaml"
    if not data_file.exists():
        print(f"ERROR: Base data file not found: {data_file}", file=sys.stderr)
        sys.exit(1)
    with open(data_file) as f:
        base_data = yaml.safe_load(f)

    # Try Claude CLI first (default)
    tailored = None
    if use_ai:
        tailored = claude_generate(brief_text, doc_type, base_data)

    # Fall back to keyword-based tailoring
    if tailored is None:
        if doc_type == "cv":
            tailored = tailor_cv(brief_text, base_data)
        else:
            tailored = copy.deepcopy(base_data)

    # Consistency gate — lint before saving
    if doc_type == "cv":
        lint_warnings = lint_cv_data(tailored)
        if lint_warnings:
            print(f"  LINT {len(lint_warnings)} warning(s):", file=sys.stderr)
            for w in lint_warnings:
                print(f"    [{w['field']}] {w['issue']}", file=sys.stderr)

    # Write output
    TAILORED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TAILORED_DIR / f"{output_id}.yaml"
    with open(out_path, "w") as f:
        yaml.dump(tailored, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False)

    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate tailored documents from briefs/job descriptions"
    )
    parser.add_argument(
        "brief", type=Path, help="Path to brief/job description file"
    )
    parser.add_argument(
        "--type",
        default="cv",
        choices=["cv", "paper", "patent", "faq", "guide"],
        help="Document type (default: cv)",
    )
    parser.add_argument(
        "--id", help="Output document ID (default: derived from brief filename)"
    )
    parser.add_argument(
        "--base",
        type=Path,
        help="Base data file (default: data/{type}-data.yaml)",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip Claude CLI, use keyword-based tailoring only",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Also render to LaTeX after generating",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Also compile to PDF after rendering",
    )
    args = parser.parse_args(argv)

    output_id = args.id or args.brief.stem
    use_ai = not args.no_ai
    yaml_path = generate(args.brief, args.type, output_id, args.base, use_ai)
    print(f"  TAILOR {output_id} -> {yaml_path}")

    if args.render or args.build:
        try:
            try:
                render_module = __import__("render")
            except ModuleNotFoundError:
                from euxis_publisher.cli import render as render_module

            render_module.render_document(output_id, fmt="latex",
                                          build_mode="draft")
        except ImportError:
            print("ERROR: Jinja2 not installed. Run: pip install jinja2",
                  file=sys.stderr)
            sys.exit(1)

    if args.build:
        try:
            try:
                build_module = __import__("build")
            except ModuleNotFoundError:
                from euxis_publisher.cli import build as build_module

            meta = build_module.load_meta()
            doc_config = {
                "class": f"pub-{args.type}",
                "src": f"build/rendered/{output_id}.tex",
                "title": output_id,
                "version": "1.0",
                "description": f"Tailored {args.type}",
            }
            build_module.build_document(output_id, doc_config, "draft", meta)
        except ImportError:
            print("ERROR: Build module not available", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
