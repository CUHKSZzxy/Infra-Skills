#!/usr/bin/env python3
"""Template case file for ``kernel_microbench.py``.

Copy this file near a LMDeploy checkout or pass it directly to the generic
runner, then replace the setup/run/check functions with the target kernel.
Keep imports inside ``build_cases`` when they depend on PYTHONPATH.
"""

from __future__ import annotations

import argparse

import torch
from kernel_microbench import BenchmarkCase


def configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dtype", default="float16", choices=["float16", "bfloat16", "float32"]
    )
    parser.add_argument("--m", type=int, default=4096)
    parser.add_argument("--n", type=int, default=4096)


def build_cases(args: argparse.Namespace) -> list[BenchmarkCase]:
    dtype = getattr(torch, args.dtype)
    x = torch.randn(args.m, args.n, device="cuda", dtype=dtype)
    y = torch.empty_like(x)

    def run_copy() -> None:
        # Replace this with the LMDeploy kernel call under test.
        y.copy_(x)

    def check_copy() -> dict[str, object]:
        torch.testing.assert_close(y, x)
        return {"correct": True}

    bytes_moved = x.numel() * x.element_size() * 2
    return [
        BenchmarkCase(
            name="copy_baseline",
            run=run_copy,
            check=check_copy,
            shape=f"m={args.m},n={args.n}",
            dtype=args.dtype,
            bytes_moved=bytes_moved,
            metadata={"kind": "template"},
        )
    ]
