#!/usr/bin/env python3
"""Compare two JSONL kernel benchmark result files.

Rows should contain `name`, `shape`, and `median_ms` or `mean_ms`. Repeated rows
are aggregated by their median instead of selecting the fastest observation.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise SystemExit(f"{path}:{line_no}: expected object row")
            rows.append(row)
    return rows


def key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("name", "")),
        str(row.get("shape", "")),
        str(row.get("dtype", "")),
    )


def aggregate_by_key(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        try:
            _timing_value(row)
        except (KeyError, TypeError, ValueError):
            continue
        grouped.setdefault(key(row), []).append(row)

    aggregated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item_key, items in grouped.items():
        result = dict(items[-1])
        result["median_ms"] = statistics.median(_timing_value(row) for row in items)
        correctness = [row.get("correct") for row in items]
        if any(value is False for value in correctness):
            result["correct"] = False
        elif correctness and all(value is True for value in correctness):
            result["correct"] = True
        else:
            result["correct"] = None
        result["run_count"] = len(items)
        aggregated[item_key] = result
    return aggregated


def _timing_value(row: dict[str, Any]) -> float:
    value = row.get("median_ms", row.get("mean_ms"))
    if value is None:
        raise KeyError("median_ms")
    return float(value)


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def cell(value: Any, digits: int = 3) -> str:
    return fmt(value, digits).replace("|", "\\|").replace("\n", "<br>")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument(
        "--regression-pct",
        type=float,
        default=3.0,
        help="mark rows slower than this percentage as regressions",
    )
    args = parser.parse_args()

    baseline = aggregate_by_key(load_jsonl(args.baseline))
    candidate = aggregate_by_key(load_jsonl(args.candidate))
    all_keys = sorted(set(baseline) | set(candidate))

    print(
        "| Kernel | Shape | DType | Baseline ms | Candidate ms | Delta | Status | Notes |"
    )
    print("| --- | --- | --- | ---: | ---: | ---: | --- | --- |")
    failures = 0
    for item_key in all_keys:
        base = baseline.get(item_key)
        cand = candidate.get(item_key)
        name, shape, dtype = item_key
        if base is None:
            print(
                f"| {cell(name)} | {cell(shape)} | {cell(dtype)} | | {cell(cand.get('median_ms'))} | | new | |"
            )
            continue
        if cand is None:
            failures += 1
            print(
                f"| {cell(name)} | {cell(shape)} | {cell(dtype)} | {cell(base.get('median_ms'))} | | | missing | |"
            )
            continue
        base_ms = float(base["median_ms"])
        cand_ms = float(cand["median_ms"])
        delta_pct = (cand_ms / base_ms - 1.0) * 100.0 if base_ms else 0.0
        correct = cand.get("correct")
        status = "ok"
        notes = []
        if correct is False:
            status = "incorrect"
            failures += 1
        elif delta_pct > args.regression_pct:
            status = "regression"
            failures += 1
        elif delta_pct < -args.regression_pct:
            status = "faster"
        if correct is not None:
            notes.append(f"correct={correct}")
        if cand.get("gbps") is not None:
            notes.append(f"GB/s={float(cand['gbps']):.1f}")
        if cand.get("tflops") is not None:
            notes.append(f"TFLOP/s={float(cand['tflops']):.1f}")
        if cand.get("run_count", 1) > 1:
            notes.append(f"runs={cand['run_count']}")
        print(
            f"| {cell(name)} | {cell(shape)} | {cell(dtype)} | "
            f"{base_ms:.4f} | {cand_ms:.4f} | {delta_pct:+.2f}% | "
            f"{status} | {cell(', '.join(notes))} |"
        )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
