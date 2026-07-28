#!/usr/bin/env python3
"""Run a small deterministic OpenAI-compatible API smoke and save outputs."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_PROMPTS = [
    "Give the final answer only: 17 + 28 =",
    "Write one short sentence explaining why KV cache helps autoregressive generation.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:23334/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="JSONL strings or objects with a 'prompt' field.",
    )
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--endpoint", choices=("chat", "completion"), default="chat")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser.parse_args()


def load_prompts(path: Path | None) -> list[str]:
    if path is None:
        return DEFAULT_PROMPTS
    prompts: list[str] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        prompts.append(item if isinstance(item, str) else item["prompt"])
    return prompts


def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer EMPTY"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode())


def extract_text(response: dict[str, object], endpoint: str) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    choice = choices[0]
    if endpoint == "chat":
        return str(choice.get("message", {}).get("content", ""))
    return str(choice.get("text", ""))


def build_payload(args: argparse.Namespace, prompt: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    if args.endpoint == "chat":
        payload["messages"] = [{"role": "user", "content": prompt}]
    else:
        payload["prompt"] = prompt
    return payload


def main() -> int:
    args = parse_args()
    prompts = load_prompts(args.prompt_file)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    route = "chat/completions" if args.endpoint == "chat" else "completions"
    url = f"{args.base_url.rstrip('/')}/{route}"

    with args.out.open("w") as f:
        for index, prompt in enumerate(prompts):
            started = time.perf_counter()
            row: dict[str, object] = {"index": index, "prompt": prompt}
            try:
                response = post_json(url, build_payload(args, prompt))
                row["latency_s"] = round(time.perf_counter() - started, 6)
                row["text"] = extract_text(response, args.endpoint)
                row["usage"] = response.get("usage", {})
            except (urllib.error.URLError, TimeoutError) as exc:
                row["error"] = repr(exc)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
