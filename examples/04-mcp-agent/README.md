# 04 — MCP server + agent driver

Run `inclusio-mcp` as a stdio MCP server, connect it to Claude Code
(or any MCP client), and watch the agent drive `list_docs`,
`audit_pdf`, `render`, and `doc_count` against a content tree.

**You'll learn:** the MCP server's tool/resource surface and how to
wire it into an agent without writing any glue code.

## Prereqs

- `inclusio` with the MCP extra: `pip install 'inclusio[mcp]'`
- Claude Code, Continue, or any MCP client (the [official Claude
  Desktop](https://claude.ai/download) works too)

## Run the server

```bash
inclusio-mcp                       # stdio transport (Claude Code default)
inclusio-mcp --http                # Streamable HTTP on :8000
inclusio-mcp --http --port 9090    # custom port
```

## Wire it into Claude Code

Add to `~/.claude/claude_desktop_config.json` (Desktop) or your
project's `.mcp.json`:

```json
{
  "mcpServers": {
    "inclusio": {
      "command": "inclusio-mcp",
      "env": {
        "INCLUSIO_CONTENT_DIR": "/path/to/your/content"
      }
    }
  }
}
```

Restart the client; `inclusio` appears as a tool source. Try:

> List my registered documents.
>
> Audit `build/cv.pdf` against PDF/UA-2.
>
> Render `cv` to text so I can review it.

## Tool surface

| Tool | Purpose |
|---|---|
| `list_docs` | Enumerate `data/meta.yaml documents:` |
| `doc_count` | Number of registered documents |
| `audit_pdf` | Run veraPDF over a PDF or directory |
| `render` | Render a Jinja2-template-driven document |

## Resource surface

| URI | Mime | Content |
|---|---|---|
| `inclusio://meta` | `text/yaml` | Raw `data/meta.yaml` |
| `inclusio://audit/latest` | `application/json` | Most recent audit report |
| `inclusio://version` | `application/json` | Engine version + Server Card |

## Authoring a custom skill

Drop your own Claude Code skill in `.claude/skills/<name>/SKILL.md`
that consumes the MCP tools above. See [`claude-skill/SKILL.md`](
./claude-skill/SKILL.md) in this folder for a working example.
