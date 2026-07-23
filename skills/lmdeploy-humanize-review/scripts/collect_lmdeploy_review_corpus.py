#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_ROOT = "https://api.github.com"
DEFAULT_REPO = "InternLM/lmdeploy"
DEFAULT_START_DATE = "2026-01-01"
DEFAULT_OUT_NAME = "lmdeploy-review-corpus-2026.jsonl.gz"

AGENT_LOGIN_PATTERNS = [
    r"\[bot\]$",
    r"^dependabot",
    r"^renovate",
    r"^github-actions",
    r"^pre-commit-ci",
    r"^copilot",
    r"^claude",
    r"^codex",
    r"^cursor",
    r"^devin",
    r"^sweep",
    r"^greptile",
    r"^openhands",
    r"^aider",
    r"^codeium",
    r"^qodo",
    r"^coderabbit",
    r"[-_]agent$",
]

CATEGORY_PATTERNS = {
    "correctness": [
        r"\bbug\b",
        r"\bwrong\b",
        r"\berror\b",
        r"\bfix\b",
        r"\bcrash\b",
        r"\bfail",
        r"\bassert",
        r"\bcorner case\b",
        r"\bedge case\b",
        r"not correct",
        r"incorrect",
        r"\bregression\b",
        r"\bunexpected\b",
    ],
    "tests-ci": [
        r"\btest",
        r"\bpytest\b",
        r"\bci\b",
        r"\bunit test\b",
        r"\bintegration",
        r"\bcoverage\b",
        r"\bbenchmark",
        r"\bworkflow",
        r"\but\b",
        r"\be2e\b",
    ],
    "performance": [
        r"\bperf",
        r"\blatency\b",
        r"\bthroughput\b",
        r"\bslow",
        r"\bfast",
        r"\bbenchmark",
        r"\bprofile",
        r"\boverhead\b",
        r"\boptimiz",
        r"\bbenchmark\b",
        r"\bprofile\b",
        r"\bttft\b",
        r"\btpot\b",
        r"\btps\b",
    ],
    "gpu-kernel": [
        r"\bcuda\b",
        r"\btriton\b",
        r"\bkernel\b",
        r"\bcutlass\b",
        r"\bflashattention\b",
        r"\bflashmla\b",
        r"\bfa3\b",
        r"\bsm\d+",
        r"\bwarp\b",
        r"\bblock\b",
        r"\bfused\b",
    ],
    "distributed-concurrency": [
        r"\btp\b",
        r"\bdp\b",
        r"\bpp\b",
        r"\bep\b",
        r"\bnccl\b",
        r"\brank\b",
        r"\bworker\b",
        r"\bthread\b",
        r"\bprocess\b",
        r"\bmp\b",
        r"\blocking\b",
        r"\brace\b",
        r"\bhang\b",
        r"\bdeadlock\b",
        r"\bdistserve\b",
        r"\bproxy\b",
        r"\bzmq\b",
    ],
    "memory-cache": [
        r"\bmemory\b",
        r"\boom\b",
        r"\bkv\b",
        r"\bcache\b",
        r"\bpage\b",
        r"\bpool\b",
        r"\balloc",
        r"\bfree\b",
        r"\bgpu memory\b",
        r"\bblock_size\b",
        r"\bsession\b",
    ],
    "api-compat": [
        r"\bapi\b",
        r"\bopenai\b",
        r"\bcompatible\b",
        r"\bbackward",
        r"\bserver_args\b",
        r"\barg\b",
        r"\bcli\b",
        r"\bendpoint\b",
        r"\brequest\b",
        r"\bresponse\b",
        r"\bchat\b",
        r"\bcompletion\b",
        r"\bgenerate\b",
        r"\bpipeline\b",
        r"\bconfig\b",
    ],
    "models-quant": [
        r"\bmodel\b",
        r"\btokenizer\b",
        r"\bfp8\b",
        r"\bint4\b",
        r"\bawq\b",
        r"\bw4a16\b",
        r"\bquant",
        r"\bmoe\b",
        r"\bmrope\b",
        r"\battention\b",
        r"\blora\b",
        r"\badapter\b",
        r"\bchat template\b",
        r"\barch",
    ],
    "pytorch-backend": [
        r"\bpytorch\b",
        r"\bpt\b",
        r"\bmodel_agent\b",
        r"\bmodel_runner\b",
        r"\bengine\b",
        r"\bpaged_attention\b",
        r"\bgraph_runner\b",
    ],
    "turbomind-backend": [
        r"\bturbomind\b",
        r"\btm\b",
        r"\bcsrc\b",
        r"\btritonserver\b",
        r"\bweight\b",
        r"\bworkspace\b",
    ],
    "docs-examples": [
        r"\breadme\b",
        r"\bdoc",
        r"\bexample",
        r"\btutorial",
        r"\bcomment",
        r"\bguide",
        r"\bnotebook",
        r"\bbenchmark",
    ],
    "style-maintainability": [
        r"\bstyle\b",
        r"\bnit",
        r"\bcleanup\b",
        r"\brefactor\b",
        r"\brename\b",
        r"\bduplicate\b",
        r"\bsimpl",
        r"\bmaintain",
        r"\btyping\b",
        r"\btype hint\b",
        r"\bformat\b",
    ],
    "build-deps": [
        r"\bbuild\b",
        r"\bcmake\b",
        r"\bsetup\b",
        r"\binstall\b",
        r"\bdependency\b",
        r"\bpackage\b",
        r"\bversion\b",
        r"\bdocker\b",
        r"\bcmake\b",
        r"\bwheel\b",
        r"\bpyproject\b",
    ],
    "observability": [
        r"\blog\b",
        r"\bmetric",
        r"\bprometheus\b",
        r"\btrace\b",
        r"\bdebug\b",
        r"\bwarning\b",
        r"\bmessage\b",
        r"\bexception\b",
    ],
    "multimodal": [
        r"\bvlm\b",
        r"\bvision\b",
        r"\bimage\b",
        r"\bvideo\b",
        r"\bocr\b",
        r"\bvisual\b",
        r"\bmultimodal\b",
    ],
}

EXTENSION_LANGUAGE = {
    ".py": "python",
    ".pyi": "python",
    ".cu": "cuda",
    ".cuh": "cuda",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".sh": "shell",
    ".bash": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".rst": "rst",
    ".toml": "toml",
    ".txt": "text",
    ".ipynb": "notebook",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect human LMDeploy pull-request review threads."
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help="Inclusive UTC start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Inclusive UTC end date in YYYY-MM-DD format; defaults to now.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references",
    )
    parser.add_argument("--out-name", default=DEFAULT_OUT_NAME)
    parser.add_argument(
        "--include-agent-reviewers",
        action="store_true",
        help="Keep comments from bot or coding-agent accounts in the corpus.",
    )
    parser.add_argument(
        "--max-comment-pages",
        type=int,
        default=None,
        help="Debug limit for the global review-comments pagination.",
    )
    parser.add_argument(
        "--max-pr-pages",
        type=int,
        default=None,
        help="Debug limit for pull-request pagination.",
    )
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    return parser.parse_args()


def gh_token_from_cli() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    token = result.stdout.strip()
    return token or None


def parse_github_dt(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso_utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def is_agent_user(user: dict[str, Any] | None) -> bool:
    if not user:
        return True
    login = str(user.get("login") or "").lower()
    if str(user.get("type") or "").lower() == "bot":
        return True
    return any(re.search(pattern, login) for pattern in AGENT_LOGIN_PATTERNS)


def api_get(
    url: str, token: str | None, retry_count: int = 8
) -> tuple[Any, dict[str, str]]:
    if not url.startswith("http"):
        url = f"{API_ROOT}{url}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "lmdeploy-humanize-review-corpus",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    for attempt in range(retry_count):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload), {
                    k.lower(): v for k, v in response.headers.items()
                }
        except urllib.error.HTTPError as exc:
            remaining = exc.headers.get("X-RateLimit-Remaining")
            reset_at = exc.headers.get("X-RateLimit-Reset")
            if exc.code in {403, 429} and remaining == "0" and reset_at:
                sleep_s = max(int(reset_at) - int(time.time()) + 5, 5)
                print(f"rate limited; sleeping {sleep_s}s", file=sys.stderr)
                time.sleep(sleep_s)
                continue
            if exc.code >= 500 and attempt + 1 < retry_count:
                time.sleep(2**attempt)
                continue
            raise
        except (
            http.client.IncompleteRead,
            http.client.RemoteDisconnected,
            TimeoutError,
            socket.timeout,
            urllib.error.URLError,
        ):
            if attempt + 1 >= retry_count:
                raise
            time.sleep(2**attempt)
    raise RuntimeError(f"failed to fetch {url}")


def next_link(headers: dict[str, str]) -> str | None:
    link_header = headers.get("link", "")
    for part in link_header.split(","):
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None


def code_language_for_path(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in EXTENSION_LANGUAGE:
        return EXTENSION_LANGUAGE[suffix]
    if "/" in path and "." not in Path(path).name:
        return "extensionless"
    return suffix.lstrip(".") or "unknown"


def natural_language_hint(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh_or_cjk"
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[^\x00-\x7f]", text):
        return "non_ascii_other"
    return "en_or_ascii"


def categories_for_thread(thread: dict[str, Any]) -> list[str]:
    haystack_parts = [
        thread.get("path", ""),
        thread.get("diff_hunk", ""),
        thread.get("pull_request", {}).get("title", ""),
    ]
    haystack_parts.extend(comment.get("body", "") for comment in thread["comments"])
    haystack = "\n".join(haystack_parts).lower()
    labels = []
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(re.search(pattern, haystack) for pattern in patterns):
            labels.append(category)
    return labels or ["general-review"]


def compact_pull(pr: dict[str, Any]) -> dict[str, Any]:
    user = pr.get("user") or {}
    return {
        "number": pr["number"],
        "title": pr.get("title") or "",
        "state": pr.get("state"),
        "created_at": pr.get("created_at"),
        "updated_at": pr.get("updated_at"),
        "closed_at": pr.get("closed_at"),
        "merged_at": pr.get("merged_at"),
        "html_url": pr.get("html_url"),
        "author": {
            "login": user.get("login"),
            "type": user.get("type"),
            "is_agent": is_agent_user(user),
        },
    }


def compact_comment(comment: dict[str, Any]) -> dict[str, Any]:
    user = comment.get("user") or {}
    body = comment.get("body") or ""
    return {
        "id": comment.get("id"),
        "in_reply_to_id": comment.get("in_reply_to_id"),
        "created_at": comment.get("created_at"),
        "updated_at": comment.get("updated_at"),
        "html_url": comment.get("html_url"),
        "author": {
            "login": user.get("login"),
            "type": user.get("type"),
            "is_agent": is_agent_user(user),
            "association": comment.get("author_association"),
        },
        "body": body,
        "body_language_hint": natural_language_hint(body),
    }


def pr_number_from_comment(comment: dict[str, Any]) -> int:
    return int(str(comment["pull_request_url"]).rstrip("/").split("/")[-1])


def fetch_target_pulls(
    repo: str,
    token: str | None,
    start_dt: dt.datetime,
    end_dt: dt.datetime,
    max_pages: int | None,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    target_pulls: dict[int, dict[str, Any]] = {}
    seen_numbers: set[int] = set()
    stats = collections.Counter()

    chunk_start = start_dt
    while chunk_start <= end_dt:
        next_month = (
            dt.datetime(chunk_start.year + 1, 1, 1, tzinfo=dt.timezone.utc)
            if chunk_start.month == 12
            else dt.datetime(chunk_start.year, chunk_start.month + 1, 1, tzinfo=dt.timezone.utc)
        )
        chunk_end = min(end_dt, next_month - dt.timedelta(seconds=1))
        query = (
            f"repo:{repo} is:pr "
            f"created:{chunk_start.date().isoformat()}..{chunk_end.date().isoformat()}"
        )
        url = (
            f"{API_ROOT}/search/issues?q={urllib.parse.quote(query)}"
            "&sort=created&order=asc&per_page=100"
        )
        page = 0
        while url:
            page += 1
            if max_pages is not None and page > max_pages:
                break
            payload, headers = api_get(url, token)
            items = payload.get("items", [])
            stats["search_result_items_seen"] += len(items)
            if page == 1:
                stats["search_total_count_sum"] += int(payload.get("total_count", 0))
                print(
                    "searched PRs "
                    f"{chunk_start.date().isoformat()}..{chunk_end.date().isoformat()}: "
                    f"{payload.get('total_count', 0)}",
                    file=sys.stderr,
                )
            if not items:
                break

            for pr in items:
                number = int(pr["number"])
                if number in seen_numbers:
                    continue
                seen_numbers.add(number)
                created_at = parse_github_dt(pr["created_at"])
                if created_at < start_dt or created_at > end_dt:
                    continue

                stats["window_prs"] += 1
                compact = compact_pull(pr)
                if compact["author"]["is_agent"]:
                    stats["excluded_agent_prs"] += 1
                    continue
                stats["included_human_prs"] += 1
                stats[f"included_human_prs_{created_at.year}"] += 1
                target_pulls[number] = compact

            url = next_link(headers)
        chunk_start = next_month

    return target_pulls, dict(stats)


def fetch_review_threads(
    repo: str,
    token: str | None,
    target_pulls: dict[int, dict[str, Any]],
    start_dt: dt.datetime,
    include_agent_reviewers: bool,
    max_pages: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    encoded = urllib.parse.quote(repo, safe="/")
    since = urllib.parse.quote(start_dt.isoformat().replace("+00:00", "Z"))
    url = (
        f"{API_ROOT}/repos/{encoded}/pulls/comments"
        f"?sort=created&direction=asc&per_page=100&since={since}"
    )
    by_thread: dict[int, dict[str, Any]] = {}
    stats = collections.Counter()
    page = 0

    while url:
        page += 1
        if max_pages is not None and page > max_pages:
            break
        comments, headers = api_get(url, token)
        if not comments:
            break
        if page % 25 == 0:
            print(
                "pulled review-comment page "
                f"{page}: {comments[0]['created_at']}..{comments[-1]['created_at']}",
                file=sys.stderr,
            )

        for comment in comments:
            stats["all_review_comments_seen"] += 1
            pr_number = pr_number_from_comment(comment)
            pull = target_pulls.get(pr_number)
            if pull is None:
                continue

            user_is_agent = is_agent_user(comment.get("user"))
            if user_is_agent:
                stats["agent_reviewer_comments_on_target_prs"] += 1
                if not include_agent_reviewers:
                    continue
            else:
                stats["human_reviewer_comments_on_target_prs"] += 1

            root_id = int(comment.get("in_reply_to_id") or comment["id"])
            thread = by_thread.get(root_id)
            if thread is None:
                thread = {
                    "schema_version": 1,
                    "source": {
                        "repo": repo,
                        "date_window": "configured_at_collection_time",
                        "collection": "github_pull_review_comments",
                    },
                    "thread_id": root_id,
                    "pull_request": pull,
                    "path": comment.get("path") or "",
                    "code_language": code_language_for_path(comment.get("path") or ""),
                    "diff_hunk": comment.get("diff_hunk") or "",
                    "commit_id": comment.get("commit_id"),
                    "original_commit_id": comment.get("original_commit_id"),
                    "line": comment.get("line"),
                    "original_line": comment.get("original_line"),
                    "start_line": comment.get("start_line"),
                    "original_start_line": comment.get("original_start_line"),
                    "side": comment.get("side"),
                    "subject_type": comment.get("subject_type"),
                    "comments": [],
                }
                by_thread[root_id] = thread
            elif not thread.get("diff_hunk") and comment.get("diff_hunk"):
                thread["diff_hunk"] = comment.get("diff_hunk") or ""
                thread["path"] = comment.get("path") or thread["path"]
                thread["code_language"] = code_language_for_path(thread["path"])

            thread["comments"].append(compact_comment(comment))

        url = next_link(headers)

    threads = []
    for thread in by_thread.values():
        thread["comments"].sort(key=lambda item: item["created_at"] or "")
        thread["categories"] = categories_for_thread(thread)
        thread["human_reviewer_comment_count"] = sum(
            1 for comment in thread["comments"] if not comment["author"]["is_agent"]
        )
        thread["agent_reviewer_comment_count"] = sum(
            1 for comment in thread["comments"] if comment["author"]["is_agent"]
        )
        thread["comment_language_hints"] = sorted(
            {comment["body_language_hint"] for comment in thread["comments"]}
        )
        threads.append(thread)

    threads.sort(
        key=lambda item: (
            item["pull_request"]["number"],
            item["comments"][0]["created_at"] if item["comments"] else "",
            item["thread_id"],
        )
    )
    stats["threads"] = len(threads)
    return threads, dict(stats)


def write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def summarize(
    threads: list[dict[str, Any]],
    pull_stats: dict[str, Any],
    comment_stats: dict[str, Any],
    repo: str,
    start_dt: dt.datetime,
    end_dt: dt.datetime,
    include_agent_reviewers: bool,
) -> dict[str, Any]:
    category_counts: collections.Counter[str] = collections.Counter()
    path_counts: collections.Counter[str] = collections.Counter()
    language_counts: collections.Counter[str] = collections.Counter()
    body_language_counts: collections.Counter[str] = collections.Counter()
    reviewer_counts: collections.Counter[str] = collections.Counter()
    pr_year_counts: collections.Counter[str] = collections.Counter()
    comments_per_thread: list[int] = []

    for thread in threads:
        for category in thread["categories"]:
            category_counts[category] += 1
        path_counts[thread["path"]] += 1
        language_counts[thread["code_language"]] += 1
        pr_year = thread["pull_request"]["created_at"][:4]
        pr_year_counts[pr_year] += 1
        comments_per_thread.append(len(thread["comments"]))
        for comment in thread["comments"]:
            body_language_counts[comment["body_language_hint"]] += 1
            if not comment["author"]["is_agent"]:
                reviewer_counts[comment["author"]["login"] or "unknown"] += 1

    return {
        "schema_version": 1,
        "repo": repo,
        "generated_at": iso_utc_now(),
        "source_date_window": [start_dt.isoformat(), end_dt.isoformat()],
        "collection_policy": {
            "pull_requests": "PR created_at within inclusive date window; bot and coding-agent PR authors excluded.",
            "review_comments": "GitHub pull review comments grouped by in_reply_to_id thread.",
            "agent_reviewers_included": include_agent_reviewers,
            "comment_text_policy": "Original comment bodies are preserved as UTF-8; no natural-language filter is applied.",
        },
        "pull_request_stats": pull_stats,
        "comment_stats": comment_stats,
        "thread_count": len(threads),
        "comment_count": sum(len(thread["comments"]) for thread in threads),
        "human_reviewer_comment_count": sum(
            thread["human_reviewer_comment_count"] for thread in threads
        ),
        "agent_reviewer_comment_count": sum(
            thread["agent_reviewer_comment_count"] for thread in threads
        ),
        "threads_by_pr_year": dict(sorted(pr_year_counts.items())),
        "top_categories": category_counts.most_common(20),
        "top_paths": path_counts.most_common(30),
        "code_languages": language_counts.most_common(),
        "comment_language_hints": body_language_counts.most_common(),
        "top_human_reviewers": reviewer_counts.most_common(30),
        "max_comments_per_thread": max(comments_per_thread, default=0),
    }


def write_summary_markdown(
    path: Path, metadata: dict[str, Any], corpus_name: str
) -> None:
    def table(rows: list[tuple[Any, Any]], left: str, right: str) -> list[str]:
        lines = [f"| {left} | {right} |", "| --- | ---: |"]
        lines.extend(f"| `{name}` | {count} |" for name, count in rows)
        return lines

    lines = [
        "# LMDeploy Human Review Corpus Summary",
        "",
        f"- Repo: `{metadata['repo']}`",
        f"- Source PR date window: `{metadata['source_date_window'][0]}` to `{metadata['source_date_window'][1]}` inclusive",
        f"- Generated at: `{metadata['generated_at']}`",
        f"- Corpus file: `{corpus_name}`",
        f"- Threads: `{metadata['thread_count']}`",
        f"- Comments in corpus: `{metadata['comment_count']}`",
        f"- Human reviewer comments: `{metadata['human_reviewer_comment_count']}`",
        f"- Agent reviewer comments: `{metadata['agent_reviewer_comment_count']}`",
        "",
        "## Collection Policy",
        "",
        "- Pull requests are selected by PR `created_at` in the requested date window.",
        "- Pull requests authored by GitHub bots or obvious coding-agent accounts are excluded.",
        "- Review comments are GitHub inline pull-review comments grouped by thread.",
        "- Comments by Copilot, GitHub bots, and obvious coding-agent accounts are excluded unless `--include-agent-reviewers` is used.",
        "- Comment bodies are kept in their original language; the corpus does not translate or drop non-English text.",
        "- `diff_hunk` stores the code context that produced each review thread.",
        "",
        "## Pull Request Stats",
        "",
    ]
    lines.extend(
        table(sorted(metadata["pull_request_stats"].items()), "Metric", "Count")
    )
    lines.extend(["", "## Comment Stats", ""])
    lines.extend(table(sorted(metadata["comment_stats"].items()), "Metric", "Count"))
    lines.extend(["", "## Top Categories", ""])
    lines.extend(table(metadata["top_categories"], "Category", "Threads"))
    lines.extend(["", "## Code Languages", ""])
    lines.extend(table(metadata["code_languages"], "Language", "Threads"))
    lines.extend(["", "## Comment Language Hints", ""])
    lines.extend(table(metadata["comment_language_hints"], "Hint", "Comments"))
    lines.extend(["", "## Top Paths", ""])
    lines.extend(table(metadata["top_paths"], "Path", "Threads"))
    lines.extend(["", "## Top Human Reviewers", ""])
    lines.extend(table(metadata["top_human_reviewers"], "Reviewer", "Comments"))
    lines.extend(
        [
            "",
            "## Query Examples",
            "",
            "```bash",
            "python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --query cuda --limit 5",
            "python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --path lmdeploy/pytorch --category correctness --limit 8",
            "python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --query 'turbomind' --format jsonl --limit 3",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    token = args.token or gh_token_from_cli()
    if not token:
        print(
            "warning: collecting through the rate-limited public GitHub API; "
            "set GITHUB_TOKEN or authenticate gh for higher limits",
            file=sys.stderr,
        )

    start_dt = dt.datetime.fromisoformat(args.start_date).replace(
        tzinfo=dt.timezone.utc
    )
    if args.end_date:
        end_dt = dt.datetime.fromisoformat(args.end_date).replace(
            hour=23, minute=59, second=59, tzinfo=dt.timezone.utc
        )
    else:
        end_dt = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"collecting PRs from {args.repo} created {start_dt.isoformat()}..{end_dt.isoformat()}",
        file=sys.stderr,
    )
    pulls, pull_stats = fetch_target_pulls(
        args.repo,
        token,
        start_dt,
        end_dt,
        args.max_pr_pages,
    )
    print(f"target human PRs: {len(pulls)}", file=sys.stderr)

    print("collecting global pull review comments", file=sys.stderr)
    threads, comment_stats = fetch_review_threads(
        args.repo,
        token,
        pulls,
        start_dt,
        args.include_agent_reviewers,
        args.max_comment_pages,
    )
    for thread in threads:
        thread["source"]["date_window"] = [start_dt.isoformat(), end_dt.isoformat()]

    corpus_path = args.out_dir / args.out_name
    metadata_path = args.out_dir / "lmdeploy-review-corpus-2026.metadata.json"
    summary_path = args.out_dir / "corpus-summary.md"

    write_jsonl_gz(corpus_path, threads)
    metadata = summarize(
        threads,
        pull_stats,
        comment_stats,
        args.repo,
        start_dt,
        end_dt,
        args.include_agent_reviewers,
    )
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_summary_markdown(summary_path, metadata, corpus_path.name)

    print(f"wrote {corpus_path}", file=sys.stderr)
    print(f"wrote {metadata_path}", file=sys.stderr)
    print(f"wrote {summary_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
