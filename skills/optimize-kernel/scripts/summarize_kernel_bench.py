#!/usr/bin/env python3
"""Summarize LMDeploy kernel benchmark JSONL artifacts as a Markdown table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def is_bench_row(row: dict[str, Any]) -> bool:
    return "mean_ms" in row and ("name" in row or "metadata" in row)


def iter_rows(path: Path) -> list[dict[str, Any]]:
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
            if isinstance(row, dict) and is_bench_row(row):
                row = dict(row)
                row["_file"] = str(path)
                rows.append(row)
    return rows


def cell(value: Any, digits: int = 4) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        text = f"{value:.{digits}f}"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def metadata_value(row: dict[str, Any], key: str) -> Any:
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        return metadata.get(key)
    return None


def row_sort_key(row: dict[str, Any]) -> tuple[str, str, float]:
    return (
        str(metadata_value(row, "stage") or ""),
        str(row.get("name") or ""),
        float(row.get("mean_ms") or 0.0),
    )


def shape_text(row: dict[str, Any]) -> str:
    if row.get("shape"):
        return str(row["shape"])
    qlen = metadata_value(row, "query_len")
    kvlen = metadata_value(row, "kv_len")
    heads = metadata_value(row, "q_heads")
    kv_heads = metadata_value(row, "kv_heads")
    head_dim = metadata_value(row, "head_dim")
    parts = []
    if qlen is not None:
        parts.append(f"q={qlen}")
    if kvlen is not None:
        parts.append(f"kv={kvlen}")
    if heads is not None or kv_heads is not None:
        parts.append(f"h={heads}/{kv_heads}")
    if head_dim is not None:
        parts.append(f"d={head_dim}")
    return ", ".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a compact table from LMDeploy kernel benchmark JSONL artifacts."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="JSONL artifact files")
    parser.add_argument("--stage", help="only show rows whose metadata.stage matches")
    parser.add_argument("--name", help="only show rows whose name matches")
    parser.add_argument("--sort", choices=("file", "stage", "mean"), default="stage")
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for path in args.paths:
        rows.extend(iter_rows(path))

    if args.stage:
        rows = [row for row in rows if metadata_value(row, "stage") == args.stage]
    if args.name:
        rows = [row for row in rows if row.get("name") == args.name]

    if args.sort == "file":
        rows.sort(key=lambda row: (str(row.get("_file")), row_sort_key(row)))
    elif args.sort == "mean":
        rows.sort(key=lambda row: float(row.get("mean_ms") or 0.0))
    else:
        rows.sort(key=row_sort_key)

    print(
        "| File | Name | Stage | Quant | Shape | Split | Mean ms | Median ms | p20-p80 ms | Correct |"
    )
    print("| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for row in rows:
        interval = f"{cell(row.get('p20_ms'))}-{cell(row.get('p80_ms'))}"
        print(
            "| "
            f"{cell(Path(str(row.get('_file'))).name)} | "
            f"{cell(row.get('name'))} | "
            f"{cell(metadata_value(row, 'stage'))} | "
            f"{cell(metadata_value(row, 'quant_policy'))} | "
            f"{cell(shape_text(row))} | "
            f"{cell(metadata_value(row, 'force_split_k'))} | "
            f"{cell(row.get('mean_ms'))} | "
            f"{cell(row.get('median_ms'))} | "
            f"{interval} | "
            f"{cell(row.get('correct'))} |"
        )


if __name__ == "__main__":
    main()
