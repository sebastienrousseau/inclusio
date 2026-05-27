# Copyright (c) 2026 Sebastien Rousseau
# Licensed under the MIT License
# See LICENSE file for details
"""FastMCP server exposing the Euxis Publisher engine over MCP.

Run with:
    euxis-mcp                       # stdio transport (Claude Code default)
    euxis-mcp --http                # Streamable HTTP on :8000
    euxis-mcp --http --port 9090    # custom port

Or from Python:
    python -m euxis_publisher.mcp.server

The server intentionally does NOT auto-rebuild documents — it exposes
the engine's read + audit surface so an MCP client can ask "list docs",
"audit this PDF", "render this template" and reason about the results
without surprise side effects. Write operations (`render`, `audit`)
return their result paths but never mutate `data/meta.yaml`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# FastMCP is an optional dependency — only required when the MCP server
# is actually run. Import lazily so `pip install euxis-publisher` works
# without it; clear error if a user runs `euxis-mcp` without installing
# the `mcp` extra.
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised by test_mcp_optional_import
    FastMCP = None  # type: ignore[assignment]

from euxis_publisher.cli import audit as audit_mod
from euxis_publisher.cli import build as build_mod
from euxis_publisher.cli import render as render_mod


def _content_root() -> Path:
    """Resolve the content root (EUXIS_CONTENT_DIR or the package root)."""
    env = os.environ.get("EUXIS_CONTENT_DIR")
    if env:
        return Path(env).resolve()
    return build_mod.CONTENT_ROOT


def _load_meta() -> dict[str, Any]:
    """Load the project manifest, returning {} when absent."""
    try:
        import yaml
    except ImportError:
        return {}
    meta_path = _content_root() / "data" / "meta.yaml"
    if not meta_path.exists():
        return {}
    return yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}


def create_server() -> Any:
    """Build the FastMCP app. Returns the app instance for run / inspect.

    Factored out so tests can import the configured server without
    running it, and so the CLI entry point can pick transport at run time.
    """
    if FastMCP is None:
        raise RuntimeError(
            "FastMCP is not installed. Install with: pip install 'euxis-publisher[mcp]'"
        )

    app = FastMCP(
        "euxis-publisher",
        instructions=(
            "Euxis Publisher MCP server — list, render, lint, and audit "
            "documents in a LaTeX-first publishing repository. Honours "
            "EUXIS_CONTENT_DIR. Use list_docs first to see what's available."
        ),
    )

    # ── Tools ───────────────────────────────────────────────────────────

    @app.tool()
    def list_docs() -> list[dict[str, Any]]:
        """List every document registered in data/meta.yaml.

        Returns one dict per document with id, class, src, title, and
        any `pdf_a` / `note` flags. Empty list when no manifest exists.
        """
        meta = _load_meta()
        out = []
        for doc_id, cfg in (meta.get("documents") or {}).items():
            if not isinstance(cfg, dict):
                cfg = {}
            out.append(
                {
                    "id": doc_id,
                    "class": cfg.get("class", ""),
                    "src": cfg.get("src", ""),
                    "title": cfg.get("title", doc_id),
                    "pdf_a": cfg.get("pdf_a"),
                    "note": cfg.get("note"),
                }
            )
        return out

    @app.tool()
    def audit_pdf(target: str = "", strict: bool = False) -> dict[str, Any]:
        """Run veraPDF over a single PDF or every PDF under build/.

        Args:
            target: PDF path or directory. Defaults to `build/` under
                EUXIS_CONTENT_DIR.
            strict: When True, every blocking-flavour FAIL is surfaced
                in the response (`blocking_failure: True`); the caller
                decides whether to treat this as an error.

        Returns the audit report dict (summary, by_pdf, by_flavour).
        Requires `verapdf` on PATH; the report contains
        `verapdf_present: False` when it is not.
        """
        root = _content_root()
        target_path = Path(target) if target else root / "build"
        registry_stems = audit_mod._registry_stems(root / "data" / "meta.yaml")
        pdfs = audit_mod.collect_pdfs(target_path, root / "build", registry_stems)
        if not pdfs:
            return {"summary": {"pdfs": 0}, "by_pdf": {}, "by_flavour": {}}
        report = audit_mod.audit(pdfs)
        report["blocking_failure"] = strict and audit_mod._is_blocking(report)
        return report

    @app.tool()
    def render(doc_id: str, fmt: str = "latex", mode: str = "draft") -> dict[str, Any]:
        """Render a registered template-driven document.

        Args:
            doc_id: registered template id (see `list_docs`).
            fmt: one of `latex`, `markdown`, `json`, `text`.
            mode: one of `draft`, `submission`, `camera-ready`.

        Returns `{"doc_id": …, "format": …, "output_path": …, "bytes": int}`.
        """
        root = _content_root()
        render_mod.render_document(doc_id, fmt=fmt, build_mode=mode, content_root=root)
        ext = {"latex": "tex", "markdown": "md", "json": "json", "text": "txt"}[fmt]
        out_path = root / "build" / ".cache" / "rendered" / f"{doc_id}.{ext}"
        return {
            "doc_id": doc_id,
            "format": fmt,
            "mode": mode,
            "output_path": str(out_path),
            "bytes": out_path.stat().st_size if out_path.exists() else 0,
        }

    @app.tool()
    def doc_count() -> int:
        """Return the number of documents registered in data/meta.yaml.

        Cheap probe for clients that just want to verify connectivity
        and that the engine sees a valid manifest.
        """
        return len(_load_meta().get("documents") or {})

    # ── Resources ───────────────────────────────────────────────────────

    @app.resource("euxis://meta", mime_type="text/yaml")
    def meta_resource() -> str:
        """Return the raw text of data/meta.yaml (project manifest)."""
        meta_path = _content_root() / "data" / "meta.yaml"
        if not meta_path.exists():
            return ""
        return meta_path.read_text(encoding="utf-8")

    @app.resource("euxis://audit/latest", mime_type="application/json")
    def audit_latest_resource() -> str:
        """Return the last audit report JSON (build/.audit/latest.json).

        Empty JSON object when no audit has run yet.
        """
        path = _content_root() / "build" / ".audit" / "latest.json"
        if not path.exists():
            return "{}"
        return path.read_text(encoding="utf-8")

    @app.resource("euxis://version", mime_type="application/json")
    def version_resource() -> str:
        """Return the engine version and MCP Server Card metadata."""
        return json.dumps(
            {
                "name": "euxis-publisher",
                "version": _engine_version(),
                "mcp_spec": "0.1",
                "content_root": str(_content_root()),
                "homepage": ("https://github.com/sebastienrousseau/euxis-publisher"),
            },
            indent=2,
        )

    return app


def _engine_version() -> str:
    """Read the engine version from pyproject.toml without importlib.metadata.

    Avoids the pip-install-required path so the resource works in
    editable / source checkouts the same as in installed packages.
    """
    try:
        import tomllib  # 3.11+
    except ImportError:  # pragma: no cover
        return "unknown"
    project_root = Path(__file__).resolve().parent.parent.parent
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data.get("project", {}).get("version", "unknown")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="euxis-mcp",
        description="MCP server for the Euxis Publisher engine.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use Streamable HTTP transport instead of stdio.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP host (only with --http; default 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port (only with --http; default 8000).",
    )
    args = parser.parse_args(argv)

    if FastMCP is None:
        print(
            "ERROR: FastMCP is not installed.\nInstall with: pip install 'euxis-publisher[mcp]'",
            file=sys.stderr,
        )
        return 1

    app = create_server()
    if args.http:
        # FastMCP 3.x: streamable HTTP transport.
        app.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        # Default: stdio transport, the Claude Code default.
        app.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
