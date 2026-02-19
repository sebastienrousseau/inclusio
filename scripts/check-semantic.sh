#!/usr/bin/env bash
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
#
# check-semantic.sh — Enforce semantic macros in src/ files.
# Raw formatting commands like \textbf, \vspace, \fontsize etc. are forbidden
# in content files. All formatting must come from core/ classes and packages.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTENT_ROOT="${EUXIS_CONTENT_DIR:-$ENGINE_ROOT}"
SRC_DIR="$CONTENT_ROOT/src"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Forbidden raw formatting commands in src/ content files.
# These should be replaced with semantic equivalents:
#   \textbf{...}  → \keyterm{...}
#   \texttt{...}  → \code{...}
#   \vspace{...}  → (remove or use class-level spacing)
#   \hspace{...}  → (remove or use class-level spacing)
#   \fontsize     → (handled by class)
#   \color{...}   → (handled by class)
#   \centering    → (handled by class)
FORBIDDEN_PATTERN='\\textbf\|\\vspace\|\\hspace\|\\fontsize\|\\color{[^}]*}'

if [ ! -d "$SRC_DIR" ]; then
    echo -e "${RED}ERROR: $SRC_DIR not found${NC}"
    exit 1
fi

violations=$(grep -rn "$FORBIDDEN_PATTERN" "$SRC_DIR" --include='*.tex' 2>/dev/null || true)

if [ -n "$violations" ]; then
    echo -e "${RED}FAIL: Raw formatting commands found in src/${NC}"
    echo ""
    echo "$violations" | head -50
    count=$(echo "$violations" | wc -l | xargs)
    echo ""
    echo -e "${RED}Total violations: $count${NC}"
    echo ""
    echo "Replace with semantic macros:"
    echo "  \\textbf{...}  → \\keyterm{...}"
    echo "  \\texttt{...}  → \\code{...}"
    echo "  \\vspace{...}  → (remove — handled by class)"
    echo "  \\hspace{...}  → (remove — handled by class)"
    echo "  \\fontsize     → (remove — handled by class)"
    echo "  \\color{...}   → (remove — handled by class)"
    exit 1
else
    echo -e "${GREEN}OK: No raw formatting commands in src/${NC}"
    exit 0
fi
