# Tutorials

End-to-end walkthroughs for the four most common inclusio scenarios.
Each tutorial corresponds to one folder under
[`examples/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/) — read the tutorial for the why, then
run the example for the how.

| # | Tutorial | Example | What you'll have at the end |
|---|---|---|---|
| 1 | [Building a tagged PDF](./01-tagged-pdf.md) | [`01-hello-world/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/01-hello-world/) | A PDF/UA-2 + WTPDF + PDF/A-4f triple-conforming artefact |
| 2 | [Scoring a CV against an ATS](./02-judge-cv.md) | [`02-cv-from-jsonresume/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/02-cv-from-jsonresume/) | A CV with a grade, findings, and a JD-fit score |
| 3 | [Driving inclusio from an MCP agent](./03-mcp-agent.md) | [`04-mcp-agent/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/04-mcp-agent/) | A working Claude Code workflow over the engine |
| 4 | [Camera-ready chain (C2PA + PAdES + SLSA)](./04-camera-ready.md) | [`05-c2pa-sign/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/05-c2pa-sign/), [`06-pades-sign/`](https://github.com/sebastienrousseau/inclusio/tree/main/examples/06-pades-sign/) | A PDF with three provenance layers |

```{toctree}
:hidden:
:maxdepth: 1

01-tagged-pdf
02-judge-cv
03-mcp-agent
04-camera-ready
```
