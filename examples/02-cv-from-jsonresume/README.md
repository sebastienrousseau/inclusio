# 02 — CV from a JSON Resume

End-to-end: take a [JSON Resume](https://jsonresume.org/) document,
convert it to `inclusio`'s CV YAML schema, render the CV through the
Jinja2 template, build the tagged PDF, and score it against the ATS
heuristic + a job-description brief.

**You'll learn:** the `import-resume` → `tailor` → `build` → `judge`
chain that produces an EAA-compliant CV PDF *and* a numeric ATS
fit-score against a target role.

## Prereqs

- `inclusio` (`pip install inclusio`)
- LuaLaTeX (for the build step)

## Run it

```bash
make            # full chain: import → render → build → judge
make ats        # score CV against the ATS judge
make jd-fit     # score CV against ./brief.txt
make clean
```

## What the pieces do

| Step | CLI | Output |
|---|---|---|
| 1. Import | `inclusio import-resume resume.json -o data/cv-data.yaml` | YAML matching the engine's CV schema |
| 2. Render | `inclusio render --doc cv --format latex` | `build/.cache/rendered/cv.tex` (Jinja2 → LaTeX) |
| 3. Build | `inclusio build --doc cv` | `build/cv.pdf` (tagged) |
| 4. Audit | `inclusio audit --strict` | veraPDF report |
| 5. Judge (ATS) | `inclusio judge --judge ats --doc cv` | Grade + actionable findings |
| 6. Judge (JD fit) | `inclusio judge --judge jd_fit --doc cv --brief brief.txt` | Score vs. a target role |

## Files

- `resume.json` — sample JSON Resume document (jsonresume.org v1
  schema)
- `brief.txt` — sample job description for the `jd_fit` judge
- `data/meta.yaml` — registers the CV with `inclusio`
- `data/cv-data.yaml` — *generated* by step 1 (don't edit by hand)

## Tailoring against a real role

Instead of `import-resume`, use `inclusio tailor brief.txt
--type cv` to drive the heuristic CV tailor over an existing
base YAML. Add `--llm-url http://localhost:8080` to involve a
local llama.cpp instance for the rerank pass.
