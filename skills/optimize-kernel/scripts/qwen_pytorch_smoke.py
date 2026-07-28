#!/usr/bin/env python3
"""Minimum Qwen3/Qwen3.5 PyTorch pipeline smoke for kernel optimization.

Runs text and/or single-image requests through LMDeploy's PyTorch backend. Keep
aliases local and easy to edit; pass --model with an absolute checkpoint path
when validating a specific checkout or kernel branch.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

MODEL_ALIASES = {
    # Update these aliases to local snapshot paths when needed.
    "qwen3-8b": "Qwen/Qwen3-8B",
    "qwen3-vl-4b": "Qwen/Qwen3-VL-4B-Instruct",
    "qwen3-vl-30b": "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "qwen35-4b": "Qwen/Qwen3.5-4B",
    "qwen35-35b": "Qwen/Qwen3.5-35B-A3B",
    "qwen35-35b-fp8": "Qwen/Qwen3.5-35B-A3B-FP8",
}

QUANT_POLICIES = {
    "none": 0,
    "int4": 4,
    "int8": 8,
    "fp8": 16,
    "turbo_quant": 42,
    "turboquant": 42,
}


def resolve_model(model: str) -> str:
    return MODEL_ALIASES.get(model, model)


def parse_quant_policy(value: str) -> int:
    lowered = value.lower()
    if lowered in QUANT_POLICIES:
        return QUANT_POLICIES[lowered]
    return int(value)


def text_message(prompt: str) -> list[dict[str, Any]]:
    return [{"role": "user", "content": [{"type": "text", "text": prompt}]}]


def image_message(image_url: str, prompt: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ],
        }
    ]


def response_text(response: Any) -> str:
    if isinstance(response, (list, tuple)):
        return "\n".join(response_text(item) for item in response)
    text = getattr(response, "text", None)
    if text is not None:
        return str(text)
    return str(response)


def assert_nonempty(case: str, response: Any) -> str:
    text = response_text(response).strip()
    if not text:
        raise RuntimeError(f"{case} smoke produced an empty response: {response!r}")
    return text


def build_pipe(args: argparse.Namespace):
    if args.cuda is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.cuda
    os.environ.setdefault("LMDEPLOY_SKIP_WARMUP", "1")
    os.environ.setdefault("RAY_DEDUP_LOGS", "0")

    from lmdeploy import PytorchEngineConfig, pipeline

    backend_kwargs: dict[str, Any] = {
        "tp": args.tp,
        "max_batch_size": 2,
    }
    if args.eager:
        backend_kwargs["eager_mode"] = True
    if args.quant_policy:
        from lmdeploy.messages import QuantPolicy

        backend_kwargs["quant_policy"] = QuantPolicy(args.quant_policy)

    backend_config = PytorchEngineConfig(**backend_kwargs)
    return pipeline(
        resolve_model(args.model),
        backend_config=backend_config,
        log_level=args.log_level,
    )


def run_case(
    pipe: Any,
    case: str,
    messages: list[dict[str, Any]],
    max_new_tokens: int,
    temperature: float,
) -> None:
    from lmdeploy import GenerationConfig

    gen_config = GenerationConfig(
        max_new_tokens=max_new_tokens, temperature=temperature
    )
    print(f"\n===== {case} input =====")
    print(messages)
    response = pipe(messages, gen_config=gen_config)
    text = assert_nonempty(case, response)
    print(f"\n===== {case} output =====")
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="qwen3-vl-4b",
        help="Qwen alias or checkpoint path. Edit MODEL_ALIASES for local paths.",
    )
    parser.add_argument("--case", choices=["text", "image", "all"], default="all")
    parser.add_argument(
        "--cuda", default=None, help="CUDA_VISIBLE_DEVICES value, e.g. 0 or 6,7"
    )
    parser.add_argument("--tp", type=int, default=1)
    parser.add_argument("--tokens", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--eager", action="store_true")
    parser.add_argument("--quant-policy", type=parse_quant_policy, default=0)
    parser.add_argument(
        "--text-prompt", default="Briefly introduce yourself in one sentence."
    )
    parser.add_argument(
        "--image-url",
        default="https://raw.githubusercontent.com/open-mmlab/mmdeploy/main/tests/data/tiger.jpeg",
        help="Image URL or file:// path for the single-image smoke case.",
    )
    parser.add_argument(
        "--image-prompt", default="Describe this image in one sentence."
    )
    args = parser.parse_args()

    pipe = build_pipe(args)
    if args.case in {"text", "all"}:
        run_case(
            pipe, "text", text_message(args.text_prompt), args.tokens, args.temperature
        )
    if args.case in {"image", "all"}:
        run_case(
            pipe,
            "image",
            image_message(args.image_url, args.image_prompt),
            args.tokens,
            args.temperature,
        )
    print("\nQwen PyTorch smoke passed.")


if __name__ == "__main__":
    main()
