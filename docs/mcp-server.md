# MCP server — `euxis-mcp`

Sprint 6 (S6.4) ships an MCP (Model Context Protocol) server that
exposes the Euxis Publisher engine's read + audit surface to AI
clients (Claude Code, Cursor, the MCP Inspector). Forcing Function #4
in [`strategy-2026.md`](strategy-2026.md): the AI authoring layer.

## Install

```bash
pip install 'euxis-publisher[mcp]'
```

The `mcp` extra pulls in `mcp[cli]>=1.27.0` (the official Python SDK
with FastMCP + inspector). Without the extra, `euxis-mcp` prints a
clear install hint and exits 1.

## Run

```bash
# stdio transport (Claude Code default)
euxis-mcp

# Streamable HTTP transport
euxis-mcp --http                       # 127.0.0.1:8000
euxis-mcp --http --port 9090

# Or directly through Python
python -m euxis_publisher.mcp.server
```

The server honours `EUXIS_CONTENT_DIR` like every other engine CLI.

## Tools

| Name | Inputs | Returns | Notes |
|---|---|---|---|
| `list_docs` | none | `list[{id, class, src, title, pdf_a, note}]` | Enumerates `data/meta.yaml` `documents:` block. Empty list when manifest is absent. |
| `audit_pdf` | `target: str = ""`, `strict: bool = False` | audit-report dict (`summary`, `by_pdf`, `by_flavour`, `blocking_failure`) | Wraps the `cli.audit.audit()` path. `target` defaults to `build/`. `strict=True` surfaces blocking failures in the response. |
| `render` | `doc_id: str`, `fmt: str = "latex"`, `mode: str = "draft"` | `{doc_id, format, mode, output_path, bytes}` | Wraps `cli.render.render_document()`. `fmt ∈ {latex, markdown, json, text}`. |
| `doc_count` | none | `int` | Cheap probe — clients use this to verify connectivity + manifest. |

## Resources

| URI | MIME | Contents |
|---|---|---|
| `euxis://meta` | `text/yaml` | Raw `data/meta.yaml`. Empty string when absent. |
| `euxis://audit/latest` | `application/json` | `build/.audit/latest.json`. Empty JSON object when no audit has run. |
| `euxis://version` | `application/json` | Engine version + MCP Server Card (`name`, `version`, `mcp_spec`, `content_root`, `homepage`). |

## Claude Code integration

The repo ships a Claude skill at `.claude/skills/euxis-publisher/SKILL.md`
that documents the engine's CLI surface. The MCP server complements the
skill: the skill tells Claude what's possible; the server provides
typed structured access.

To register the server with Claude Code:

```bash
# Add to ~/.config/claude-code/mcp.json (or platform equivalent)
{
  "mcpServers": {
    "euxis-publisher": {
      "command": "euxis-mcp",
      "env": {
        "EUXIS_CONTENT_DIR": "/path/to/content/repo"
      }
    }
  }
}
```

## Cursor integration

`.cursor/rules/euxis-publisher.mdc` ships in this repo and auto-loads
when `.tex`, `.cls`, `.sty`, `meta.yaml`, or `*-data.yaml` files are
open. The rule points Cursor at the MCP tools above for structured
queries.

## Roadmap

- **Sprint 6 (current)**: read + audit surface — done.
- **Sprint 7**: write-side tools (`tailor` brief → CV, `lint` semantic
  + chktex + vale), LLM judge bridge (citation grounding, ATS
  scoring).
- **Sprint 8**: provenance — sign tool outputs with SLSA + C2PA
  manifests; expose `euxis://provenance/{doc_id}` resource.

See [`audit-2026-05.md`](audit-2026-05.md) §5 for the full Sprint 6+
plan.

## Reference

- [MCP spec](https://spec.modelcontextprotocol.io/)
- [FastMCP docs](https://gofastmcp.com/)
- [Anthropic skill conventions](https://docs.anthropic.com/claude/docs/claude-code/skills)
