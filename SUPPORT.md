# Support

Thanks for using **Inclusio**. Here's where to go for help.

## Documentation

The quickest answer to most questions is in the docs:

- **[Quickstart](./docs/quickstart.md)** — five-minute walkthrough.
- **[Tutorials](./docs/tutorials/)** — four end-to-end walkthroughs
  paired 1 : 1 with [`examples/`](./examples/).
- **[Reference docs](./docs/)** — tagged-PDF stack, multi-format
  emit, judges, provenance, MCP server.

## "How do I …?"

Open a [Q&A discussion](https://github.com/sebastienrousseau/inclusio/discussions)
on the repo. Common ground:

| You want to … | Read |
|---|---|
| Build your first tagged PDF | [`examples/01-hello-world/`](./examples/01-hello-world/) |
| Score a CV against a job description | [`examples/02-cv-from-jsonresume/`](./examples/02-cv-from-jsonresume/) + [`docs/judges.md`](./docs/judges.md) |
| Sign a PDF with C2PA / PAdES | [`examples/05-c2pa-sign/`](./examples/05-c2pa-sign/), [`examples/06-pades-sign/`](./examples/06-pades-sign/) + [`docs/provenance.md`](./docs/provenance.md) |
| Drive Inclusio from Claude Code / Cursor | [`examples/04-mcp-agent/`](./examples/04-mcp-agent/) + [`docs/mcp-server.md`](./docs/mcp-server.md) |

## Bugs

Open a [bug report](https://github.com/sebastienrousseau/inclusio/issues/new?template=bug.yml).
Please include:

- Inclusio version (`inclusio --version` or `pip show inclusio`)
- Python version (`python --version`)
- OS + LaTeX distribution (when relevant)
- Minimal reproducer — ideally a 10-line `.tex` or YAML fragment
- Expected vs. actual behaviour
- Full error output

## Feature requests

Open a [feature request](https://github.com/sebastienrousseau/inclusio/issues/new?template=feature.yml).
Explain the use case first (the *why*) — the *what* often follows.

## Security

**Do NOT open a public issue for security reports.** See
[`SECURITY.md`](./SECURITY.md) for the responsible-disclosure
channel.

## Commercial support

Inclusio is MIT-licensed and maintained on a best-effort basis.
There's no commercial support contract today; reach out via the
contact details in [`pyproject.toml`](./pyproject.toml) if that
changes for you.

## Response times

This is an open-source side project. Realistic expectations:

- **Bugs with a clear reproducer:** triaged within ~1 week.
- **Feature requests:** discussed but not promised — see the
  CHANGELOG `[Unreleased]` block for what's queued.
- **Security reports:** acknowledged within 72 hours.
