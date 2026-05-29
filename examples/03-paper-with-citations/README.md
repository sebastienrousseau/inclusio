# 03 — Paper with citations + multi-format

A scholarly paper with three `\cite{}` calls and a small
`thebibliography` — built into a tagged PDF, emitted to HTML5, JATS
XML, and EPUB3, and scored by the citation-grounding judge.

**You'll learn:** the `build` → `emit` → `audit` → `judge` pipeline
for scholarly content, and how the four output formats relate.

## Prereqs

- `inclusio` (`pip install inclusio`)
- LuaLaTeX + Pandoc on `PATH`

## Run it

```bash
make            # build PDF + emit HTML/JATS/EPUB + audit + judge
make emit       # only the multi-format emission
make citations  # only the citation-grounding judge
make clean
```

## Output

```
build/
  paper.pdf                    # Tagged PDF/UA-2 + PDF/A-4f
  emit/
    paper.html                 # HTML5 with accessibility metadata
    paper.xml                  # JATS XML (1.4 archival)
    paper.epub                 # EPUB3 with Schema.org accessibility
  .audit/eaa-*.json            # veraPDF report
```

## Citation-grounding judge

The `citations` judge parses every `\cite{key}` in the source,
matches each against the `\bibitem{key}` entries, and (when an LLM
is reachable) asks it whether the citation context plausibly
supports the bibitem description. Returns a graded report with a
per-citation finding when the support is weak.

```bash
inclusio judge --doc paper --judge citations            # heuristic only
inclusio judge --doc paper --judge citations \
  --llm-url http://localhost:8080                       # + local rerank
inclusio judge --doc paper --judge citations \
  --llm-url https://api.anthropic.com/v1/messages \
  --llm-model claude-opus-4-7                           # + cloud rerank
```

(Cloud LLMs need `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the env;
inclusio refuses to auto-discover keys.)
