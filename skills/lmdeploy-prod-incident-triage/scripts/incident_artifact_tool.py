#!/usr/bin/env python3
"""Collect and summarize read-only LMDeploy serving incident bundles."""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib import error, parse, request


METRIC_RE = re.compile(
    r"^(?P<name>[^{\s]+)(?:\{(?P<labels>[^}]*)\})?\s+"
    r"(?P<value>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)$"
)
LABEL_RE = re.compile(r'([a-zA-Z_:][a-zA-Z0-9_:]*)="((?:[^"\\]|\\.)*)"')

ENDPOINTS = (
    ("json", "health.json", "/health"),
    ("json", "models.json", "/v1/models"),
    ("text", "metrics.txt", "/metrics"),
    ("json", "is_sleeping.json", "/is_sleeping"),
    ("json", "distserve_engine_info.json", "/distserve/engine_info"),
    ("json", "nodes_status.json", "/nodes/status"),
)


def request_text(base_url: str, path: str, token: str | None, timeout: float) -> tuple[bool, int, str]:
    url = parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return True, resp.status, resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        return False, exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return False, -1, f"{type(exc).__name__}: {exc}"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def collect_bundle(base_url: str, outdir: str | None, token: str | None, timeout: float) -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    bundle_dir = Path(outdir or f"./lmdeploy_incident_bundle_{timestamp}").resolve()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        bundle_dir / "metadata.json",
        {
            "artifact_type": "lmdeploy_incident_bundle",
            "base_url": base_url,
            "collected_at": timestamp,
            "token_provided": bool(token),
            "timeout_seconds": timeout,
        },
    )

    summary_lines: list[str] = []
    for kind, filename, path in ENDPOINTS:
        ok, status, body = request_text(base_url, path, token, timeout)
        result: dict[str, Any] = {"ok": ok, "status": status, "path": path}
        if ok and kind == "json":
            try:
                result["json"] = json.loads(body)
            except json.JSONDecodeError:
                result["text"] = body
                result["decode_error"] = "response was not valid JSON"
        elif ok:
            result["text"] = body
        else:
            result["error"] = body

        output = bundle_dir / filename
        if ok and kind == "text":
            output.write_text(body, encoding="utf-8")
        else:
            write_json(output, result)
        summary_lines.append(f"{filename}: {'ok' if ok else f'failed status={status}'}")

    (bundle_dir / "SUMMARY.txt").write_text(
        "\n".join(
            summary_lines
            + [
                "",
                "This bundle is read-only. It does not start profiling or change server state.",
                "Optional endpoints may fail on older builds or non-proxy deployments.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return bundle_dir


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def unwrap(path: Path) -> dict[str, Any] | None:
    value = load_json(path)
    if value is None:
        return None
    if isinstance(value, dict) and "json" in value:
        inner = value["json"]
        return inner if isinstance(inner, dict) else {"value": inner}
    return value


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_labels(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    return {
        key: bytes(value, "utf-8").decode("unicode_escape")
        for key, value in LABEL_RE.findall(raw)
    }


def parse_metrics(text: str) -> dict[str, list[dict[str, Any]]]:
    metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = METRIC_RE.match(line)
        if match is None:
            continue
        metrics[match.group("name")].append(
            {
                "labels": parse_labels(match.group("labels")),
                "value": float(match.group("value")),
            }
        )
    return metrics


def metric_sum(metrics: dict[str, list[dict[str, Any]]], name: str) -> float:
    return sum(item["value"] for item in metrics.get(name, []))


def metric_max(metrics: dict[str, list[dict[str, Any]]], name: str) -> float | None:
    values = [item["value"] for item in metrics.get(name, [])]
    if not values:
        return None
    return max(values)


def hist_avg(metrics: dict[str, list[dict[str, Any]]], base_name: str) -> float | None:
    total = metric_sum(metrics, f"{base_name}_sum")
    count = metric_sum(metrics, f"{base_name}_count")
    if count == 0:
        return None
    return total / count


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def health_status(bundle_dir: Path) -> tuple[str, str]:
    health = unwrap(bundle_dir / "health.json") or {}
    if "status" in health:
        return str(health.get("status")), str(health.get("message") or "")
    raw = load_json(bundle_dir / "health.json") or {}
    if raw.get("ok") is False:
        return "failed", str(raw.get("error") or raw.get("status"))
    return "unknown", ""


def model_ids(bundle_dir: Path) -> list[str]:
    models = unwrap(bundle_dir / "models.json") or {}
    data = models.get("data")
    if not isinstance(data, list):
        return []
    ids = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return ids


def build_summary(bundle_dir: Path) -> dict[str, Any]:
    metadata = load_json(bundle_dir / "metadata.json") or {}
    metrics = parse_metrics(read_text(bundle_dir / "metrics.txt"))
    health, health_message = health_status(bundle_dir)
    ids = model_ids(bundle_dir)

    summary: dict[str, Any] = {
        "bundle_dir": str(bundle_dir),
        "base_url": metadata.get("base_url"),
        "collected_at": metadata.get("collected_at"),
        "health": health,
        "health_message": health_message,
        "models": ids,
        "metrics": {
            "api_waiting": metric_sum(metrics, "lmdeploy:num_api_requests_waiting"),
            "engine_running": metric_sum(metrics, "lmdeploy:num_requests_running"),
            "engine_waiting": metric_sum(metrics, "lmdeploy:num_requests_waiting"),
            "gpu_cache_usage_max": metric_max(metrics, "lmdeploy:gpu_cache_usage_perc"),
            "prompt_tokens_total": metric_sum(metrics, "lmdeploy:prompt_tokens_total"),
            "generation_tokens_total": metric_sum(metrics, "lmdeploy:generation_tokens_total"),
            "avg_ttft_seconds": hist_avg(metrics, "lmdeploy:time_to_first_token_seconds"),
            "avg_tpot_seconds": hist_avg(metrics, "lmdeploy:time_per_output_token_seconds"),
            "avg_itl_seconds": hist_avg(metrics, "lmdeploy:iter_token_latency"),
            "avg_e2e_seconds": hist_avg(metrics, "lmdeploy:e2e_request_latency_seconds"),
            "avg_queue_seconds": hist_avg(metrics, "lmdeploy:request_queue_time_seconds"),
            "avg_prefill_seconds": hist_avg(metrics, "lmdeploy:request_prefill_time_seconds"),
            "avg_decode_seconds": hist_avg(metrics, "lmdeploy:request_decode_time_seconds"),
        },
        "signals": [],
    }

    signals = summary["signals"]
    m = summary["metrics"]
    if health not in ("healthy", "sleeping", "unknown"):
        signals.append(f"/health is not green: {health} {health_message}".strip())
    if not ids:
        signals.append("/v1/models did not return a model list; check reachability, auth, or startup.")
    if m["api_waiting"] > 0:
        signals.append(f"API-side waiting requests present: {fmt(m['api_waiting'], 0)}.")
    if m["engine_waiting"] > 0:
        signals.append(f"Engine-side waiting requests present: {fmt(m['engine_waiting'], 0)}.")
    if m["gpu_cache_usage_max"] is not None and m["gpu_cache_usage_max"] >= 0.9:
        signals.append(f"GPU KV-cache usage is high: {fmt(m['gpu_cache_usage_max'])}.")
    if (
        m["avg_ttft_seconds"] is not None
        and m["avg_queue_seconds"] is not None
        and m["avg_ttft_seconds"] > 2.0
        and m["avg_queue_seconds"] < 0.2
    ):
        signals.append(
            "TTFT is high while queue time is low; inspect prefill, preprocessing, or RPC handoff."
        )
    if m["prompt_tokens_total"] == 0 and m["generation_tokens_total"] == 0:
        signals.append("Metrics show no token work; bundle may be idle or metrics may be disabled.")
    return summary


def render_summary(summary: dict[str, Any]) -> str:
    m = summary["metrics"]
    lines = [
        f"Bundle: {summary['bundle_dir']}",
        f"Base URL: {summary.get('base_url') or 'n/a'}",
        f"Collected At: {summary.get('collected_at') or 'n/a'}",
        f"Health: {summary.get('health')} {summary.get('health_message') or ''}".rstrip(),
        f"Models: {', '.join(summary['models']) if summary['models'] else 'n/a'}",
        "Queue/Capacity: "
        f"api_waiting={fmt(m['api_waiting'], 0)} "
        f"engine_running={fmt(m['engine_running'], 0)} "
        f"engine_waiting={fmt(m['engine_waiting'], 0)} "
        f"gpu_cache_usage_max={fmt(m['gpu_cache_usage_max'])}",
        "Token totals: "
        f"prompt={fmt(m['prompt_tokens_total'], 0)} "
        f"generation={fmt(m['generation_tokens_total'], 0)}",
        "Latency averages: "
        f"ttft={fmt(m['avg_ttft_seconds'])}s "
        f"tpot={fmt(m['avg_tpot_seconds'])}s "
        f"itl={fmt(m['avg_itl_seconds'])}s "
        f"e2e={fmt(m['avg_e2e_seconds'])}s "
        f"queue={fmt(m['avg_queue_seconds'])}s "
        f"prefill={fmt(m['avg_prefill_seconds'])}s "
        f"decode={fmt(m['avg_decode_seconds'])}s",
        "",
        "What stands out:",
    ]
    if summary["signals"]:
        lines.extend(f"- {signal}" for signal in summary["signals"])
    else:
        lines.append("- No strong signal from this bundle.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    collect = subparsers.add_parser("collect-bundle")
    collect.add_argument("--base-url", required=True)
    collect.add_argument("--outdir")
    collect.add_argument("--token")
    collect.add_argument("--timeout", type=float, default=10.0)

    summarize = subparsers.add_parser("summarize-bundle")
    summarize.add_argument("bundle_dir")
    summarize.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.cmd == "collect-bundle":
        bundle_dir = collect_bundle(args.base_url, args.outdir, args.token, args.timeout)
        print(bundle_dir)
        return

    summary = build_summary(Path(args.bundle_dir))
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(render_summary(summary), end="")


if __name__ == "__main__":
    main()
