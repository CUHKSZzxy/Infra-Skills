# External Kernel Evidence

Use this reference when an LMDeploy kernel campaign needs hardware-specific
design evidence or Nsight Compute counters. Keep these optional dependencies
outside the core skill so their detailed knowledge and metric schemas remain
updatable at their upstream cadence.

## Initialize

Resolve the Infra-Skills checkout from `INFRA_SKILLS_HOME` in local conventions,
then initialize the pinned HTTPS submodules if their `SKILL.md` files are absent:

```bash
git -C "$INFRA_SKILLS_HOME" submodule update --init \
  external/KernelWiki external/ncu-report-skill

KERNEL_WIKI="$INFRA_SKILLS_HOME/external/KernelWiki"
NCU_SKILL="$INFRA_SKILLS_HOME/external/ncu-report-skill"
PYTHON_BIN=/path/to/paired-env/bin/python
```

Do not update submodule revisions during an optimization campaign. Record both
gitlink SHAs with the benchmark provenance.

## Query KernelWiki

Use KernelWiki for Blackwell or Hopper kernel design, architecture-specific
symptoms, and concrete upstream PR precedents. Do not use it for generic host,
scheduler, or distributed-system changes.

```bash
"$PYTHON_BIN" \
  "$KERNEL_WIKI/scripts/query.py" \
  "paged attention long scoreboard split k" \
  --architecture sm90 --language triton --compact
```

Search by the observed symptom, kernel family, GPU architecture, and language.
Open the few relevant pages with `scripts/get_page.py --follow-sources`. Record
page IDs, paths, confidence, upstream sources, and why each technique applies to
the frozen LMDeploy shape. Treat source-reported or inferred speedups as
hypotheses, not expected results.

## NCU Gate

Read the pinned `external/ncu-report-skill/SKILL.md` and its detailed references
when counters are needed. Use NCU only when at least one condition holds:

- stable timing identifies a hot kernel but not its limiting resource,
- an architecture-specific candidate needs occupancy, stall, memory, tensor
  core, or tail-effect evidence,
- a material regression needs diagnosis before the next edit.

Do not profile every campaign round. First check `ncu --version` and performance
counter access on one GPU. If `ERR_NVGPUCTRPERM` occurs, report the environment
blocker; do not change host security settings or use `sudo` automatically.

Select exactly one frozen `BenchmarkPair` case. Run its normal correctness and
paired benchmark first. The runner's profile mode then emits one implementation
repeated after a known number of warmups, allowing NCU to skip warmup launches:

```bash
PROFILE_DIR="$RUN_DIR/rounds/<round>/ncu/<case>"
mkdir -p "$PROFILE_DIR"/{reports,analysis}

ncu --set full \
  --section PmSampling --section PmSampling_WarpStates \
  -k "regex:<exact-kernel-regex>" -s 1 -c 1 \
  -o "$PROFILE_DIR/reports/full_candidate" \
  "$PYTHON_BIN" \
  "$SKILL_DIR/scripts/kernel_microbench.py" /path/to/kernel_cases.py \
  --out "$PROFILE_DIR/profile_runner.jsonl" \
  --case <case> --profile-variant candidate --profile-warmup 1 \
  -- <case-specific-args>
```

The kernel regex must match exactly one target launch per callable invocation.
If it matches more, narrow the regex or set `-s` to
`profile_warmup * matching_launches_per_invocation`; otherwise NCU may capture a
warmup sub-kernel instead of the final target launch.

Capture baseline with the same command and frozen inputs when the report needs
an A/B counter comparison. Use a fresh profile directory for each campaign
round and workload; never overwrite `.ncu-rep` files.

Collect source counters only when source mapping is available:

```bash
ncu --set source --section SourceCounters \
  -k "regex:<exact-kernel-regex>" -s 1 -c 1 \
  -o "$PROFILE_DIR/reports/source_candidate" \
  <same profile-variant command>
```

CUDA sources need `-lineinfo`. For JIT or Triton kernels without useful source
mapping, keep the full report and do not invent line-level attribution. Build a
standalone harness only when it preserves the production kernel, ABI, inputs,
and dispatch behavior; a toy reconstruction is not production evidence.

## Analyze And Report

Use `ncu --import <report> --page details` first, then the pinned helpers. The
helpers require Nsight Compute's `ncu_report` Python module; add the matching
installation's `extras/python` directory to `PYTHONPATH` when needed.

```bash
"$PYTHON_BIN" "$NCU_SKILL/helpers/analyze_reports.py" \
  --run-dir "$PROFILE_DIR" \
  --report "$PROFILE_DIR/reports/full_baseline.ncu-rep" --tag baseline \
  --report "$PROFILE_DIR/reports/full_candidate.ncu-rep" --tag candidate
```

Follow the external analysis dimensions and diagnosis playbook. On GPUs other
than B200, enumerate `action.metric_names()` and use supported equivalents
instead of assuming the helper's B200 metric list exists.

Write `$PROFILE_DIR/REPORT.md` with:

- exact kernel, workload, GPU, NCU version, command, and report paths,
- duration, occupancy/launch geometry, dominant stalls, memory/cache behavior,
  tensor-core use when relevant, and imbalance/tail evidence,
- two or three actual metric values for each diagnosis,
- ranked next edits tied to NCU evidence and KernelWiki/upstream references,
- confidence, missing metrics, source-mapping limits, and untested shapes.

NCU replay duration and rule-engine speedup estimates are diagnostic evidence,
not benchmark promotion metrics. Promotion still requires the paired campaign's
correctness, timing, regression gates, and any serving-level validation implied
by the claim.
