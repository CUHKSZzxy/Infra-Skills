# Bounded Kernel Campaign

Use a campaign for multiple optimization hypotheses and the single runner for
one-off validation. Start from `scripts/microbench_case_template.py`; each
`BenchmarkPair` must compare equivalent baseline/candidate callables for one
production-relevant shape and record tolerances plus path-affecting knobs.

```bash
: "${INFRA_SKILLS_HOME:?set INFRA_SKILLS_HOME from docs/conventions/machines.md}"
: "${CONDA_ROOT:?set CONDA_ROOT from docs/conventions/machines.md}"
: "${LMDEPLOY_DEV_SOURCE:?set LMDEPLOY_DEV_SOURCE from docs/conventions/machines.md}"
SKILL_DIR="$INFRA_SKILLS_HOME/skills/optimize-kernel"
PYTHON_BIN="$CONDA_ROOT/envs/dev/bin/python"
RUN_DATE=${RUN_DATE:-$(date +%Y%m%d)}
RUN_DIR="$LMDEPLOY_DEV_SOURCE/benchmark/${RUN_DATE}_kernel_<target>"

"$PYTHON_BIN" \
  "$SKILL_DIR/scripts/kernel_campaign.py" init "$RUN_DIR" \
  --case-file /path/to/kernel_cases.py \
  --source-checkout "$LMDEPLOY_DEV_SOURCE" \
  --python "$PYTHON_BIN" \
  --gpu 0 --max-rounds 5

"$PYTHON_BIN" \
  "$SKILL_DIR/scripts/kernel_campaign.py" run "$RUN_DIR" \
  --hypothesis "Coalesce cache payload loads for long decode contexts"
```

Initialization freezes the case-file hash; the first run freezes
`workloads.json`. Create a new campaign when shapes, tolerances, required
cases, or headline cases change. Each round records the hypothesis, command,
samples, decision, and comparison report; `status` reports the checkpoint.

For each round, make one narrow edit, run focused correctness before timing,
let the paired runner interleave A/B samples, and keep a candidate only after
dispatch and integration validation. Resolve unclear correctness before timing.
Continue within the configured budget when evidence is inconclusive; stop at
that budget or when further work requires a change in scope. The wrapper defaults
to one GPU, checkpoints evidence, and does not edit, commit, or push source. Use
NCU or a serving trace only when it would choose the next edit.
