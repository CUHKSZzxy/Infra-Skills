#!/usr/bin/env python3
"""Initialize and run bounded paired LMDeploy kernel benchmark campaigns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
RUNNER = SCRIPT_DIR / "kernel_microbench.py"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("root", type=Path)
    init.add_argument("--case-file", type=Path, required=True)
    init.add_argument("--source-checkout", type=Path, required=True)
    init.add_argument("--python", default=sys.executable)
    init.add_argument("--gpu", default="0")
    init.add_argument("--max-rounds", type=int, default=5)
    init.add_argument("--warmup", type=int, default=10)
    init.add_argument("--trials", type=int, default=7)
    init.add_argument("--target-sample-us", type=float, default=1000.0)
    init.add_argument("--inner-iterations-max", type=int, default=4096)
    init.add_argument("--minimum-gain-pct", type=float, default=3.0)
    init.add_argument("--regression-pct", type=float, default=3.0)
    init.add_argument("--case-args", nargs=argparse.REMAINDER, default=[])

    run = commands.add_parser("run")
    run.add_argument("root", type=Path)
    run.add_argument("--hypothesis", required=True)

    status = commands.add_parser("status")
    status.add_argument("root", type=Path)
    return parser


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object in {path}")
    return value


def _git_value(checkout: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(checkout), *args],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def init_campaign(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if root.exists() and any(root.iterdir()):
        raise RuntimeError(f"campaign directory is not empty: {root}")
    if "," in args.gpu:
        raise RuntimeError("kernel campaigns use one GPU id by default")
    if args.max_rounds <= 0:
        raise RuntimeError("max-rounds must be positive")

    case_file = args.case_file.resolve()
    checkout = args.source_checkout.resolve()
    if not case_file.is_file():
        raise RuntimeError(f"case file does not exist: {case_file}")
    if not checkout.is_dir():
        raise RuntimeError(f"source checkout does not exist: {checkout}")

    root.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "case_file": str(case_file),
        "case_file_sha256": _sha256(case_file),
        "case_args": list(args.case_args),
        "source_checkout": str(checkout),
        "source_commit": _git_value(checkout, "rev-parse", "HEAD"),
        "source_branch": _git_value(checkout, "branch", "--show-current"),
        "python": args.python,
        "gpu": args.gpu,
        "max_rounds": args.max_rounds,
        "warmup": args.warmup,
        "trials": args.trials,
        "target_sample_us": args.target_sample_us,
        "inner_iterations_max": args.inner_iterations_max,
        "minimum_gain_pct": args.minimum_gain_pct,
        "regression_pct": args.regression_pct,
    }
    checkpoint = {
        "schema_version": 1,
        "status": "active",
        "next_round": 0,
        "last_round": None,
        "last_decision": None,
    }
    _write_json(root / "campaign.json", config)
    _write_json(root / "checkpoint.json", checkpoint)
    (root / "rounds").mkdir()
    print(json.dumps({"root": str(root), **checkpoint}, sort_keys=True))


def run_campaign(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    config = _read_json(root / "campaign.json")
    checkpoint_path = root / "checkpoint.json"
    checkpoint = _read_json(checkpoint_path)
    if checkpoint.get("status") != "active":
        raise RuntimeError(f"campaign is not active: status={checkpoint.get('status')}")
    case_file = Path(str(config["case_file"]))
    if _sha256(case_file) != config.get("case_file_sha256"):
        raise RuntimeError(
            "benchmark case file changed; initialize a new campaign for the "
            "new measurement contract"
        )

    round_index = int(checkpoint["next_round"])
    max_rounds = int(config["max_rounds"])
    if round_index >= max_rounds:
        checkpoint["status"] = "budget_exhausted"
        _write_json(checkpoint_path, checkpoint)
        raise RuntimeError("campaign round budget is exhausted")

    round_dir = root / "rounds" / f"{round_index:03d}"
    if round_dir.exists():
        raise RuntimeError(f"round directory already exists: {round_dir}")
    round_dir.mkdir(parents=True)
    (round_dir / "hypothesis.md").write_text(
        f"# Hypothesis\n\n{args.hypothesis.strip()}\n",
        encoding="utf-8",
    )

    command = [
        str(config["python"]),
        str(RUNNER),
        str(config["case_file"]),
        "--out",
        str(round_dir / "results.jsonl"),
        "--label",
        f"round-{round_index:03d}",
        "--warmup",
        str(config["warmup"]),
        "--trials",
        str(config["trials"]),
        "--target-sample-us",
        str(config["target_sample_us"]),
        "--inner-iterations-max",
        str(config["inner_iterations_max"]),
        "--minimum-gain-pct",
        str(config["minimum_gain_pct"]),
        "--regression-pct",
        str(config["regression_pct"]),
        "--workload-manifest",
        str(root / "workloads.json"),
        "--decision-out",
        str(round_dir / "decision.json"),
        "--report-out",
        str(round_dir / "comparison.md"),
    ]
    case_args = list(config.get("case_args") or [])
    if case_args:
        command.extend(["--", *case_args])

    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = str(config["gpu"])
    source_checkout = str(config["source_checkout"])
    current_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{source_checkout}{os.pathsep}{current_pythonpath}"
        if current_pythonpath
        else source_checkout
    )
    _write_json(
        round_dir / "command.json",
        {
            "argv": command,
            "cwd": source_checkout,
            "environment": {
                "CUDA_VISIBLE_DEVICES": environment["CUDA_VISIBLE_DEVICES"],
                "PYTHONPATH": environment["PYTHONPATH"],
            },
        },
    )

    result = subprocess.run(
        command,
        cwd=source_checkout,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (round_dir / "runner.log").write_text(result.stdout, encoding="utf-8")
    print(result.stdout, end="")

    decision_path = round_dir / "decision.json"
    if result.returncode != 0:
        decision = {
            "status": "runner_failed",
            "reason": f"runner exited with code {result.returncode}",
        }
    elif not decision_path.exists():
        decision = {
            "status": "runner_failed",
            "reason": "runner completed without writing a decision",
        }
    else:
        decision = _read_json(decision_path)
    checkpoint.update(
        {
            "next_round": round_index + 1,
            "last_round": round_index,
            "last_decision": decision,
        }
    )
    if decision.get("status") == "accepted":
        checkpoint["status"] = "candidate_accepted"
    elif round_index + 1 >= max_rounds:
        checkpoint["status"] = "budget_exhausted"
    _write_json(checkpoint_path, checkpoint)
    print(json.dumps(checkpoint, sort_keys=True))
    if decision["status"] == "runner_failed":
        raise SystemExit(result.returncode or 1)


def show_status(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    print(
        json.dumps(
            {
                "root": str(root),
                "campaign": _read_json(root / "campaign.json"),
                "checkpoint": _read_json(root / "checkpoint.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    args = _parser().parse_args()
    if args.command == "init":
        init_campaign(args)
    elif args.command == "run":
        run_campaign(args)
    else:
        show_status(args)


if __name__ == "__main__":
    main()
