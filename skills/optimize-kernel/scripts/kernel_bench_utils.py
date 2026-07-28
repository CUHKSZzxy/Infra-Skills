#!/usr/bin/env python3
"""Small helpers for LMDeploy CUDA/Triton kernel microbenchmarks.

Import this from ad hoc benchmark files instead of rewriting timing, device
metadata, and JSONL result handling for every kernel experiment.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import torch


@dataclass
class BenchStats:
    name: str
    shape: str
    dtype: str
    device: str
    repeat: int
    warmup: int
    mean_ms: float
    median_ms: float
    p20_ms: float
    p80_ms: float
    min_ms: float
    max_ms: float
    bytes: int | None = None
    gbps: float | None = None
    tflops: float | None = None
    correct: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def cuda_device_summary(
    device: int | str | torch.device | None = None,
) -> dict[str, Any]:
    """Return enough device info to make benchmark artifacts comparable."""
    if not torch.cuda.is_available():
        return {
            "cuda_available": False,
            "python": platform.python_version(),
            "torch": torch.__version__,
        }
    dev = torch.device("cuda" if device is None else device)
    props = torch.cuda.get_device_properties(dev)
    return {
        "cuda_available": True,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "device_index": torch.cuda.current_device(),
        "device_name": props.name,
        "capability": f"{props.major}.{props.minor}",
        "sm_count": props.multi_processor_count,
        "total_memory_gb": round(props.total_memory / 1024**3, 2),
    }


def sync() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def flush_l2(size_mb: int = 256, device: str = "cuda") -> torch.Tensor:
    """Touch a temporary tensor to reduce cross-candidate cache luck.

    Use only when measuring memory-bound kernels and when the extra allocation
    fits comfortably. Keep disabled for normal quick iteration.
    """
    if size_mb <= 0:
        return torch.empty(0, device=device)
    count = size_mb * 1024 * 1024 // 4
    buf = torch.empty(count, dtype=torch.float32, device=device)
    buf.fill_(1.0)
    sync()
    return buf


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[index]


def cuda_event_bench(
    fn: Callable[[], Any],
    *,
    warmup: int = 25,
    repeat: int = 100,
    flush_l2_mb: int = 0,
) -> list[float]:
    """Measure one CUDA callable with CUDA events and return per-iter ms."""
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    for _ in range(warmup):
        fn()
    sync()

    times: list[float] = []
    for _ in range(repeat):
        if flush_l2_mb:
            flush_l2(flush_l2_mb)
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        fn()
        end.record()
        end.synchronize()
        times.append(float(start.elapsed_time(end)))
    return times


def summarize_times(
    *,
    name: str,
    shape: str,
    dtype: str,
    times_ms: Iterable[float],
    warmup: int,
    bytes_moved: int | None = None,
    flops: int | None = None,
    correct: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> BenchStats:
    times = list(times_ms)
    mean_ms = statistics.fmean(times)
    gbps = None
    if bytes_moved is not None and mean_ms > 0:
        gbps = bytes_moved / (mean_ms * 1e-3) / 1e9
    tflops = None
    if flops is not None and mean_ms > 0:
        tflops = flops / (mean_ms * 1e-3) / 1e12
    return BenchStats(
        name=name,
        shape=shape,
        dtype=dtype,
        device=cuda_device_summary().get("device_name", "cuda"),
        repeat=len(times),
        warmup=warmup,
        mean_ms=mean_ms,
        median_ms=statistics.median(times),
        p20_ms=percentile(times, 0.20),
        p80_ms=percentile(times, 0.80),
        min_ms=min(times),
        max_ms=max(times),
        bytes=bytes_moved,
        gbps=gbps,
        tflops=tflops,
        correct=correct,
        metadata=metadata or {},
    )


def append_jsonl(path: str | Path, row: BenchStats | dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(row) if isinstance(row, BenchStats) else row
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True))
        f.write("\n")


def close_report(actual: torch.Tensor, expected: torch.Tensor) -> dict[str, float]:
    diff = (actual.float() - expected.float()).abs()
    denom = expected.float().abs().clamp_min(1e-12)
    rel = diff / denom
    return {
        "max_abs": float(diff.max().item()),
        "mean_abs": float(diff.mean().item()),
        "max_rel": float(rel.max().item()),
        "mean_rel": float(rel.mean().item()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print CUDA device benchmark metadata."
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args()
    summary = cuda_device_summary()
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
