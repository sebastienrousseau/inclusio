# `inclusio.tools` — Supporting utilities

Helpers the engine uses internally but that are also useful as
stand-alone Python modules.

| Module | What it does |
|---|---|
| `fix_semantic` | Auto-fixes forbidden direct-formatting LaTeX commands (`\textbf`, `\textit`, `\vspace`, …) into their semantic equivalents. |
| `stamp_pdfs` | `pikepdf`-based PDF post-processor: provenance metadata, optional watermark, optional AES-256 encryption. Used by the legacy untagged-PDF build path. |
| `overlay` | Deep-merge of base + overlay YAML for CV / paper / patent variant authoring (e.g. one base CV + a per-employer overlay). |

## CLI usage

Each tool is callable as a Python module:

```bash
python -m inclusio.tools.fix_semantic src/        # in-place
python -m inclusio.tools.fix_semantic src/ --dry-run --verbose
python -m inclusio.tools.stamp_pdfs build/ --watermark DRAFT
```

## Library usage — overlay-driven variants

```python
# variant.py — base CV + employer-specific overrides
from inclusio.tools.overlay import merge

base = {
    "name":     "Jane Doe",
    "role":     "Staff Engineer",
    "summary":  "Distributed systems with 12 years of production experience.",
    "skills":   ["Python", "Go", "Kubernetes", "PostgreSQL"],
}
overlay = {
    "role":     "Senior Platform Engineer",          # overrides
    "skills":   ["Python", "Go", "Rust", "OpenTelemetry"],  # replaces
    "context":  "Application to Acme Platform team", # adds
    "summary":  None,                                # deletes
}

variant = merge(base, overlay)
assert "summary" not in variant            # None in overlay → key deleted
assert variant["role"] == "Senior Platform Engineer"
assert variant["skills"] == ["Python", "Go", "Rust", "OpenTelemetry"]
```

## Stability

All three modules are public; the function signatures are tracked
under the 97 % coverage gate. The pikepdf-backed `stamp_pdfs` is
maintained for the legacy untagged-PDF path — for new content,
prefer the Sprint-5 tagged path the engine builds by default.
