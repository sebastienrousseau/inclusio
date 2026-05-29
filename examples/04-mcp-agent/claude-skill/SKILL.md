---
name: inclusio-publisher
description: Drive the inclusio publishing engine via MCP — render, audit, and report on PDF/UA-2 tagged documents.
metadata:
  type: mcp-client
---

You have access to the `inclusio` MCP server. Use it to:

- **`list_docs`** — when the user asks "what's in my project" / "what
  docs are registered".
- **`doc_count`** — when the user wants a quick connectivity check.
- **`audit_pdf`** — when the user asks for the EAA / accessibility
  audit. Pass `strict: true` to surface blocking failures.
- **`render`** — when the user wants a Jinja2-driven doc rendered to
  LaTeX / Markdown / JSON / plain-text. Default format is `latex`.

Resources:

- `inclusio://meta` — the project manifest.
- `inclusio://audit/latest` — last audit report.
- `inclusio://version` — engine version + content-root path.

**Important constraints (from inclusio's MCP server design):**

1. Never auto-mutate `data/meta.yaml` — that's the user's source of
   truth. Always ask before suggesting an edit.
2. Cloud LLM API keys are user-supplied via env vars; never assume a
   key is available.
3. When the audit reports a FAIL, surface the per-flavour line from
   the report verbatim — don't paraphrase, that's auditor-relevant
   evidence.
