"""Multi-format emitters for the Inclusio engine.

Sprint 6 (S6.2, S6.3, S6.6) — closes Forcing Function #3
(single-source multi-format) in docs/strategy-2026.md.

The emitters convert built LaTeX documents into HTML5, JATS XML, and
EPUB-A through Pandoc. They share a thin adapter (`pandoc.py`) that
manages subprocess invocation, ARIA / accessibility post-processing,
and registry-aware output paths.

A registered document's emission goes to:
    build/<type>/<doc_id>.html         # S6.3
    build/<type>/<doc_id>.xml          # S6.2  (JATS 1.3)
    build/<type>/<doc_id>.epub         # S6.6
"""

from __future__ import annotations
