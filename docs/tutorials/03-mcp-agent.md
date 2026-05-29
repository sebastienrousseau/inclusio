# Tutorial 3 — Driving inclusio from an MCP agent

> 25 minutes · Difficulty: medium · Example:
> [`examples/04-mcp-agent/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/04-mcp-agent/)

By the end of this tutorial you'll have inclusio running as an MCP
server, connected to Claude Code, and you'll have driven a real
build + audit + judge sequence through natural language.

## Why MCP

The [Model Context Protocol](https://modelcontextprotocol.io) is the
emerging standard for letting LLM agents discover and invoke tools.
inclusio ships a FastMCP server (`inclusio-mcp`) that exposes the
engine's read + audit surface so Claude Code, Claude Desktop, Cursor,
Continue, or any other MCP client can:

- **List documents** registered in `data/meta.yaml`
- **Audit PDFs** for EAA / WCAG compliance
- **Render** Jinja2-driven templates to LaTeX / Markdown / JSON / text
- **Probe** version + project manifest as resources

Write operations (mutating `data/meta.yaml`, deleting build outputs)
are intentionally NOT exposed — the agent reads + computes, you write.

> **2026 note:** The MCP 2026-07-28 RC introduces *Tasks* — stateless
> resumable operations — which fit publishing pipelines (typeset →
> tag → validate → sign) cleanly. inclusio's server will adopt Tasks
> in v0.0.4.

## Step 1 — Install the MCP extra

```bash
pip install 'inclusio[mcp]'
inclusio-mcp --help
```

You should see the stdio + HTTP transport options. The default is
stdio, which is how Claude Code / Claude Desktop / Cursor connect.

## Step 2 — Test the server in isolation

```bash
inclusio-mcp --http --port 8765 &
curl http://localhost:8765/mcp/list_tools | jq
kill %1
```

You should see four registered tools: `list_docs`, `doc_count`,
`audit_pdf`, `render`.

## Step 3 — Wire into Claude Code

Add to `~/.claude/claude_desktop_config.json` (or your project's
`.mcp.json`):

```json
{
  "mcpServers": {
    "inclusio": {
      "command": "inclusio-mcp",
      "env": {
        "INCLUSIO_CONTENT_DIR": "/absolute/path/to/your/content-repo"
      }
    }
  }
}
```

Restart the client. In a new conversation, type `/mcp` to see the
registered servers; `inclusio` should appear with its four tools and
three resources.

## Step 4 — Drive it with prompts

> **List my registered documents.**

Claude Code calls `list_docs`, returning the manifest entries from
`data/meta.yaml`. You'll see something like:

```
- id: cv         class: pub-cv     title: My CV
- id: paper      class: pub-paper  title: Whisper, Real-Time ASR
- id: patent     class: pub-patent title: Tagged PDF Patent
```

> **Audit `build/cv.pdf` against PDF/UA-2 in strict mode.**

Claude calls `audit_pdf(target="build/cv.pdf", strict=True)` and gets
back the veraPDF report. If a profile fails, Claude surfaces the
per-flavour line verbatim — auditor-relevant evidence shouldn't be
paraphrased.

> **Render the cv template to plain text so I can review it.**

Claude calls `render(doc_id="cv", fmt="text", mode="draft")`. The
output path lands under `build/.cache/rendered/cv.txt`.

## Step 5 — Inspect the resources

Resources are read-only side channels. Claude Code shows them in the
attachment picker:

| URI | MIME | When to use |
|---|---|---|
| `inclusio://meta` | `text/yaml` | "What documents am I working with?" |
| `inclusio://audit/latest` | `application/json` | "What did the last audit find?" |
| `inclusio://version` | `application/json` | "Is the server reachable, and what version?" |

> **Read the latest audit report and summarise the failures.**

Claude fetches `inclusio://audit/latest` as a resource and walks the
JSON. Without the resource, the agent would have to call `audit_pdf`
which is more expensive.

## Step 6 — Author a custom skill

Drop a Claude Code skill at
`.claude/skills/your-skill/SKILL.md`. A working example lives in the
tutorial's companion folder:

```markdown
---
name: inclusio-publisher
description: Drive the inclusio engine via MCP.
---

You have access to the `inclusio` MCP server. Use it to:

- list_docs when the user asks what's registered.
- audit_pdf when the user asks for the EAA audit.
- render when the user wants a Jinja2-driven doc rendered.

Never auto-mutate `data/meta.yaml` — ask the user first.
Surface audit FAIL lines verbatim — that's auditor-relevant.
```

See [`examples/04-mcp-agent/claude-skill/SKILL.md`](
https://github.com/sebastienrousseau/inclusio/tree/main/examples/04-mcp-agent/claude-skill/SKILL.md) for the full
example.

## Architecture — what the server looks like

```
┌─────────────┐      stdio       ┌────────────────────┐
│ Claude Code │ ───────────────> │ inclusio-mcp       │
│  /mcp tools │ <─────────────── │ (FastMCP server)   │
└─────────────┘    JSON-RPC      └────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────────┐
                              │ inclusio Python package   │
                              │  cli.build / cli.audit /  │
                              │  cli.render / mcp.server  │
                              └───────────────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────────┐
                              │ Content tree              │
                              │  data/meta.yaml           │
                              │  src/*.tex, build/*.pdf   │
                              └───────────────────────────┘
```

The server reads `INCLUSIO_CONTENT_DIR` to resolve the content tree.
Without it, the server uses the engine's bundled content (the
inclusio repo's own showcase).

## Common questions

**Can I expose more tools?** Yes — add a `@app.tool()`-decorated
function to `inclusio/mcp/server.py` that calls into the engine. See
the [MCP server reference docs](../mcp-server.md) for the contract.

**What about long-running builds?** The MCP RC's Tasks layer is the
right answer; inclusio adopts it in v0.0.4. For now, `inclusio build`
runs synchronously inside the tool call — keep documents small or use
the stand-alone CLI for long jobs.

**Is the server safe to run network-exposed?** With `--http`, yes —
the surface is read-only and the operations (audit / render) are
side-effect-free. But authentication is not built-in; put it behind
a reverse proxy if you bind to a public interface.

## Next steps

- [Tutorial 4 — Camera-ready chain](./04-camera-ready.md)
- [`docs/mcp-server.md`](../mcp-server.md) — the MCP server reference.
- [MCP specification](https://modelcontextprotocol.io/specification)
