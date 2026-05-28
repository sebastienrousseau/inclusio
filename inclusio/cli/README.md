# CLI

Packaged command entrypoints for the public engine.

- `build.py`: top-level orchestrator for build, render, blog, tailor, lint, and cleanup commands
- `render.py`: Jinja2-based render pipeline
- `sitemap.py`: semantic metadata generation
- `tailor.py`: brief-to-document tailoring flow

Preferred invocation style:

```bash
python3 -m inclusio.cli.build list
python3 -m inclusio.cli.render --doc cv
python3 -m inclusio.cli.sitemap --pretty
python3 -m inclusio.cli.tailor data/jobs/test.txt --no-ai
```

`python3 -m inclusio.cli.build build` and `make publish` also scan
`data/jobs/` and auto-generate tailored YAML for supported brief formats before
they compile PDFs.
