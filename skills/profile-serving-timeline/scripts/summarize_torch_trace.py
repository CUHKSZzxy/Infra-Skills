#!/usr/bin/env python3
"""Summarize steady cycles in PyTorch Chrome traces.

The script accepts uncompressed ``.json`` and gzip-compressed ``.json.gz``
traces. It uses a user-supplied annotation regex as the cycle anchor, groups
duplicate GPU annotations by external ID, and restricts kernel accounting to
complete start-to-start cycle windows so profiler-boundary events do not
dominate the result.
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def percentile(values: list[float], q: float) -> float | None:
    """Return a linearly interpolated percentile."""
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - pos) + ordered[high] * (pos - low)


def stats_ms(values_us: list[float]) -> dict[str, float] | None:
    """Return compact duration statistics in milliseconds."""
    if not values_us:
        return None
    return {
        "min": min(values_us) / 1000,
        "median": statistics.median(values_us) / 1000,
        "mean": statistics.mean(values_us) / 1000,
        "p95": percentile(values_us, 0.95) / 1000,
        "max": max(values_us) / 1000,
    }


def expand_inputs(items: list[str]) -> list[Path]:
    """Expand files, directories, and quoted glob patterns."""
    found: list[Path] = []
    for item in items:
        path = Path(item)
        if path.is_dir():
            found.extend(sorted(path.glob("*.json")))
            found.extend(sorted(path.glob("*.json.gz")))
            continue
        matches = sorted(Path(match) for match in glob.glob(item))
        if matches:
            found.extend(matches)
        elif path.is_file():
            found.append(path)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in found:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    if not unique:
        raise ValueError("no .json or .json.gz trace files matched")
    return unique


def load_trace(path: Path) -> dict[str, Any]:
    """Load one JSON or JSON-gzip trace."""
    with open(path, "rb") as raw_handle:
        is_gzip = raw_handle.read(2) == b"\x1f\x8b"
    opener = gzip.open if is_gzip else open
    with opener(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data.get("traceEvents"), list):
        raise ValueError(f"{path}: missing traceEvents list")
    return data


def complete_events(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return duration-bearing complete events."""
    return [
        event
        for event in data["traceEvents"]
        if event.get("ph") == "X"
        and isinstance(event.get("ts"), (int, float))
        and isinstance(event.get("dur"), (int, float))
    ]


def choose_step_events(
    events: list[dict[str, Any]],
    pattern: re.Pattern[str],
    category: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Select and deduplicate step annotations."""
    matches = [
        event
        for event in events
        if pattern.search(str(event.get("name", "")))
        and event.get("cat") in {"gpu_user_annotation", "user_annotation"}
    ]
    if category == "auto":
        selected_category = (
            "gpu_user_annotation"
            if any(event.get("cat") == "gpu_user_annotation" for event in matches)
            else "user_annotation"
        )
    else:
        selected_category = category
    selected = [event for event in matches if event.get("cat") == selected_category]
    if not selected:
        names = Counter(
            str(event.get("name", ""))
            for event in events
            if event.get("cat") in {"gpu_user_annotation", "user_annotation"}
        )
        examples = ", ".join(name for name, _ in names.most_common(12))
        raise ValueError(
            f"no {selected_category} annotation matched {pattern.pattern!r}; "
            f"available examples: {examples}"
        )

    # vLLM can emit one annotation on each GPU stream for the same external
    # operation. Retain the longest range for each (name, External id) pair.
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, event in enumerate(selected):
        external_id = event.get("args", {}).get("External id")
        key = (
            (str(event.get("name", "")), external_id)
            if external_id is not None
            else (str(event.get("name", "")), event["ts"], index)
        )
        previous = deduped.get(key)
        if previous is None or event["dur"] > previous["dur"]:
            deduped[key] = event
    return selected_category, sorted(deduped.values(), key=lambda event: event["ts"])


def clipped_interval(
    event: dict[str, Any], lower: float, upper: float
) -> tuple[float, float] | None:
    """Clip an event to the analysis window."""
    start = max(float(event["ts"]), lower)
    end = min(float(event["ts"] + event["dur"]), upper)
    return (start, end) if end > start else None


def merge_intervals(intervals: list[tuple[float, float]]) -> list[list[float]]:
    """Merge overlapping intervals."""
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return merged


def parse_groups(items: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    """Parse ordered NAME=REGEX kernel groups."""
    groups: list[tuple[str, re.Pattern[str]]] = []
    names: set[str] = set()
    for item in items:
        name, separator, expression = item.partition("=")
        if not separator or not name or not expression:
            raise ValueError(f"invalid --group {item!r}; expected NAME=REGEX")
        if name == "other":
            raise ValueError("'other' is reserved as the unmatched group")
        if name in names:
            raise ValueError(f"duplicate group name: {name}")
        names.add(name)
        groups.append((name, re.compile(expression)))
    return groups


def trace_summary(
    path: Path,
    step_pattern: re.Pattern[str],
    annotation_category: str,
    trim_first: int,
    trim_last: int,
    top: int,
    groups: list[tuple[str, re.Pattern[str]]],
) -> dict[str, Any]:
    """Summarize one trace."""
    data = load_trace(path)
    events = complete_events(data)
    selected_category, steps = choose_step_events(
        events, step_pattern, annotation_category
    )

    first_cycle = trim_first
    cycle_stop = len(steps) - 1 - trim_last
    if first_cycle < 0 or trim_last < 0:
        raise ValueError("trim values must be nonnegative")
    if cycle_stop <= first_cycle:
        raise ValueError(
            f"{path}: {len(steps)} matched steps leave no complete cycles "
            f"after trim-first={trim_first}, trim-last={trim_last}"
        )

    cycle_starts = steps[first_cycle:cycle_stop]
    cycle_ends = steps[first_cycle + 1 : cycle_stop + 1]
    periods_us = [
        end["ts"] - start["ts"] for start, end in zip(cycle_starts, cycle_ends)
    ]
    forward_us = [float(event["dur"]) for event in cycle_starts]
    lower = float(cycle_starts[0]["ts"])
    upper = float(cycle_ends[-1]["ts"])
    cycles = len(cycle_starts)

    kernels: list[tuple[str, float, dict[str, Any]]] = []
    busy_intervals: list[tuple[float, float]] = []
    for event in events:
        interval = clipped_interval(event, lower, upper)
        if interval is None:
            continue
        category = event.get("cat")
        if category in {"kernel", "gpu_memcpy", "gpu_memset"}:
            busy_intervals.append(interval)
        if category == "kernel":
            kernels.append((str(event.get("name", "")), interval[1] - interval[0], event))

    total_kernel_us = sum(duration for _, duration, _ in kernels)
    kernel_totals: dict[str, float] = defaultdict(float)
    kernel_calls: Counter[str] = Counter()
    for name, duration, _ in kernels:
        kernel_totals[name] += duration
        kernel_calls[name] += 1

    top_kernels = []
    for name, duration in sorted(kernel_totals.items(), key=lambda item: -item[1])[:top]:
        top_kernels.append(
            {
                "name": name,
                "ms_per_cycle": duration / cycles / 1000,
                "calls_per_cycle": kernel_calls[name] / cycles,
                "share_of_summed_kernel_percent": (
                    duration / total_kernel_us * 100 if total_kernel_us else 0.0
                ),
            }
        )

    group_output: dict[str, dict[str, float]] = {}
    if groups:
        group_duration: dict[str, float] = defaultdict(float)
        group_calls: Counter[str] = Counter()
        for kernel_name, duration, _ in kernels:
            owner = "other"
            for group_name, expression in groups:
                if expression.search(kernel_name):
                    owner = group_name
                    break
            group_duration[owner] += duration
            group_calls[owner] += 1
        for name in [group[0] for group in groups] + ["other"]:
            duration = group_duration[name]
            group_output[name] = {
                "ms_per_cycle": duration / cycles / 1000,
                "calls_per_cycle": group_calls[name] / cycles,
                "share_of_summed_kernel_percent": (
                    duration / total_kernel_us * 100 if total_kernel_us else 0.0
                ),
            }

    merged = merge_intervals(busy_intervals)
    busy_us = sum(end - start for start, end in merged)
    gaps: list[float] = []
    cursor = lower
    for start, end in merged:
        if start > cursor:
            gaps.append(start - cursor)
        cursor = max(cursor, end)
    if cursor < upper:
        gaps.append(upper - cursor)

    all_graph_launches = [
        event
        for event in events
        if event.get("cat") == "cuda_runtime"
        and event.get("name") == "cudaGraphLaunch"
    ]
    graph_launches = [
        event for event in all_graph_launches if lower <= event["ts"] < upper
    ]
    graph_correlations = {
        event.get("args", {}).get("correlation")
        for event in all_graph_launches
        if event.get("args", {}).get("correlation") is not None
    }
    graph_child_count = sum(
        1
        for _, _, event in kernels
        if event.get("args", {}).get("correlation") in graph_correlations
    )

    distributed = data.get("distributedInfo") or {}
    rank = distributed.get("rank")
    if rank is None:
        match = re.search(r"rank[_\[]?(\d+)", path.name)
        rank = int(match.group(1)) if match else None
    devices = sorted(
        {
            event.get("args", {}).get("device")
            for _, _, event in kernels
            if event.get("args", {}).get("device") is not None
        },
        key=str,
    )

    return {
        "file": str(path),
        "rank": rank,
        "world_size": distributed.get("world_size"),
        "reported_kernel_devices": devices,
        "annotation_category": selected_category,
        "matched_step_count": len(steps),
        "complete_cycle_count": cycles,
        "forward_ms": stats_ms(forward_us),
        "cycle_ms": stats_ms(periods_us),
        "analysis_window_ms": (upper - lower) / 1000,
        "kernel_sum_ms_per_cycle": total_kernel_us / cycles / 1000,
        "kernel_nodes_per_cycle": len(kernels) / cycles,
        "graph_launches_per_cycle": len(graph_launches) / cycles,
        "graph_child_kernel_nodes_per_cycle": graph_child_count / cycles,
        "gpu_busy_union_percent": busy_us / (upper - lower) * 100,
        "max_all_stream_idle_gap_us": max(gaps, default=0.0),
        "groups": group_output,
        "top_kernels": top_kernels,
    }


def spread(rows: list[dict[str, Any]], path: tuple[str, ...]) -> dict[str, Any] | None:
    """Calculate cross-trace spread for one numeric field."""
    pairs: list[tuple[Any, float]] = []
    for row in rows:
        current: Any = row
        for key in path:
            current = current.get(key) if isinstance(current, dict) else None
        if isinstance(current, (int, float)):
            pairs.append((row["rank"], float(current)))
    if not pairs:
        return None
    values = [value for _, value in pairs]
    mean = statistics.mean(values)
    minimum = min(values)
    maximum = max(values)
    return {
        "min": minimum,
        "min_ranks": [
            rank for rank, value in pairs if math.isclose(value, minimum)
        ],
        "max": maximum,
        "max_ranks": [
            rank for rank, value in pairs if math.isclose(value, maximum)
        ],
        "mean": mean,
        "max_minus_min": maximum - minimum,
        "spread_percent_of_mean": (
            (maximum - minimum) / mean * 100 if mean else 0.0
        ),
        "population_cv_percent": (
            statistics.pstdev(values) / mean * 100 if mean else 0.0
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize complete cycles in PyTorch Chrome traces."
    )
    parser.add_argument("traces", nargs="+", help="Trace files, directories, or globs")
    parser.add_argument(
        "--step-regex",
        required=True,
        help="Regex matching the GPU/CPU annotation used as the cycle anchor",
    )
    parser.add_argument(
        "--annotation-category",
        choices=("auto", "gpu_user_annotation", "user_annotation"),
        default="auto",
        help="Prefer GPU annotations automatically, or force one category",
    )
    parser.add_argument(
        "--trim-first",
        type=int,
        default=1,
        help="Number of leading matched steps to exclude (default: 1)",
    )
    parser.add_argument(
        "--trim-last",
        type=int,
        default=0,
        help="Number of additional trailing complete cycles to exclude (default: 0)",
    )
    parser.add_argument("--top", type=int, default=20, help="Top kernel names per trace")
    parser.add_argument(
        "--group",
        action="append",
        default=[],
        metavar="NAME=REGEX",
        help="Ordered, non-overlapping kernel group; repeat as needed",
    )
    parser.add_argument("--output", type=Path, help="Write JSON here instead of stdout")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        paths = expand_inputs(args.traces)
        groups = parse_groups(args.group)
        step_pattern = re.compile(args.step_regex)
        rows = [
            trace_summary(
                path,
                step_pattern,
                args.annotation_category,
                args.trim_first,
                args.trim_last,
                args.top,
                groups,
            )
            for path in paths
        ]
    except (OSError, ValueError, json.JSONDecodeError, re.error) as error:
        parser.error(str(error))

    rows.sort(key=lambda row: (row["rank"] is None, row["rank"], row["file"]))
    result = {
        "method": {
            "duration_unit": "PyTorch Chrome trace microseconds",
            "step_regex": args.step_regex,
            "annotation_category": args.annotation_category,
            "trim_first": args.trim_first,
            "trim_last": args.trim_last,
            "kernel_window": "complete consecutive step-start intervals only",
            "kernel_groups": "ordered first-match ownership",
        },
        "traces": rows,
        "cross_trace_spread": {
            "median_forward_ms": spread(rows, ("forward_ms", "median")),
            "median_cycle_ms": spread(rows, ("cycle_ms", "median")),
            "kernel_sum_ms_per_cycle": spread(rows, ("kernel_sum_ms_per_cycle",)),
            "kernel_nodes_per_cycle": spread(rows, ("kernel_nodes_per_cycle",)),
        },
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
