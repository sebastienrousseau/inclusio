# `data/` — Public fixture data

Non-sensitive YAML fixtures used by the engine and its tests.
External consumers supply their own `data/meta.yaml` and override
this directory via `INCLUSIO_CONTENT_DIR`.

| Path | Role |
|---|---|
| `data/meta.yaml` | Document + blog registry for the public fixture set |
| `data/*-data.yaml` | Sample structured inputs for the template-driven docs (CV, paper, FAQ, guide) |
| `data/blog/` | Sample blog metadata used by blog-rendering tests |
| `data/jobs/` | Sample briefs for the tailoring flow |
| `data/stopwords.txt` | Stopword list used by the JD-fit judge |

External / client-owned data lives in a consumer's own content
repo, not here.
