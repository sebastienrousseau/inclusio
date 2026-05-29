# Benchmarks

Hot-path micro-benchmarks driven by
[`pytest-benchmark`](https://pytest-benchmark.readthedocs.io/).
Targets the call sites that dominate `make build`, `make audit`, and
`make judge` end-to-end times.

## Run

```bash
make benchmark                          # default
pytest benches/ --benchmark-only        # equivalent

# Save a baseline JSON for regression gating:
pytest benches/ --benchmark-only --benchmark-save=baseline

# Compare a later run against the baseline:
pytest benches/ --benchmark-only --benchmark-compare-fail=mean:5%
```

## Regression gating — anatomy of a comparison

After saving a baseline (`--benchmark-save=baseline`), a later
run produces a delta block:

```
Comparing against benchmark baseline:

Name (time in us)         Min     Mean    Median    OPS (Kops/s)
---------------------------------------------------------------
test_bench_jaccard      6.04    6.45    6.10           155.04
  (vs baseline)         5.83 → +3.6%    6.04 → +0.9%   162.59 → -4.7%
```

A `+5%` change on the `mean` column with
`--benchmark-compare-fail=mean:5%` fails the suite. The baseline
JSON belongs under `benches/baselines/<sha>.json` once we adopt
regression gating in CI.

## Soft budgets (per call, on a modern laptop)

| Target | Budget | Last reading |
|---|---:|---:|
| `judge.jaccard` | < 0.1 ms | 6 μs |
| `judge.citations.parse_citations` | < 0.5 ms | 16 μs |
| `judge.citations.parse_bibitems` | < 0.5 ms | 20 μs |
| `provenance.c2pa.build_manifest_json` | < 0.5 ms | 28 μs |
| `judge.citations.score_citations` | < 1 ms | 41 μs |
| `judge.jd_fit.extract_keywords` (6 KB CV) | < 0.5 ms | 96 μs |
| `judge.ats.score_cv` | < 1 ms | 109 μs |
| `judge.jd_fit.score_jd_fit` | < 0.5 ms | 177 μs |
| `cli.render.render_text` (CV) | < 5 ms | 200 μs |

## Notes

- Benchmarks share the same `pytest-benchmark` plugin. The module
  guards on `pytest.importorskip("pytest_benchmark")` so workflows
  that don't install the plugin (e.g. Build Documents) skip the
  whole suite cleanly.
- CI runs the suite observationally — no regression gate yet. Promote
  to a gate by checking in a baseline JSON and adding
  `--benchmark-compare-fail=mean:5%` to the `make benchmark` target.
- A baseline JSON belongs under `benches/baselines/` once we adopt
  regression gating.
