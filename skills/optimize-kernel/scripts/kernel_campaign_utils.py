#!/usr/bin/env python3
"""Dependency-free helpers for paired kernel benchmark campaigns."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


def geometric_mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values or any(value <= 0 for value in values):
        raise ValueError("geometric mean requires positive values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def workload_manifest(cases: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {"schema_version": 1, "cases": cases}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {
        **payload,
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def freeze_workload_manifest(path: Path, current: dict[str, Any]) -> None:
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved != current:
            raise RuntimeError(
                f"workload manifest changed: {path}; use a new campaign directory "
                "or delete prior results and the manifest before remeasuring"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def decide_paired_results(
    rows: list[dict[str, Any]],
    *,
    minimum_gain_pct: float,
    regression_pct: float,
) -> dict[str, Any]:
    paired = [row for row in rows if row.get("type") == "paired_bench"]
    if not paired:
        return {
            "status": "rejected",
            "reason": "no paired benchmark rows",
            "minimum_gain_pct": minimum_gain_pct,
            "regression_pct": regression_pct,
        }

    correctness_failures = [
        str(row.get("name"))
        for row in paired
        if row.get("required", True) and row.get("correct") is not True
    ]
    regressions = [
        str(row.get("name"))
        for row in paired
        if row.get("required", True)
        and row.get("delta_pct") is not None
        and float(row["delta_pct"]) > regression_pct
    ]
    headline = [
        row
        for row in paired
        if row.get("headline", True)
        and row.get("correct") is True
        and row.get("speedup") is not None
    ]

    speedup = (
        geometric_mean(float(row["speedup"]) for row in headline) if headline else None
    )
    gain_pct = (speedup - 1.0) * 100.0 if speedup is not None else None

    status = "inconclusive"
    reason = "candidate gain is below the promotion threshold"
    if correctness_failures:
        status = "rejected"
        reason = "required correctness checks failed"
    elif regressions:
        status = "rejected"
        reason = "required workload regression exceeded the limit"
    elif not headline:
        status = "rejected"
        reason = "no correct headline workloads"
    elif gain_pct is not None and gain_pct >= minimum_gain_pct:
        status = "accepted"
        reason = "headline geometric-mean gain met the promotion threshold"

    return {
        "status": status,
        "reason": reason,
        "minimum_gain_pct": minimum_gain_pct,
        "regression_pct": regression_pct,
        "geomean_speedup": speedup,
        "gain_pct": gain_pct,
        "headline_cases": [str(row.get("name")) for row in headline],
        "correctness_failures": correctness_failures,
        "regressions": regressions,
    }


def paired_report(
    rows: list[dict[str, Any]],
    decision: dict[str, Any],
) -> str:
    lines = [
        "| Case | Shape | DType | Baseline median ms | Candidate median ms | "
        "Speedup | Delta | Correct |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        if row.get("type") != "paired_bench":
            continue
        baseline = row.get("baseline") or {}
        candidate = row.get("candidate") or {}
        speedup = row.get("speedup")
        delta_pct = row.get("delta_pct")
        lines.append(
            "| "
            f"{_cell(row.get('name'))} | "
            f"{_cell(row.get('shape'))} | "
            f"{_cell(row.get('dtype'))} | "
            f"{_number(baseline.get('median_ms'))} | "
            f"{_number(candidate.get('median_ms'))} | "
            f"{_speedup(speedup)} | "
            f"{_signed_percent(delta_pct)} | "
            f"{_cell(row.get('correct'))} |"
        )

    lines.extend(
        [
            "",
            f"Decision: **{decision.get('status', 'unknown')}**",
            "",
            str(decision.get("reason", "")),
        ]
    )
    speedup = decision.get("geomean_speedup")
    if speedup is not None:
        lines.extend(["", f"Headline geometric-mean speedup: `{float(speedup):.4f}x`"])
    return "\n".join(lines) + "\n"


def _cell(value: Any) -> str:
    return str("" if value is None else value).replace("|", "\\|").replace("\n", "<br>")


def _number(value: Any) -> str:
    return "" if value is None else f"{float(value):.4f}"


def _speedup(value: Any) -> str:
    return "" if value is None else f"{float(value):.4f}x"


def _signed_percent(value: Any) -> str:
    return "" if value is None else f"{float(value):+.2f}%"
