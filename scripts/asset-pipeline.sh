#!/usr/bin/env bash
# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
#
# asset-pipeline.sh — Vector-first asset pipeline: .mmd → .svg → .pdf + .png
# Supports theme-aware output (light/dark) and ICC profile embedding.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTENT_ROOT="${EUXIS_CONTENT_DIR:-$ENGINE_ROOT}"
ASSETS_DIR="$CONTENT_ROOT/assets"

# Configurable options (overridable via environment)
DIAGRAM_WIDTH="${DIAGRAM_WIDTH:-2048}"
MERMAID_BG="${MERMAID_BG:-white}"
MERMAID_DARK_BG="${MERMAID_DARK_BG:-#1e1e2e}"
MERMAID_DARK_THEME="${MERMAID_DARK_THEME:-dark}"
ENABLE_DARK="${ENABLE_DARK:-true}"
ENABLE_ICC="${ENABLE_ICC:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[asset-pipeline]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[asset-pipeline]${NC} $*"; }
log_error() { echo -e "${RED}[asset-pipeline]${NC} $*" >&2; }

# ── Tool detection ───────────────────────────────────────────────────────
check_tool() {
    if ! command -v "$1" &>/dev/null; then
        log_error "Required tool '$1' not found. Install it first."
        return 1
    fi
}

check_tools() {
    local missing=0
    for tool in mmdc rsvg-convert; do
        if ! check_tool "$tool"; then
            missing=1
        fi
    done
    if [ "$missing" -eq 1 ]; then
        log_error "Install missing tools: npm install -g @mermaid-js/mermaid-cli && brew install librsvg"
        exit 1
    fi
}

# ── ICC profile embedding via ghostscript ────────────────────────────────
# Embeds sRGB ICC profile into PDF for professional print compliance.
embed_icc_profile() {
    local pdf="$1"
    local name
    name="$(basename "$pdf")"

    if [ "$ENABLE_ICC" != "true" ]; then
        return 0
    fi

    if ! command -v gs &>/dev/null; then
        log_warn "  ghostscript not found — skipping ICC embed for $name"
        return 0
    fi

    local tmp_pdf="${pdf%.pdf}.icc.pdf"
    gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
       -dPDFSETTINGS=/prepress \
       -dColorConversionStrategy=/UseDeviceIndependentColor \
       -sOutputFile="$tmp_pdf" "$pdf" 2>/dev/null && {
        mv "$tmp_pdf" "$pdf"
    } || {
        rm -f "$tmp_pdf"
        log_warn "  ICC embed failed for $name (non-fatal)"
    }
}

# ── Convert a single .mmd file ──────────────────────────────────────────
convert_mmd() {
    local mmd="$1"
    local base="${mmd%.mmd}"
    local svg="${base}.svg"
    local pdf="${base}.pdf"
    local png="${base}.png"
    local name
    name="$(basename "$mmd")"

    # Skip if SVG is newer than MMD
    if [ -f "$svg" ] && [ "$svg" -nt "$mmd" ]; then
        log_info "  skip (up-to-date): $name"
        return 0
    fi

    log_info "  converting: $name"

    # ── Light theme (default / print) ────────────────────────────────────

    # Step 1: MMD → SVG (canonical vector source)
    mmdc -i "$mmd" -o "$svg" -b "$MERMAID_BG" --quiet 2>/dev/null || {
        log_error "  mmdc failed for $name"
        return 1
    }

    # Step 2: SVG → PDF (for LaTeX \includegraphics)
    rsvg-convert -f pdf -o "$pdf" "$svg" || {
        log_error "  rsvg-convert (PDF) failed for $name"
        return 1
    }

    # Step 2b: Embed ICC profile for print compliance
    embed_icc_profile "$pdf"

    # Step 3: SVG → PNG (for web/preview)
    rsvg-convert -f png -w "$DIAGRAM_WIDTH" -o "$png" "$svg" || {
        log_error "  rsvg-convert (PNG) failed for $name"
        return 1
    }

    log_info "  done: $name → .svg .pdf .png"

    # ── Dark theme (for web / dark-mode) ─────────────────────────────────

    if [ "$ENABLE_DARK" = "true" ]; then
        local dark_svg="${base}.dark.svg"
        local dark_png="${base}.dark.png"

        mmdc -i "$mmd" -o "$dark_svg" -b "$MERMAID_DARK_BG" \
             -t "$MERMAID_DARK_THEME" --quiet 2>/dev/null || {
            log_warn "  dark theme failed for $name (non-fatal)"
            return 0
        }

        rsvg-convert -f png -w "$DIAGRAM_WIDTH" -o "$dark_png" "$dark_svg" || {
            log_warn "  dark PNG failed for $name (non-fatal)"
            return 0
        }

        log_info "  done: $name → .dark.svg .dark.png"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────
main() {
    log_info "Starting asset pipeline..."
    log_info "  Themes: light=yes dark=$ENABLE_DARK  ICC=$ENABLE_ICC"
    check_tools

    local count=0
    local errors=0

    # Process all .mmd files under assets/
    while IFS= read -r -d '' mmd; do
        if convert_mmd "$mmd"; then
            count=$((count + 1))
        else
            errors=$((errors + 1))
        fi
    done < <(find "$ASSETS_DIR" -name '*.mmd' -print0 2>/dev/null)

    if [ "$count" -eq 0 ] && [ "$errors" -eq 0 ]; then
        log_warn "No .mmd files found in $ASSETS_DIR"
    else
        log_info "Processed $count diagrams ($errors errors)"
    fi

    return "$errors"
}

main "$@"
