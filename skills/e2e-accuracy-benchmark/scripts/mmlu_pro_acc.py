#!/usr/bin/env python3
"""MMLU-Pro multiple-choice accuracy test for an OpenAI-compatible server."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

DEFAULT_DATASET_NAME = "TIGER-Lab/MMLU-Pro"
DEFAULT_SPLIT = "test"
CHOICES = list("ABCDEFGHIJKLMNOP")
LETTER_END = r"(?=$|[\s).,;:])"
ANSWER_PATTERN = re.compile(rf"(?i)\bANSWER\s*:\s*\(?([A-P])\)?{LETTER_END}")

MMLU_PRO_CATEGORIES = [
    "math",
    "physics",
    "chemistry",
    "law",
    "engineering",
    "other",
    "economics",
    "health",
    "psychology",
    "business",
    "biology",
    "philosophy",
    "computer science",
    "history",
]

MINI_MMLU_PRO = [
    {
        "question": "Which expression is equal to 2 multiplied by 6?",
        "options": [
            "2 + 6",
            "2 - 6",
            "2 x 6",
            "6 / 2",
            "2 / 6",
            "6 - 2",
            "2^6",
            "6^2",
            "12 + 2",
            "12 - 2",
        ],
        "answer": "C",
        "category": "math",
    },
    {
        "question": "Which organ pumps blood through the human body?",
        "options": [
            "Liver",
            "Heart",
            "Lung",
            "Kidney",
            "Stomach",
            "Spleen",
            "Pancreas",
            "Brain",
            "Skin",
            "Intestine",
        ],
        "answer": "B",
        "category": "health",
    },
    {
        "question": "In a market economy, prices most directly communicate what?",
        "options": [
            "Relative scarcity and demand",
            "The age of a product",
            "A legal verdict",
            "A chemical formula",
            "The mass of an item",
            "A calendar date",
            "A programming language",
            "A weather forecast",
            "A postal address",
            "A medical diagnosis",
        ],
        "answer": "A",
        "category": "economics",
    },
    {
        "question": "Which item is typically used to store key-value pairs in Python?",
        "options": [
            "list",
            "tuple",
            "set",
            "dictionary",
            "string",
            "integer",
            "float",
            "module",
            "package",
            "comment",
        ],
        "answer": "D",
        "category": "computer science",
    },
]


@dataclass
class MMLUProRecord:
    index: int
    question: str
    options: list[str]
    answer: str
    category: str = "unknown"


@dataclass
class EvalItem:
    index: int
    question: str
    category: str
    expected_answer: str
    extracted_answer: str | None
    score: float
    response: str
    error: str | None = None


@dataclass
class EvalResult:
    correct: int
    total: int
    accuracy: float
    request_errors: int
    extraction_errors: int
    category_scores: dict[str, float]
    category_totals: dict[str, int]
    items: list[EvalItem]


def parse_options(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip() != "N/A"]

    if isinstance(value, str):
        text = value.strip()
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
            except (json.JSONDecodeError, SyntaxError, ValueError):
                continue
            if isinstance(parsed, (list, tuple)):
                return [
                    str(item).strip()
                    for item in parsed
                    if str(item).strip() != "N/A"
                ]

        labeled_options = []
        for line in text.splitlines():
            match = re.match(r"^\s*\(?([A-P])\)?[.)\s:-]+(.+?)\s*$", line)
            if match:
                labeled_options.append(match.group(2).strip())
        if labeled_options:
            return labeled_options
        if text:
            return [text]

    raise ValueError(f"Cannot parse options from {value!r}")


def normalize_answer(value: Any, options: list[str]) -> str:
    if isinstance(value, int):
        if 0 <= value < len(options):
            return CHOICES[value]
        raise ValueError(f"answer index {value} is outside options")

    text = str(value).strip()
    if not text:
        raise ValueError("empty answer")

    letter_match = re.match(r"^\(?([A-P])\)?(?:[.)\s:]|$)", text, re.IGNORECASE)
    if letter_match:
        letter = letter_match.group(1).upper()
        if letter in CHOICES[: len(options)]:
            return letter

    for idx, option in enumerate(options):
        if text == option or text == f"{CHOICES[idx]}. {option}":
            return CHOICES[idx]

    raise ValueError(f"Cannot normalize answer {value!r}")


def record_from_mapping(row: dict[str, Any], index: int) -> MMLUProRecord:
    if "question" not in row:
        raise ValueError(f"Missing question in record {index}")
    if "options" in row:
        options = parse_options(row["options"])
    elif "choices" in row:
        options = parse_options(row["choices"])
    else:
        raise ValueError(f"Missing options in record {index}")

    if "answer" in row:
        answer_value = row["answer"]
    elif "answer_index" in row:
        answer_value = row["answer_index"]
    elif "label" in row:
        answer_value = row["label"]
    else:
        raise ValueError(f"Missing answer in record {index}")

    return MMLUProRecord(
        index=index,
        question=str(row["question"]),
        options=options,
        answer=normalize_answer(answer_value, options),
        category=str(row.get("category") or "unknown"),
    )


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def read_json(path: str | Path, split: str | None = None) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if split and split in payload and isinstance(payload[split], list):
            return payload[split]
        for key in ("data", "records", "examples"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError(f"Unsupported JSON dataset shape in {path}")


def load_records(args) -> tuple[list[MMLUProRecord], str]:
    if args.mini:
        return [
            record_from_mapping(record, index)
            for index, record in enumerate(MINI_MMLU_PRO)
        ], "built-in mini"

    if args.data_path:
        path = Path(args.data_path).expanduser()
        raw_records = (
            read_jsonl(path)
            if path.suffix == ".jsonl"
            else read_json(path, args.split)
        )
        return [
            record_from_mapping(record, index)
            for index, record in enumerate(raw_records)
        ], str(path)

    try:
        from datasets import load_dataset
    except ImportError as e:
        raise RuntimeError(
            "Please install datasets or pass --data-path/--mini for MMLU-Pro."
        ) from e

    dataset = load_dataset(args.dataset_name, split=args.split)
    return [
        record_from_mapping(dict(record), index)
        for index, record in enumerate(dataset)
    ], f"{args.dataset_name}:{args.split}"


def split_examples(
    records: list[MMLUProRecord],
    num_shots: int,
    start_index: int = 0,
    num_examples: int | None = None,
) -> tuple[list[MMLUProRecord], list[MMLUProRecord]]:
    if len(records) <= num_shots:
        raise ValueError(f"Need more than {num_shots} records, got {len(records)}.")

    few_shot = records[:num_shots]
    eval_records = records[num_shots:]
    eval_records = eval_records[start_index:]
    if num_examples is not None:
        eval_records = eval_records[:num_examples]
    if not eval_records:
        raise ValueError("No evaluation records selected.")
    return few_shot, eval_records


def format_options(options: list[str]) -> str:
    return "\n".join(
        f"{CHOICES[idx]}. {option}" for idx, option in enumerate(options)
    )


def format_example(record: MMLUProRecord, include_answer: bool) -> str:
    text = f"Question:\n{record.question}\n\nOptions:\n{format_options(record.options)}"
    if include_answer:
        text += f"\n\nAnswer: {record.answer}"
    return text


def build_prompt(
    few_shot: Iterable[MMLUProRecord], record: MMLUProRecord, use_cot: bool = True
) -> str:
    answer_letters = "".join(CHOICES[: len(record.options)])
    instruction = (
        "Answer the following multiple choice question. "
        "The last line of your response must be exactly "
        f"'ANSWER: <LETTER>' where <LETTER> is one of {answer_letters}."
    )
    if use_cot:
        instruction += " Think step by step before answering."
    else:
        instruction += " Answer directly."

    examples = "".join(
        format_example(example, include_answer=True) + "\n\n" for example in few_shot
    )
    return (
        instruction + "\n\n" + examples + format_example(record, include_answer=False)
    )


def extract_answer(text: str, allowed_choices: list[str]) -> str | None:
    allowed = set(allowed_choices)
    for match in reversed(list(ANSWER_PATTERN.finditer(text))):
        if match.group(1).upper() in allowed:
            return match.group(1).upper()

    fallback_patterns = [
        rf"(?i)\banswer\s+is\s*\(?([A-P])\)?{LETTER_END}",
        rf"(?i)\bfinal\s+answer\s*(?:is|:)?\s*\(?([A-P])\)?{LETTER_END}",
        rf"(?i)\banswer\s*:\s*option\s+([A-P]){LETTER_END}",
    ]
    for pattern in fallback_patterns:
        for match in reversed(list(re.finditer(pattern, text))):
            if match.group(1).upper() in allowed:
                return match.group(1).upper()

    for line in reversed(text.splitlines()):
        match = re.fullmatch(r"\s*\(?([A-P])\)?[.)]?\s*", line)
        if match and match.group(1).upper() in allowed:
            return match.group(1).upper()
    return None


def aggregate_category_scores(
    items: list[EvalItem],
) -> tuple[dict[str, float], dict[str, int]]:
    correct_by_category = {category: 0 for category in MMLU_PRO_CATEGORIES}
    totals = {category: 0 for category in MMLU_PRO_CATEGORIES}
    for item in items:
        if item.category not in totals:
            totals[item.category] = 0
            correct_by_category[item.category] = 0
        totals[item.category] += 1
        correct_by_category[item.category] += int(item.score)

    scores = {
        category: correct_by_category[category] / total
        for category, total in totals.items()
        if total
    }
    return scores, totals


def run_eval(
    records: list[MMLUProRecord],
    sampler: Callable[[str], str],
    num_shots: int = 0,
    start_index: int = 0,
    num_examples: int | None = None,
    num_threads: int = 16,
    progress_interval: int = 20,
    use_cot: bool = True,
) -> EvalResult:
    few_shot, eval_records = split_examples(
        records,
        num_shots=num_shots,
        start_index=start_index,
        num_examples=num_examples,
    )
    items: list[EvalItem | None] = [None] * len(eval_records)

    def eval_one(_idx: int, record: MMLUProRecord) -> EvalItem:
        try:
            response = sampler(build_prompt(few_shot, record, use_cot=use_cot))
            error = None
        except Exception as e:
            response = ""
            error = repr(e)
        extracted = extract_answer(response, CHOICES[: len(record.options)])
        score = float(extracted == record.answer)
        return EvalItem(
            index=record.index,
            question=record.question,
            category=record.category,
            expected_answer=record.answer,
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
    request_errors = sum(1 for item in final_items if item.error)
    extraction_errors = sum(1 for item in final_items if item.extracted_answer is None)
    category_scores, category_totals = aggregate_category_scores(final_items)
    return EvalResult(
        correct=correct,
        total=total,
        accuracy=correct / total,
        request_errors=request_errors,
        extraction_errors=extraction_errors,
        category_scores=category_scores,
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
    parser = argparse.ArgumentParser(description="Run MMLU-Pro accuracy.")
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
        help="Optional local JSONL/JSON path with question/options/answer/category fields.",
    )
    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help="Hugging Face dataset name used when --data-path and --mini are not set.",
    )
    parser.add_argument(
        "--split",
        default=DEFAULT_SPLIT,
        help="Dataset split for Hugging Face or split-keyed local JSON.",
    )
    parser.add_argument(
        "--mini",
        action="store_true",
        help="Use the built-in tiny sample set instead of the full MMLU-Pro test set.",
    )
    parser.add_argument(
        "--num-shots",
        type=int,
        default=0,
        help="Few-shot examples taken from the start of the loaded data.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start offset after few-shot records.",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=None,
        help="Number of eval examples after --start-index.",
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
    parser.add_argument(
        "--no-cot",
        action="store_true",
        help="Ask for a direct answer instead of step-by-step reasoning.",
    )
    parser.add_argument("--max-tokens", type=int, default=2048)
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
    records, dataset_source = load_records(args)
    result = run_eval(
        records=records,
        sampler=make_openai_sampler(args),
        num_shots=args.num_shots,
        start_index=args.start_index,
        num_examples=args.num_examples,
        num_threads=args.num_threads,
        progress_interval=args.progress_interval,
        use_cot=not args.no_cot,
    )

    for item in result.items:
        if args.show_details or not item.score or item.error:
            status = "OK" if item.score else "FAIL"
            print(
                f"[{item.index}] {status} category={item.category!r} "
                f"expected={item.expected_answer} got={item.extracted_answer}"
            )
            print(f"question: {item.question}")
            if item.error:
                print(f"error: {item.error}")
            print(f"response: {item.response}\n")

    print(
        f"accuracy={result.accuracy:.4f} correct={result.correct} "
        f"total={result.total} request_errors={result.request_errors} "
        f"extraction_errors={result.extraction_errors} dataset={dataset_source}"
    )
    for category in sorted(result.category_scores):
        total = result.category_totals[category]
        print(
            f"{category}: accuracy={result.category_scores[category]:.4f} "
            f"total={total}"
        )

    if args.dump_json:
        payload = {
            "accuracy": result.accuracy,
            "correct": result.correct,
            "total": result.total,
            "request_errors": result.request_errors,
            "extraction_errors": result.extraction_errors,
            "category_scores": result.category_scores,
            "category_totals": result.category_totals,
            "dataset_source": dataset_source,
            "num_shots": args.num_shots,
            "start_index": args.start_index,
            "num_examples": result.total,
            "use_cot": not args.no_cot,
            "items": [asdict(item) for item in result.items],
        }
        dump_path = Path(args.dump_json)
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
