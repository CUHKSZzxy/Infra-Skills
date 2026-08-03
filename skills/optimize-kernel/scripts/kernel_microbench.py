#!/usr/bin/env python3
"""Generic CUDA-event runner for LMDeploy kernel microbench cases.

Write a small case file that defines ``build_cases(args)`` and returns
``BenchmarkCase`` or ``BenchmarkPair`` objects. This runner handles warmup,
timing, correctness hooks, metadata, and JSONL output so kernel experiments
share one measurement loop.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
sys.modules.setdefault("kernel_microbench", sys.modules[__name__])


@dataclass
class BenchmarkCase:
    """One directly timed kernel or kernel-like callable."""

    name: str
    run: Callable[[], Any]
    shape: str = ""
    dtype: str = ""
    bytes_moved: int | None = None
    flops: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    check: Callable[[], bool | dict[str, Any] | None] | None = None
    before: Callable[[], None] | None = None
    after: Callable[[], None] | None = None


@dataclass
class BenchmarkPair:
    """Symmetric baseline/candidate callables for one frozen workload."""

    name: str
    baseline: Callable[[], Any]
    candidate: Callable[[], Any]
    shape: str = ""
    dtype: str = ""
    bytes_moved: int | None = None
    flops: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    check: Callable[[], bool | dict[str, Any] | None] | None = None
    prepare_trial: Callable[[int], None] | None = None
    before_sample: Callable[[str, int], None] | None = None
    before: Callable[[], None] | None = None
    after: Callable[[], None] | None = None
    required: bool = True
    headline: bool = True


def _repo_metadata() -> dict[str, Any]:
    meta: dict[str, Any] = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "argv": sys.argv,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    git_checkout = Path.cwd()
    try:
        import torch

        meta["torch"] = torch.__version__
        meta["torch_cuda"] = torch.version.cuda
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(torch.cuda.current_device())
            meta.update(
                {
                    "gpu": props.name,
                    "capability": f"{props.major}.{props.minor}",
                    "sm_count": props.multi_processor_count,
                    "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                }
            )
    except Exception as exc:
        meta["torch_error"] = repr(exc)
    try:
        import triton

        meta["triton"] = triton.__version__
    except Exception as exc:  # pragma: no cover - optional dependency surface
        meta["triton_error"] = repr(exc)
    try:
        import lmdeploy

        meta["lmdeploy_version"] = getattr(lmdeploy, "__version__", None)
        meta["lmdeploy_file"] = lmdeploy.__file__
        if lmdeploy.__file__:
            git_checkout = Path(lmdeploy.__file__).resolve().parent
    except Exception as exc:
        meta["lmdeploy_error"] = repr(exc)
    for key, cmd in {
        "git_commit": ["git", "-C", str(git_checkout), "rev-parse", "HEAD"],
        "git_branch": [
            "git",
            "-C",
            str(git_checkout),
            "branch",
            "--show-current",
        ],
        "git_status": ["git", "-C", str(git_checkout), "status", "--short"],
    }.items():
        try:
            meta[key] = subprocess.check_output(cmd, text=True).strip()
        except Exception:
            pass
    try:
        diff = subprocess.check_output(
            ["git", "-C", str(git_checkout), "diff", "--binary", "HEAD"]
        )
        meta["git_diff_sha256"] = hashlib.sha256(diff).hexdigest()
    except Exception:
        pass

    skills_root = SCRIPT_DIR.parents[2]
    for key, path in {
        "kernelwiki_commit": skills_root / "external" / "KernelWiki",
        "ncu_report_skill_commit": skills_root / "external" / "ncu-report-skill",
    }.items():
        try:
            meta[key] = subprocess.check_output(
                ["git", "-C", str(path), "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            pass
    return meta


def _append_jsonl(path: str | Path, row: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True))
        f.write("\n")


def _load_case_module(path: Path):
    path = path.resolve()
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(
        "lmdeploy_kernel_microbench_case", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load case file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize_case(
    case: BenchmarkCase | BenchmarkPair | dict[str, Any],
) -> BenchmarkCase | BenchmarkPair:
    if isinstance(case, (BenchmarkCase, BenchmarkPair)):
        return case
    if "baseline" in case or "candidate" in case:
        return BenchmarkPair(**case)
    return BenchmarkCase(**case)


def _run_check(
    case: BenchmarkCase | BenchmarkPair,
) -> tuple[bool | None, dict[str, Any]]:
    if case.check is None:
        return None, {}
    result = case.check()
    if result is None:
        return None, {}
    if isinstance(result, bool):
        return result, {}
    details = dict(result)
    correct = details.pop("correct", True)
    return bool(correct), details


def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run CUDA-event microbenchmarks from a Python case file. "
            "Pass case-specific args after '--'."
        )
    )
    parser.add_argument("case_file", help="Python file defining build_cases(args)")
    parser.add_argument("--out", required=True, help="JSONL output path")
    parser.add_argument("--label", default="candidate")
    parser.add_argument(
        "--case", action="append", default=[], help="case name to run; repeatable"
    )
    parser.add_argument("--warmup", type=int, default=25)
    parser.add_argument("--repeat", type=int, default=100)
    parser.add_argument("--trials", type=int, default=7)
    parser.add_argument("--target-sample-us", type=float, default=1000.0)
    parser.add_argument("--inner-iterations-max", type=int, default=4096)
    parser.add_argument("--flush-l2-mb", type=int, default=0)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--workload-manifest", type=Path)
    parser.add_argument("--decision-out", type=Path)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--minimum-gain-pct", type=float, default=3.0)
    parser.add_argument("--regression-pct", type=float, default=3.0)
    parser.add_argument("--fail-on-reject", action="store_true")
    parser.add_argument(
        "--profile-variant",
        choices=("baseline", "candidate"),
        help="launch one selected BenchmarkPair variant for external profiling",
    )
    parser.add_argument(
        "--profile-warmup",
        type=int,
        default=1,
        help="warmup launches before the single profile target launch",
    )
    return parser


def _load_cases(
    args: argparse.Namespace,
    case_args: list[str],
) -> list[BenchmarkCase | BenchmarkPair]:
    module = _load_case_module(Path(args.case_file))
    case_parser = argparse.ArgumentParser(add_help=False)
    if hasattr(module, "configure_parser"):
        module.configure_parser(case_parser)
    case_args = case_parser.parse_args(case_args)

    if not hasattr(module, "build_cases"):
        raise RuntimeError(f"{args.case_file} must define build_cases(args)")
    selected = set(args.case)
    cases = [_normalize_case(case) for case in module.build_cases(case_args)]
    if selected:
        cases = [case for case in cases if case.name in selected]
    if not cases:
        raise RuntimeError(f"no benchmark cases selected; requested={sorted(selected)}")
    return cases


def _freeze_manifest(
    *,
    cases: list[BenchmarkCase | BenchmarkPair],
    path: Path | None,
    campaign: Any,
) -> None:
    if path is None:
        return
    pairs = [case for case in cases if isinstance(case, BenchmarkPair)]
    if not pairs:
        raise RuntimeError("a workload manifest requires BenchmarkPair cases")
    manifest_cases = [
        {
            "name": pair.name,
            "shape": pair.shape,
            "dtype": pair.dtype,
            "bytes_moved": pair.bytes_moved,
            "flops": pair.flops,
            "metadata": pair.metadata,
            "required": pair.required,
            "headline": pair.headline,
        }
        for pair in pairs
    ]
    campaign.freeze_workload_manifest(
        path,
        campaign.workload_manifest(manifest_cases),
    )


def _run_pair(
    *,
    case: BenchmarkPair,
    args: argparse.Namespace,
    bench: Any,
) -> dict[str, Any]:
    if case.before is not None:
        case.before()
    try:
        try:
            correct, check_metadata = _run_check(case)
        except Exception as exc:
            return _pair_failure_row(
                case=case,
                label=args.label,
                correct=False,
                error=repr(exc),
            )

        metadata = {**case.metadata, **check_metadata, "label": args.label}
        if correct is False or (case.required and correct is not True):
            reason = (
                "required paired cases need a passing correctness check"
                if correct is None
                else "correctness check failed"
            )
            return _pair_failure_row(
                case=case,
                label=args.label,
                correct=correct,
                reason=reason,
                check_metadata=check_metadata,
            )

        baseline_times, candidate_times, inner_iterations, orders = (
            bench.paired_cuda_event_bench(
                case.baseline,
                case.candidate,
                warmup=args.warmup,
                trials=args.trials,
                target_sample_us=args.target_sample_us,
                inner_iterations_max=args.inner_iterations_max,
                flush_l2_mb=args.flush_l2_mb,
                seed=args.seed,
                prepare_trial=case.prepare_trial,
                before_sample=case.before_sample,
            )
        )
        baseline_stats = bench.summarize_times(
            name=case.name,
            shape=case.shape,
            dtype=case.dtype,
            times_ms=baseline_times,
            warmup=args.warmup,
            bytes_moved=case.bytes_moved,
            flops=case.flops,
            correct=correct,
            metadata={**metadata, "variant": "baseline"},
        )
        candidate_stats = bench.summarize_times(
            name=case.name,
            shape=case.shape,
            dtype=case.dtype,
            times_ms=candidate_times,
            warmup=args.warmup,
            bytes_moved=case.bytes_moved,
            flops=case.flops,
            correct=correct,
            metadata={**metadata, "variant": "candidate"},
        )
        speedup, delta_pct = _speedup(baseline_stats, candidate_stats)
        return {
            "type": "paired_bench",
            "name": case.name,
            "shape": case.shape,
            "dtype": case.dtype,
            "required": case.required,
            "headline": case.headline,
            "correct": correct,
            "baseline": asdict(baseline_stats),
            "candidate": asdict(candidate_stats),
            "baseline_samples_ms": baseline_times,
            "candidate_samples_ms": candidate_times,
            "inner_iterations": inner_iterations,
            "orders": orders,
            "speedup": speedup,
            "delta_pct": delta_pct,
            "metadata": metadata,
        }
    finally:
        if case.after is not None:
            case.after()


def _pair_failure_row(
    *,
    case: BenchmarkPair,
    label: str,
    correct: bool | None,
    reason: str | None = None,
    error: str | None = None,
    check_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "type": "paired_bench",
        "name": case.name,
        "shape": case.shape,
        "dtype": case.dtype,
        "required": case.required,
        "headline": case.headline,
        "correct": correct,
        "metadata": {
            **case.metadata,
            **(check_metadata or {}),
            "label": label,
        },
    }
    if reason is not None:
        row["reason"] = reason
    if error is not None:
        row["error"] = error
    return row


def _speedup(
    baseline_stats: Any,
    candidate_stats: Any,
) -> tuple[float | None, float | None]:
    if baseline_stats.median_ms <= 0 or candidate_stats.median_ms <= 0:
        return None, None
    speedup = baseline_stats.median_ms / candidate_stats.median_ms
    delta_pct = (candidate_stats.median_ms / baseline_stats.median_ms - 1.0) * 100.0
    return speedup, delta_pct


def _run_single_case(
    *,
    case: BenchmarkCase,
    args: argparse.Namespace,
    bench: Any,
    torch: Any,
) -> dict[str, Any]:
    if case.before is not None:
        case.before()
    try:
        case.run()
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        correct, check_metadata = _run_check(case)
        stats = bench.summarize_times(
            name=case.name,
            shape=case.shape,
            dtype=case.dtype,
            times_ms=bench.cuda_event_bench(
                case.run,
                warmup=args.warmup,
                repeat=args.repeat,
                flush_l2_mb=args.flush_l2_mb,
            ),
            warmup=args.warmup,
            bytes_moved=case.bytes_moved,
            flops=case.flops,
            correct=correct,
            metadata={**case.metadata, **check_metadata, "label": args.label},
        )
        return {"type": "bench", **asdict(stats)}
    finally:
        if case.after is not None:
            case.after()


def _record_row(out: str | Path, row: dict[str, Any]) -> None:
    _append_jsonl(out, row)
    print(json.dumps(row, sort_keys=True), flush=True)


def _finish_pairs(
    *,
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    campaign: Any,
) -> None:
    if not rows:
        return
    decision = campaign.decide_paired_results(
        rows,
        minimum_gain_pct=args.minimum_gain_pct,
        regression_pct=args.regression_pct,
    )
    _record_row(args.out, {"type": "decision", **decision})
    if args.decision_out is not None:
        args.decision_out.parent.mkdir(parents=True, exist_ok=True)
        args.decision_out.write_text(
            json.dumps(decision, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.report_out is not None:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(
            campaign.paired_report(rows, decision),
            encoding="utf-8",
        )
    if args.fail_on_reject and decision["status"] == "rejected":
        raise SystemExit(1)


def main() -> None:
    args, case_args = _base_parser().parse_known_args()
    if case_args and case_args[0] == "--":
        case_args = case_args[1:]

    metadata = {
        "type": "metadata",
        "label": args.label,
        "case_file": str(Path(args.case_file).resolve()),
        "warmup": args.warmup,
        "repeat": args.repeat,
        "trials": args.trials,
        "target_sample_us": args.target_sample_us,
        "inner_iterations_max": args.inner_iterations_max,
        "flush_l2_mb": args.flush_l2_mb,
        "profile_variant": args.profile_variant,
        "profile_warmup": args.profile_warmup,
        **_repo_metadata(),
    }
    _record_row(args.out, metadata)
    if args.metadata_only:
        return

    import kernel_bench_utils as bench
    import kernel_campaign_utils as campaign
    import torch

    if args.seed >= 0:
        torch.manual_seed(args.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(args.seed)

    cases = _load_cases(args, case_args)
    if args.profile_variant is not None:
        _run_profile_launch(
            cases=cases,
            variant=args.profile_variant,
            warmup=args.profile_warmup,
            out=args.out,
            label=args.label,
            torch=torch,
        )
        return

    _freeze_manifest(
        cases=cases,
        path=args.workload_manifest,
        campaign=campaign,
    )
    paired_rows = []
    for case in cases:
        if isinstance(case, BenchmarkPair):
            row = _run_pair(case=case, args=args, bench=bench)
            paired_rows.append(row)
        else:
            row = _run_single_case(case=case, args=args, bench=bench, torch=torch)
        _record_row(args.out, row)
    _finish_pairs(rows=paired_rows, args=args, campaign=campaign)


def _run_profile_launch(
    *,
    cases: list[BenchmarkCase | BenchmarkPair],
    variant: str,
    warmup: int,
    out: str | Path,
    label: str,
    torch: Any,
) -> None:
    if len(cases) != 1 or not isinstance(cases[0], BenchmarkPair):
        raise RuntimeError(
            "profile mode requires exactly one selected BenchmarkPair; use --case"
        )
    if warmup < 0:
        raise RuntimeError("profile-warmup must be non-negative")

    case = cases[0]
    run = case.baseline if variant == "baseline" else case.candidate
    if case.before is not None:
        case.before()
    try:
        for _ in range(warmup):
            run()
        torch.cuda.synchronize()
        run()
        torch.cuda.synchronize()
    finally:
        if case.after is not None:
            case.after()

    row = {
        "type": "profile_launch",
        "name": case.name,
        "shape": case.shape,
        "dtype": case.dtype,
        "variant": variant,
        "warmup": warmup,
        "metadata": {**case.metadata, "label": label},
    }
    _append_jsonl(out, row)
    print(json.dumps(row, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
