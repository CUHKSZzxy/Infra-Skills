#!/usr/bin/env python3
"""Template case file for ``kernel_microbench.py``.

Copy this file near a LMDeploy checkout or pass it directly to the generic
runner, then replace the setup/run/check functions with the target kernel.
Keep imports inside ``build_cases`` when they depend on PYTHONPATH.
"""

from __future__ import annotations

import argparse

import torch
from kernel_microbench import BenchmarkPair


def configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dtype", default="float16", choices=["float16", "bfloat16", "float32"]
    )
    parser.add_argument("--m", type=int, default=4096)
    parser.add_argument("--n", type=int, default=4096)


def build_cases(args: argparse.Namespace) -> list[BenchmarkPair]:
    dtype = getattr(torch, args.dtype)
    x = torch.randn(args.m, args.n, device="cuda", dtype=dtype)
    baseline_out = torch.empty_like(x)
    candidate_out = torch.empty_like(x)

    def run_baseline() -> None:
        # Replace this with the current LMDeploy kernel call.
        baseline_out.copy_(x)

    def run_candidate() -> None:
        # Replace this with the optimized candidate using the same call contract.
        candidate_out.copy_(x)

    def prepare_trial(seed: int) -> None:
        generator = torch.Generator(device="cuda").manual_seed(seed)
        x.normal_(generator=generator)

    def check_copy() -> dict[str, object]:
        baseline_out.fill_(float("nan"))
        candidate_out.fill_(float("nan"))
        run_baseline()
        run_candidate()
        torch.testing.assert_close(baseline_out, x)
        torch.testing.assert_close(candidate_out, x)
        torch.testing.assert_close(candidate_out, baseline_out)
        return {"correct": True}

    bytes_moved = x.numel() * x.element_size() * 2
    return [
        BenchmarkPair(
            name="copy",
            baseline=run_baseline,
            candidate=run_candidate,
            check=check_copy,
            prepare_trial=prepare_trial,
            shape=f"m={args.m},n={args.n}",
            dtype=args.dtype,
            bytes_moved=bytes_moved,
            metadata={"kind": "template"},
        )
    ]
