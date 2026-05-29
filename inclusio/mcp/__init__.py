"""Model Context Protocol (MCP) server for the Inclusio engine.

Exposes the engine's CLI surface as MCP tools + resources so Claude
Code, Cursor, and other MCP clients can invoke it directly:

  Tools:
    - list_docs         enumerate registered documents
    - audit_pdf         run veraPDF on a single PDF or directory
    - lint              chktex + vale + semantic gate
    - render            render a doc template (latex/markdown/json/text)

  Resources:
    - inclusio://meta              data/meta.yaml (project manifest)
    - inclusio://audit/latest      build/.audit/latest.json (last audit run)
    - inclusio://pdf/{doc_id}      build/<type>/<doc_id>.pdf binary

The server uses FastMCP (the official MCP Python SDK's high-level API)
with stdio transport by default and Streamable HTTP available via
`inclusio-mcp --http`. Per docs/strategy-2026.md decision D4, the server
is the brokered-access surface for AI-authoring clients.
"""

from __future__ import annotations
