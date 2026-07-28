#!/usr/bin/env python3
"""GSM8K-style accuracy test for an OpenAI-compatible server."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.request import urlopen

GSM8K_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"
INVALID_ANSWER = -9999999


MINI_GSM8K = [
    {
        "question": (
            "There are 3 cars in a garage. 2 more cars arrive. "
            "How many cars are there now?"
        ),
        "answer": "There are 3 + 2 = 5 cars. #### 5",
    },
    {
        "question": (
            "A box has 12 pencils. Amy gives away 5 pencils. "
            "How many pencils remain?"
        ),
        "answer": "12 - 5 = 7. #### 7",
    },
    {
        "question": (
            "Tom buys 4 bags of apples. Each bag has 6 apples. "
            "How many apples does Tom buy?"
        ),
        "answer": "4 * 6 = 24. #### 24",
    },
    {
        "question": (
            "A train has 9 cars. Each car has 8 seats. "
            "How many seats are on the train?"
        ),
        "answer": "9 * 8 = 72. #### 72",
    },
    {
        "question": (
            "Mia reads 15 pages on Monday and 18 pages on Tuesday. "
            "How many pages does she read?"
        ),
        "answer": "15 + 18 = 33. #### 33",
    },
    {
        "question": (
            "A baker makes 40 cookies and packs them equally into 8 boxes. "
            "How many cookies are in each box?"
        ),
        "answer": "40 / 8 = 5. #### 5",
    },
    {
        "question": (
            "Nina has 21 stickers. She buys 14 more and then gives away 9. "
            "How many stickers does she have?"
        ),
        "answer": "21 + 14 - 9 = 26. #### 26",
    },
    {
        "question": (
            "A class has 6 rows of desks with 5 desks in each row. "
            "How many desks are there?"
        ),
        "answer": "6 * 5 = 30. #### 30",
    },
]


@dataclass
class EvalItem:
    question: str
    expected_answer: int | float
    extracted_answer: int | float
    score: float
    response: str
    error: str | None = None


@dataclass
class EvalResult:
    correct: int
    total: int
    accuracy: float
    items: list[EvalItem]


def read_jsonl(path: str) -> list[dict[str, str]]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def default_cache_path() -> Path:
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_root / "infra-skills" / "gsm8k_test.jsonl"


def download_gsm8k(url: str, cache_path: str | Path) -> Path:
    cache_path = Path(cache_path).expanduser()
    if cache_path.exists():
        return cache_path

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading GSM8K test set to {cache_path}")
    with urlopen(url, timeout=60) as response:
        cache_path.write_bytes(response.read())
    return cache_path


def load_records(args) -> list[dict[str, str]]:
    if args.mini:
        return MINI_GSM8K
    if args.data_path:
        return read_jsonl(args.data_path)
    return read_jsonl(str(download_gsm8k(args.gsm8k_url, args.cache_path)))


def extract_answer_value(answer: str) -> int | float:
    answer = answer.replace(",", "")
    numbers = re.findall(r"-?\d+\.?\d*", answer)
    if not numbers:
        return INVALID_ANSWER
    try:
        return ast.literal_eval(numbers[-1])
    except (SyntaxError, ValueError):
        return INVALID_ANSWER


def format_example(record: dict[str, str], include_answer: bool) -> str:
    text = f"Question: {record['question']}\nAnswer:"
    if include_answer:
        text += f" {record['answer']}"
    return text


def split_examples(
    records: list[dict[str, str]], num_shots: int, num_examples: int | None
):
    if len(records) <= num_shots:
        raise ValueError(f"Need more than {num_shots} records, got {len(records)}.")

    few_shot = records[:num_shots]
    eval_records = records[num_shots:]
    if num_examples is not None:
        eval_records = eval_records[:num_examples]
    if not eval_records:
        raise ValueError("No evaluation records selected.")
    return few_shot, eval_records


def build_prompt(few_shot: Iterable[dict[str, str]], question: dict[str, str]) -> str:
    prefix = "".join(
        format_example(record, include_answer=True) + "\n\n" for record in few_shot
    )
    instruction = "Solve the math problem. End with the final numeric answer.\n\n"
    return instruction + prefix + format_example(question, include_answer=False)


def parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError("must be a valid JSON object string") from e
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("must be a JSON object")
    return parsed


def run_eval(
    records: list[dict[str, str]],
    sampler: Callable[[str], str],
    num_shots: int,
    num_examples: int | None = None,
    num_threads: int = 16,
    progress_interval: int = 20,
) -> EvalResult:
    few_shot, eval_records = split_examples(
        records, num_shots=num_shots, num_examples=num_examples
    )
    items: list[EvalItem | None] = [None] * len(eval_records)

    def eval_one(idx: int, record: dict[str, str]) -> EvalItem:
        expected = extract_answer_value(record["answer"])
        try:
            response = sampler(build_prompt(few_shot, record))
            error = None
        except Exception as e:
            response = ""
            error = repr(e)
        extracted = extract_answer_value(response)
        score = float(extracted == expected)
        return EvalItem(
            question=record["question"],
            expected_answer=expected,
            extracted_answer=extracted,
            score=score,
            response=response,
            error=error,
        )

    tic = time.perf_counter()
    if num_threads <= 1:
        for idx, record in enumerate(eval_records):
            items[idx] = eval_one(idx, record)
            if progress_interval and (idx + 1) % progress_interval == 0:
                elapsed = time.perf_counter() - tic
                print(
                    f"progress={idx + 1}/{len(eval_records)} elapsed={elapsed:.1f}s",
                    file=sys.stderr,
                    flush=True,
                )
    else:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {
                executor.submit(eval_one, idx, record): idx
                for idx, record in enumerate(eval_records)
            }
            completed = 0
            for future in as_completed(futures):
                idx = futures[future]
                items[idx] = future.result()
                completed += 1
                if progress_interval and completed % progress_interval == 0:
                    elapsed = time.perf_counter() - tic
                    print(
                        f"progress={completed}/{len(eval_records)} elapsed={elapsed:.1f}s",
                        file=sys.stderr,
                        flush=True,
                    )

    final_items = [item for item in items if item is not None]
    correct = sum(int(item.score) for item in final_items)
    total = len(final_items)
    return EvalResult(
        correct=correct, total=total, accuracy=correct / total, items=final_items
    )


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    return base_url


def make_openai_sampler(args) -> Callable[[str], str]:
    try:
        import httpx
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError(
            "Please install openai and httpx to call an OpenAI-compatible API server."
        ) from e

    client = OpenAI(
        api_key=args.api_key or os.environ.get("OPENAI_API_KEY", "EMPTY"),
        base_url=normalize_base_url(args.base_url),
        http_client=httpx.Client(trust_env=args.disable_proxy_bypass),
        timeout=args.timeout,
    )
    model = args.model
    if model is None:
        model = client.models.list().data[0].id
    extra_body = args.extra_body_json

    def sample(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            extra_body=extra_body,
        )
        return response.choices[0].message.content or ""

    return sample


def parse_args():
    parser = argparse.ArgumentParser(description="Run a GSM8K-style accuracy test.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:23333",
        help="OpenAI-compatible server URL, with or without /v1.",
    )
    parser.add_argument(
        "--model", default=None, help="Served model name. Defaults to /v1/models[0].id."
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key. Defaults to OPENAI_API_KEY or EMPTY.",
    )
    parser.add_argument(
        "--data-path",
        default=None,
        help="Optional local GSM8K-format JSONL path with question/answer fields.",
    )
    parser.add_argument(
        "--gsm8k-url",
        default=GSM8K_URL,
        help="GSM8K test JSONL URL used when --data-path and --mini are not set.",
    )
    parser.add_argument(
        "--cache-path",
        default=str(default_cache_path()),
        help="Local cache path for downloaded GSM8K test JSONL.",
    )
    parser.add_argument(
        "--mini",
        action="store_true",
        help="Use the built-in tiny sample set instead of the full GSM8K test set.",
    )
    parser.add_argument(
        "--disable-proxy-bypass",
        action="store_true",
        help="Let httpx honor proxy environment variables instead of bypassing them.",
    )
    parser.add_argument(
        "--num-shots",
        type=int,
        default=5,
        help="Few-shot examples taken from the start of the data.",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=None,
        help="Number of eval examples after few-shot records.",
    )
    parser.add_argument(
        "--num-threads",
        type=int,
        default=16,
        help="Concurrent request threads.",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=20,
        help="Print progress every N completed requests; set 0 to disable.",
    )
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument(
        "--extra-body-json",
        type=parse_json_object,
        default=None,
        help='JSON object passed as OpenAI extra_body, e.g. \'{"chat_template_kwargs":{"enable_thinking":false}}\'.',
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument(
        "--show-details", action="store_true", help="Print each prompt result."
    )
    parser.add_argument(
        "--dump-json", default=None, help="Optional path to write metrics and details."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    records = load_records(args)
    result = run_eval(
        records=records,
        sampler=make_openai_sampler(args),
        num_shots=args.num_shots,
        num_examples=args.num_examples,
        num_threads=args.num_threads,
        progress_interval=args.progress_interval,
    )

    for idx, item in enumerate(result.items):
        if args.show_details or not item.score:
            status = "OK" if item.score else "FAIL"
            print(
                f"[{idx}] {status} "
                f"expected={item.expected_answer} got={item.extracted_answer}"
            )
            print(f"question: {item.question}")
            if item.error:
                print(f"error: {item.error}")
            print(f"response: {item.response}\n")

    print(
        f"accuracy={result.accuracy:.4f} correct={result.correct} total={result.total}"
    )

    if args.dump_json:
        payload = {
            "accuracy": result.accuracy,
            "correct": result.correct,
            "total": result.total,
            "items": [item.__dict__ for item in result.items],
        }
        with open(args.dump_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
