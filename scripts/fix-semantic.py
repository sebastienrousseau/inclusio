#!/usr/bin/env python3
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""
fix-semantic.py — Auto-fix semantic violations in LaTeX source files.

Replaces forbidden raw formatting commands with their semantic equivalents
as defined in data/meta.yaml quality.forbidden_commands.

Usage:
    python scripts/fix-semantic.py src/
    python scripts/fix-semantic.py src/ --dry-run
    python scripts/fix-semantic.py src/ --verbose
"""

import argparse
import re
import sys
from pathlib import Path


# ── Replacement rules ─────────────────────────────────────────────────────
# Each rule: (compiled regex, replacement string or callable, description)

def _brace_pattern(cmd):
    r"""Build a regex matching \cmd{...} with balanced braces (one level)."""
    # Matches \cmd{content} where content may contain nested {…} one level deep
    escaped = re.escape(cmd)
    return re.compile(
        escaped + r'\{((?:[^{}]|\{[^{}]*\})*)\}'
    )


RULES = [
    # \textbf{...} → \keyterm{...}
    (_brace_pattern(r'\textbf'), r'\\keyterm{\1}', r'\textbf → \keyterm'),
    # \textit{...} → \emph{...}
    (_brace_pattern(r'\textit'), r'\\emph{\1}', r'\textit → \emph'),
    # \vspace{...} → removed (whole match deleted)
    (_brace_pattern(r'\vspace'), '', r'\vspace → removed'),
    # \hspace{...} → removed
    (_brace_pattern(r'\hspace'), '', r'\hspace → removed'),
    # \fontsize{...}{...} → removed (two brace groups)
    (re.compile(r'\\fontsize\{[^}]*\}\{[^}]*\}'), '', r'\fontsize → removed'),
    # \color{...}{...} → keep content, remove wrapper
    (re.compile(r'\\color\{[^}]*\}\{((?:[^{}]|\{[^{}]*\})*)\}'), r'\1',
     r'\color{..}{..} → content'),
    # \centering → removed
    (re.compile(r'\\centering\b'), '', r'\centering → removed'),
]


def fix_line(line):
    """Apply all replacement rules to a single line. Return (new_line, count)."""
    total = 0
    for pattern, replacement, _desc in RULES:
        line, n = pattern.subn(replacement, line)
        total += n
    return line, total


def fix_file(path, dry_run=False, verbose=False):
    """Fix semantic violations in a single file.

    Returns the number of replacements made.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    new_lines = []
    file_total = 0

    for lineno, line in enumerate(lines, 1):
        new_line, count = fix_line(line)
        if count > 0:
            file_total += count
            # Strip lines that became empty/whitespace-only after removal
            stripped = new_line.strip()
            if stripped == "" and line.strip() != "":
                # Line was non-empty before, now empty — skip it
                if verbose:
                    print(f"  {path}:{lineno}: removed empty line")
                continue
            if verbose:
                print(f"  {path}:{lineno}: {line.rstrip()}")
                print(f"       → {new_line.rstrip()}")
        new_lines.append(new_line)

    if file_total > 0 and not dry_run:
        path.write_text("\n".join(new_lines), encoding="utf-8")

    return file_total


def main():
    parser = argparse.ArgumentParser(
        description="Auto-fix semantic violations in LaTeX source files"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Directory or file to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show each replacement line-by-line",
    )
    args = parser.parse_args()

    target = args.path
    if not target.exists():
        print(f"ERROR: {target} not found", file=sys.stderr)
        sys.exit(1)

    if target.is_file():
        files = [target]
    else:
        files = sorted(target.rglob("*.tex"))

    if not files:
        print("No .tex files found")
        sys.exit(0)

    total_replacements = 0
    files_modified = 0

    for f in files:
        count = fix_file(f, dry_run=args.dry_run, verbose=args.verbose)
        if count > 0:
            files_modified += 1
            total_replacements += count
            action = "would fix" if args.dry_run else "fixed"
            print(f"  {action} {count} violation(s) in {f}")

    mode = " (dry run)" if args.dry_run else ""
    print(f"\n{total_replacements} violation(s) in {files_modified} file(s){mode}")

    # Exit code = number of files modified (0 = nothing to do)
    sys.exit(files_modified)


if __name__ == "__main__":  # pragma: no cover
    main()
