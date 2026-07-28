#!/usr/bin/env python3
"""Collect serving benchmark logs into CSV summaries and comparison plots."""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

METRIC_PATTERNS = {
    "request_throughput_req_s": re.compile(
        r"Request throughput \(req/s\):\s*([0-9.]+)"
    ),
    "output_throughput_tok_s": re.compile(
        r"Output token throughput \(tok/s\):\s*([0-9.]+)"
    ),
    "total_throughput_tok_s": re.compile(
        r"Total Token throughput \(tok/s\):\s*([0-9.]+)"
    ),
    "mean_ttft_ms": re.compile(r"Mean TTFT \(ms\):\s*([0-9.]+)"),
    "mean_tpot_ms": re.compile(r"Mean TPOT \(ms\):\s*([0-9.]+)"),
    "mean_itl_ms": re.compile(r"Mean ITL \(ms\):\s*([0-9.]+)"),
}

HIGHER_BETTER = {
    "request_throughput_req_s",
    "output_throughput_tok_s",
    "total_throughput_tok_s",
}

FILENAME_RE = re.compile(
    r"^(?P<stamp>\d{6}_\d{6})_(?P<prefix>.+)_(?P<dataset>[^_]+)_out_"
    r"(?P<out_len>None|\d+)_prompts_(?P<num_prompts>\d+)\.log$"
)

EXPECTED_WORKLOADS = {
    "fast": {
        "None": 1000,
        "2048": 1000,
    },
    "medium": {
        "None": 1000,
        "2048": 1000,
        "4096": 500,
        "8192": 200,
    },
    "full": {
        "None": 10000,
        "2048": 8000,
        "4096": 8000,
        "8192": 4000,
        "16384": 1000,
        "32768": 500,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--baseline-group", default="baseline")
    parser.add_argument("--candidate-group", default="kvfp8")
    parser.add_argument("--baseline-label", default="Baseline")
    parser.add_argument("--candidate-label", default="Candidate")
    parser.add_argument(
        "--expected-workload",
        choices=("none", "fast", "medium", "full"),
        default="none",
        help="Optionally keep only a known ShareGPT workload matrix.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip matplotlib plots even when available.",
    )
    return parser.parse_args()


def parse_feature_group(prefix: str) -> str:
    """Derive a stable comparison group from the filename prefix."""
    parts = prefix.split("_")
    for idx, part in enumerate(parts):
        if part.startswith("kv") and len(part) > 2:
            return "_".join(parts[idx:])
    feature_match = re.search(r"(?:^|_)feature-([^_]+)", prefix)
    if feature_match:
        return feature_match.group(1)
    return "baseline"


def out_len_sort_key(out_len: str) -> int:
    return -1 if out_len == "None" else int(out_len)


def x_label(out_len: str, num_prompts: int) -> str:
    labels = {
        "None": "-",
        "2048": "2k",
        "4096": "4k",
        "8192": "8k",
        "16384": "16k",
        "32768": "32k",
    }
    return f"{labels.get(out_len, out_len)}\n({num_prompts})"


def parse_log(path: Path) -> dict[str, object] | None:
    match = FILENAME_RE.match(path.name)
    if not match:
        return None

    text = path.read_text(errors="replace")
    row: dict[str, object] = match.groupdict()
    row["file"] = str(path)
    row["feature_group"] = parse_feature_group(str(row["prefix"]))
    row["out_len_sort"] = out_len_sort_key(str(row["out_len"]))
    row["num_prompts"] = int(str(row["num_prompts"]))

    for key, pattern in METRIC_PATTERNS.items():
        metric_match = pattern.search(text)
        row[key] = float(metric_match.group(1)) if metric_match else ""
    return row


def filter_expected_workload(
    rows: list[dict[str, object]], name: str
) -> list[dict[str, object]]:
    if name == "none":
        return rows
    expected = EXPECTED_WORKLOADS[name]
    return [
        row
        for row in rows
        if expected.get(str(row["out_len"])) == int(row["num_prompts"])
    ]


def keep_latest_per_case(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    latest: dict[tuple[str, str, int, str], dict[str, object]] = {}
    for row in sorted(rows, key=lambda item: str(item["stamp"])):
        key = (
            str(row["dataset"]),
            str(row["out_len"]),
            int(row["num_prompts"]),
            str(row["feature_group"]),
        )
        latest[key] = row
    return list(latest.values())


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    metric_keys = list(METRIC_PATTERNS)
    fieldnames = [
        "stamp",
        "dataset",
        "out_len",
        "num_prompts",
        "feature_group",
        "prefix",
        *metric_keys,
        "file",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_pairwise_csv(rows: list[dict[str, object]], path: Path, metric: str) -> None:
    grouped: dict[tuple[str, str, int], dict[str, object]] = {}
    for row in rows:
        key = (str(row["dataset"]), str(row["out_len"]), int(row["num_prompts"]))
        grouped.setdefault(key, {})[str(row["feature_group"])] = row.get(metric, "")

    feature_groups = sorted({str(row["feature_group"]) for row in rows})
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dataset", "out_len", "num_prompts", *feature_groups])
        for key in sorted(
            grouped,
            key=lambda item: (item[0], out_len_sort_key(item[1]), item[2]),
        ):
            writer.writerow(
                [*key, *[grouped[key].get(group, "") for group in feature_groups]]
            )


def build_comparison_rows(
    rows: list[dict[str, object]],
    metric: str,
    baseline_group: str,
    candidate_group: str,
) -> list[dict[str, object]]:
    cases: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in rows:
        value = row.get(metric, "")
        if value == "":
            continue
        group = str(row["feature_group"])
        if group not in (baseline_group, candidate_group):
            continue
        key = (str(row["dataset"]), str(row["out_len"]), int(row["num_prompts"]))
        cases.setdefault(key, {})[group] = float(value)

    result = []
    for key, values in cases.items():
        if baseline_group not in values or candidate_group not in values:
            continue
        baseline = values[baseline_group]
        candidate = values[candidate_group]
        if baseline <= 0:
            delta_pct = math.nan
        elif metric in HIGHER_BETTER:
            delta_pct = (candidate - baseline) / baseline * 100.0
        else:
            delta_pct = (baseline - candidate) / baseline * 100.0
        result.append(
            {
                "dataset": key[0],
                "out_len": key[1],
                "num_prompts": key[2],
                "baseline": baseline,
                "candidate": candidate,
                "delta_pct": delta_pct,
                "x_label": x_label(key[1], key[2]),
            }
        )
    result.sort(
        key=lambda row: (
            str(row["dataset"]),
            out_len_sort_key(str(row["out_len"])),
            int(row["num_prompts"]),
        )
    )
    return result


def write_comparison_csv(
    rows: list[dict[str, object]],
    path: Path,
    baseline_label: str,
    candidate_label: str,
) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dataset",
                "out_len",
                "num_prompts",
                baseline_label,
                candidate_label,
                "delta_pct",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "dataset": row["dataset"],
                    "out_len": row["out_len"],
                    "num_prompts": row["num_prompts"],
                    baseline_label: row["baseline"],
                    candidate_label: row["candidate"],
                    "delta_pct": row["delta_pct"],
                }
            )


def plot_comparison(
    rows: list[dict[str, object]],
    out_path: Path,
    metric: str,
    baseline_label: str,
    candidate_label: str,
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    labels = [str(row["x_label"]) for row in rows]
    x = np.arange(len(labels))
    width = 0.36
    baseline = np.array([float(row["baseline"]) for row in rows])
    candidate = np.array([float(row["candidate"]) for row in rows])

    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)
    bars_base = ax.bar(
        x - width / 2, baseline, width, label=baseline_label, color="#C41E3A"
    )
    bars_cand = ax.bar(
        x + width / 2, candidate, width, label=candidate_label, color="#228B22"
    )

    ax.set_title(
        f"{metric}: {baseline_label} vs {candidate_label}",
        fontsize=15,
        fontweight="bold",
    )
    ax.set_ylabel(metric)
    ax.set_xlabel("Output length (num prompts)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()

    for bars in (bars_base, bars_cand):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    max_val = np.nanmax(np.r_[baseline, candidate])
    if max_val > 0:
        ax.set_ylim(0, max_val * 1.24)

    for i, row in enumerate(rows):
        delta = float(row["delta_pct"])
        if math.isnan(delta):
            continue
        color = "#228B22" if delta >= 0 else "#C41E3A"
        y = max(float(row["baseline"]), float(row["candidate"]))
        ax.annotate(
            f"{delta:+.1f}%",
            xy=(i, y),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=color,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": color,
                "alpha": 0.9,
            },
            clip_on=False,
        )

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_comparisons(
    rows: list[dict[str, object]],
    out_dir: Path,
    args: argparse.Namespace,
) -> None:
    metric_labels = {
        "output_throughput_tok_s": "Output throughput (tok/s)",
        "request_throughput_req_s": "Request throughput (req/s)",
        "mean_ttft_ms": "Mean TTFT (ms)",
        "mean_tpot_ms": "Mean TPOT (ms)",
        "mean_itl_ms": "Mean ITL (ms)",
    }
    for metric, label in metric_labels.items():
        comparison_rows = build_comparison_rows(
            rows,
            metric,
            args.baseline_group,
            args.candidate_group,
        )
        if not comparison_rows:
            continue
        stem = f"compare_{metric}_{args.baseline_group}_vs_{args.candidate_group}"
        write_comparison_csv(
            comparison_rows,
            out_dir / f"{stem}.csv",
            args.baseline_label,
            args.candidate_label,
        )
        if args.no_plots:
            continue
        try:
            import matplotlib

            matplotlib.use("Agg")
            plot_comparison(
                comparison_rows,
                out_dir / f"{stem}.png",
                label,
                args.baseline_label,
                args.candidate_label,
            )
        except Exception as exc:
            print(f"plot skipped for {metric}: {exc}")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        row
        for path in sorted(args.log_dir.glob("*.log"))
        if (row := parse_log(path)) is not None
    ]
    rows = keep_latest_per_case(filter_expected_workload(rows, args.expected_workload))
    rows.sort(
        key=lambda row: (
            str(row["dataset"]),
            int(row["out_len_sort"]),
            int(row["num_prompts"]),
            str(row["feature_group"]),
            str(row["stamp"]),
        )
    )

    summary_path = args.out_dir / "bench_summary.csv"
    write_csv(rows, summary_path)
    for metric in METRIC_PATTERNS:
        write_pairwise_csv(rows, args.out_dir / f"bench_{metric}.csv", metric)

    write_comparisons(rows, args.out_dir, args)

    print(f"parsed_logs={len(rows)}")
    print(f"summary={summary_path}")
    print(f"compare={args.baseline_group} vs {args.candidate_group}")
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
