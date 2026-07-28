#!/usr/bin/env python3
"""Compare two JSONL kernel benchmark result files.

Rows should contain at least `name`, `shape`, and `mean_ms`. This accepts the
output schema produced by `kernel_bench_utils.BenchStats`.
"""

from __future__ import annotations

import argparse
import json
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


def best_by_key(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        try:
            mean_ms = float(row["mean_ms"])
        except (KeyError, TypeError, ValueError):
            continue
        item_key = key(row)
        if item_key not in best or mean_ms < float(best[item_key]["mean_ms"]):
            best[item_key] = row
    return best


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

    baseline = best_by_key(load_jsonl(args.baseline))
    candidate = best_by_key(load_jsonl(args.candidate))
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
                f"| {cell(name)} | {cell(shape)} | {cell(dtype)} | | {cell(cand.get('mean_ms'))} | | new | |"
            )
            continue
        if cand is None:
            failures += 1
            print(
                f"| {cell(name)} | {cell(shape)} | {cell(dtype)} | {cell(base.get('mean_ms'))} | | | missing | |"
            )
            continue
        base_ms = float(base["mean_ms"])
        cand_ms = float(cand["mean_ms"])
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
        print(
            f"| {cell(name)} | {cell(shape)} | {cell(dtype)} | "
            f"{base_ms:.4f} | {cand_ms:.4f} | {delta_pct:+.2f}% | "
            f"{status} | {cell(', '.join(notes))} |"
        )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
