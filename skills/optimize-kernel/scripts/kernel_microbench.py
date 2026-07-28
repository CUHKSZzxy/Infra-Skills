#!/usr/bin/env python3
"""Generic CUDA-event runner for LMDeploy kernel microbench cases.

Write a small case file that defines ``build_cases(args)`` and returns
``BenchmarkCase`` objects. This runner handles warmup, timing, correctness
hooks, metadata, and JSONL output so kernel experiments share one measurement
loop.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
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


def _repo_metadata() -> dict[str, Any]:
    meta: dict[str, Any] = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
    }
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
    except Exception as exc:
        meta["lmdeploy_error"] = repr(exc)
    for key, cmd in {
        "git_commit": ["git", "rev-parse", "HEAD"],
        "git_branch": ["git", "branch", "--show-current"],
    }.items():
        try:
            meta[key] = subprocess.check_output(cmd, text=True).strip()
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


def _normalize_case(case: BenchmarkCase | dict[str, Any]) -> BenchmarkCase:
    if isinstance(case, BenchmarkCase):
        return case
    return BenchmarkCase(**case)


def _run_check(case: BenchmarkCase) -> tuple[bool | None, dict[str, Any]]:
    if case.check is None:
        return None, {}
    result = case.check()
    if result is None:
        return None, {}
    if isinstance(result, bool):
        return result, {}
    correct = result.pop("correct", True)
    return bool(correct), result


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
    parser.add_argument("--flush-l2-mb", type=int, default=0)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--metadata-only", action="store_true")
    return parser


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
        "flush_l2_mb": args.flush_l2_mb,
        **_repo_metadata(),
    }
    _append_jsonl(args.out, metadata)
    print(json.dumps(metadata, sort_keys=True), flush=True)
    if args.metadata_only:
        return

    import torch
    from kernel_bench_utils import cuda_event_bench, summarize_times

    if args.seed >= 0:
        torch.manual_seed(args.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(args.seed)

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

    for case in cases:
        if case.before is not None:
            case.before()
        case.run()
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        correct, check_metadata = _run_check(case)
        metadata = {**case.metadata, **check_metadata, "label": args.label}
        times = cuda_event_bench(
            case.run,
            warmup=args.warmup,
            repeat=args.repeat,
            flush_l2_mb=args.flush_l2_mb,
        )
        stats = summarize_times(
            name=case.name,
            shape=case.shape,
            dtype=case.dtype,
            times_ms=times,
            warmup=args.warmup,
            bytes_moved=case.bytes_moved,
            flops=case.flops,
            correct=correct,
            metadata=metadata,
        )
        row = {"type": "bench", **stats.__dict__}
        _append_jsonl(args.out, row)
        print(json.dumps(row, sort_keys=True), flush=True)
        if case.after is not None:
            case.after()


if __name__ == "__main__":
    main()
