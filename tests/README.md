# `tests/` — Engine test suite

Public pytest suite. **900+ tests** at v0.0.3; coverage gate
**97 %** (currently 98 %); docstring gate **100 %**.

| Subset | Path | Purpose |
|---|---|---|
| Smoke | `test_assets.py`, `test_build.py`, `test_engine_smoke.py`, `test_macro_contract.py` | Run on every CI matrix entry (≤ 20 s) |
| Unit | Most files prefixed `test_*` | Per-module coverage |
| Integration | `test_pdf_validation.py`, `test_pdf_ua*.py` | Need built PDFs under `build/`; auto-skip otherwise |
| Coverage-close | `test_coverage_gap_close.py` | Targeted closure of the last 1 % gap |

Run:

```bash
make test          # smoke
make coverage      # full suite + gate
pytest tests/test_judge_ats.py -v   # a single file
```

Content-specific assertions (brand strings, client copy) live in
external content repos, not here.
