#!/usr/bin/env python3
"""OCRBench accuracy test for an OpenAI-compatible VLM server."""

from __future__ import annotations

import argparse
import ast
import base64
import csv
import json
import mimetypes
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

OCRBENCH_URL = "https://opencompass.openxlab.space/utils/VLMEval/OCRBench.tsv"
OCRBENCH_MINI_URL = "https://opencompass.openxlab.space/utils/TEST/OCRBench_MINI.tsv"

OCRBENCH_CATEGORIES = [
    "Regular Text Recognition",
    "Irregular Text Recognition",
    "Artistic Text Recognition",
    "Handwriting Recognition",
    "Digit String Recognition",
    "Non-Semantic Text Recognition",
    "Scene Text-centric VQA",
    "Doc-oriented VQA",
    "Key Information Extraction",
    "Handwritten Mathematical Expression Recognition",
]

TEXT_RECOGNITION_CATEGORIES = [
    "Regular Text Recognition",
    "Irregular Text Recognition",
    "Artistic Text Recognition",
    "Handwriting Recognition",
    "Digit String Recognition",
    "Non-Semantic Text Recognition",
]

PROMPT_SUFFIX = "Answer the question using a single word or phrase."


@dataclass
class OCRBenchRecord:
    index: int
    image: str
    question: str
    answers: list[str]
    category: str


@dataclass
class EvalItem:
    index: int
    question: str
    category: str
    expected_answers: list[str]
    score: float
    response: str
    error: str | None = None


@dataclass
class EvalResult:
    correct: int
    total: int
    accuracy: float
    request_errors: int
    scores: dict[str, float]
    category_totals: dict[str, int]
    items: list[EvalItem]


def set_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = limit // 10


def default_cache_path(mini: bool = False) -> Path:
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    name = "OCRBench_MINI.tsv" if mini else "OCRBench.tsv"
    return cache_root / "infra-skills" / name


def download_ocrbench(url: str, cache_path: str | Path) -> Path:
    cache_path = Path(cache_path).expanduser()
    if cache_path.exists():
        return cache_path

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading OCRBench TSV to {cache_path}", file=sys.stderr)
    with urlopen(url, timeout=120) as response:
        cache_path.write_bytes(response.read())
    return cache_path


def parse_answer_list(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return [value]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def read_tsv(path: str | Path) -> list[OCRBenchRecord]:
    set_csv_field_limit()
    records: list[OCRBenchRecord] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"index", "image", "question", "answer", "category"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing OCRBench columns: {sorted(missing)}")
        for row in reader:
            records.append(
                OCRBenchRecord(
                    index=int(row["index"]),
                    image=row["image"],
                    question=row["question"],
                    answers=parse_answer_list(row["answer"]),
                    category=row["category"],
                )
            )
    return records


def load_records(args) -> tuple[list[OCRBenchRecord], str]:
    if args.data_path:
        return read_tsv(args.data_path), str(args.data_path)

    cache_path = args.cache_path or str(default_cache_path(args.mini))
    url = args.ocrbench_mini_url if args.mini else args.ocrbench_url
    path = download_ocrbench(url, cache_path)
    return read_tsv(path), str(path)


def select_records(
    records: list[OCRBenchRecord],
    start_index: int = 0,
    num_examples: int | None = None,
) -> list[OCRBenchRecord]:
    selected = records[start_index:]
    if num_examples is not None:
        selected = selected[:num_examples]
    if not selected:
        raise ValueError("No evaluation records selected.")
    return selected


def infer_image_mime_from_bytes(raw: bytes) -> str:
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        return "image/gif"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def image_to_data_url(image: str) -> str:
    if image.startswith("data:image/"):
        return image

    image_path = Path(image).expanduser()
    try:
        path_exists = image_path.exists()
    except OSError:
        path_exists = False
    if path_exists:
        raw = image_path.read_bytes()
        mime = mimetypes.guess_type(str(image_path))[0] or infer_image_mime_from_bytes(
            raw
        )
        encoded = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    compact = "".join(image.split())
    raw = base64.b64decode(compact[:128] + "===")
    mime = infer_image_mime_from_bytes(raw)
    return f"data:{mime};base64,{compact}"


def build_prompt(record: OCRBenchRecord) -> str:
    return f"{record.question}\n{PROMPT_SUFFIX}"


def build_messages(record: OCRBenchRecord) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_to_data_url(record.image)},
                },
                {"type": "text", "text": build_prompt(record)},
            ],
        }
    ]


def normalize_prediction_for_category(text: str, category: str) -> str:
    text = text.strip().replace("\n", " ")
    if category == "Handwritten Mathematical Expression Recognition":
        return text.replace(" ", "")
    return text.lower()


def normalize_answer_for_category(text: str, category: str) -> str:
    text = text.strip().replace("\n", " ")
    if category == "Handwritten Mathematical Expression Recognition":
        return text.replace(" ", "")
    return text.lower()


def score_response(record: OCRBenchRecord, response: str) -> float:
    prediction = normalize_prediction_for_category(response, record.category)
    for answer in record.answers:
        expected = normalize_answer_for_category(answer, record.category)
        if expected in prediction:
            return 1.0
    return 0.0


def aggregate_scores(items: list[EvalItem]) -> tuple[dict[str, float], dict[str, int]]:
    raw_scores = {category: 0 for category in OCRBENCH_CATEGORIES}
    category_totals = {category: 0 for category in OCRBENCH_CATEGORIES}

    for item in items:
        if item.category not in raw_scores:
            raw_scores[item.category] = 0
            category_totals[item.category] = 0
        raw_scores[item.category] += int(item.score)
        category_totals[item.category] += 1

    scores: dict[str, float] = {
        "Text Recognition": sum(
            raw_scores[category] for category in TEXT_RECOGNITION_CATEGORIES
        ),
        "Scene Text-centric VQA": raw_scores["Scene Text-centric VQA"],
        "Doc-oriented VQA": raw_scores["Doc-oriented VQA"],
        "Key Information Extraction": raw_scores["Key Information Extraction"],
        "Handwritten Mathematical Expression Recognition": raw_scores[
            "Handwritten Mathematical Expression Recognition"
        ],
    }
    scores["Final Score"] = sum(scores.values())
    scores["Final Score Norm"] = float(scores["Final Score"]) / 10
    return scores, category_totals


def run_eval(
    records: list[OCRBenchRecord],
    sampler: Callable[[OCRBenchRecord], str],
    num_threads: int = 8,
    progress_interval: int = 20,
) -> EvalResult:
    items: list[EvalItem | None] = [None] * len(records)

    def eval_one(idx: int, record: OCRBenchRecord) -> EvalItem:
        try:
            response = sampler(record)
            error = None
        except Exception as e:
            response = ""
            error = repr(e)
        score = score_response(record, response) if error is None else 0.0
        return EvalItem(
            index=record.index,
            question=record.question,
            category=record.category,
            expected_answers=record.answers,
            score=score,
            response=response,
            error=error,
        )

    tic = time.perf_counter()
    if num_threads <= 1:
        for idx, record in enumerate(records):
            items[idx] = eval_one(idx, record)
            if progress_interval and (idx + 1) % progress_interval == 0:
                elapsed = time.perf_counter() - tic
                print(
                    f"progress={idx + 1}/{len(records)} elapsed={elapsed:.1f}s",
                    file=sys.stderr,
                    flush=True,
                )
    else:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {
                executor.submit(eval_one, idx, record): idx
                for idx, record in enumerate(records)
            }
            completed = 0
            for future in as_completed(futures):
                idx = futures[future]
                items[idx] = future.result()
                completed += 1
                if progress_interval and completed % progress_interval == 0:
                    elapsed = time.perf_counter() - tic
                    print(
                        f"progress={completed}/{len(records)} elapsed={elapsed:.1f}s",
                        file=sys.stderr,
                        flush=True,
                    )

    final_items = [item for item in items if item is not None]
    correct = sum(int(item.score) for item in final_items)
    total = len(final_items)
    request_errors = sum(1 for item in final_items if item.error)
    scores, category_totals = aggregate_scores(final_items)
    return EvalResult(
        correct=correct,
        total=total,
        accuracy=correct / total,
        request_errors=request_errors,
        scores=scores,
        category_totals=category_totals,
        items=final_items,
    )


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    return base_url


def parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError("must be a valid JSON object string") from e
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("must be a JSON object")
    return parsed


def make_openai_sampler(args) -> Callable[[OCRBenchRecord], str]:
    try:
        import httpx
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError(
            "Please install openai and httpx to call an OpenAI-compatible VLM server."
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

    def sample(record: OCRBenchRecord) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=build_messages(record),
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            extra_body=extra_body,
        )
        return response.choices[0].message.content or ""

    return sample


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run OCRBench accuracy for a VLM server."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:23333",
        help="OpenAI-compatible server URL, with or without /v1.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Served model name. Defaults to /v1/models[0].id.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key. Defaults to OPENAI_API_KEY or EMPTY.",
    )
    parser.add_argument(
        "--data-path",
        default=None,
        help="Optional local OCRBench TSV path with index/image/question/answer/category fields.",
    )
    parser.add_argument(
        "--ocrbench-url",
        default=OCRBENCH_URL,
        help="Full OCRBench TSV URL used when --data-path and --mini are not set.",
    )
    parser.add_argument(
        "--ocrbench-mini-url",
        default=OCRBENCH_MINI_URL,
        help="Mini OCRBench TSV URL used when --mini is set and --data-path is not set.",
    )
    parser.add_argument(
        "--cache-path",
        default=None,
        help="Local cache path for downloaded OCRBench TSV.",
    )
    parser.add_argument(
        "--mini",
        action="store_true",
        help="Use the OCRBench_MINI TSV URL/cache instead of the full OCRBench TSV.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start offset in the loaded TSV.",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=None,
        help="Number of examples to evaluate after --start-index.",
    )
    parser.add_argument(
        "--num-threads",
        type=int,
        default=8,
        help="Concurrent request threads.",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=20,
        help="Print progress every N completed requests; set 0 to disable.",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument(
        "--extra-body-json",
        type=parse_json_object,
        default=None,
        help=(
            "JSON object passed as OpenAI extra_body, e.g. "
            '\'{"chat_template_kwargs":{"enable_thinking":false}}\'.'
        ),
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument(
        "--disable-proxy-bypass",
        action="store_true",
        help="Let httpx honor proxy environment variables instead of bypassing them.",
    )
    parser.add_argument(
        "--show-details", action="store_true", help="Print each result."
    )
    parser.add_argument(
        "--dump-json", default=None, help="Optional path to write metrics and details."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    records, dataset_path = load_records(args)
    selected = select_records(records, args.start_index, args.num_examples)
    result = run_eval(
        records=selected,
        sampler=make_openai_sampler(args),
        num_threads=args.num_threads,
        progress_interval=args.progress_interval,
    )

    for item in result.items:
        if args.show_details or not item.score or item.error:
            status = "OK" if item.score else "FAIL"
            print(
                f"[{item.index}] {status} category={item.category!r} "
                f"expected={item.expected_answers}"
            )
            print(f"question: {item.question}")
            if item.error:
                print(f"error: {item.error}")
            print(f"response: {item.response}\n")

    print(
        f"accuracy={result.accuracy:.4f} correct={result.correct} "
        f"total={result.total} request_errors={result.request_errors} "
        f"dataset={dataset_path}"
    )
    for key, value in result.scores.items():
        print(f"{key}: {value}")

    if args.dump_json:
        payload = {
            "accuracy": result.accuracy,
            "correct": result.correct,
            "total": result.total,
            "request_errors": result.request_errors,
            "scores": result.scores,
            "category_totals": result.category_totals,
            "dataset_path": dataset_path,
            "start_index": args.start_index,
            "num_examples": len(selected),
            "items": [asdict(item) for item in result.items],
        }
        dump_path = Path(args.dump_json)
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
