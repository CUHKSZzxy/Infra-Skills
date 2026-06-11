# LMDeploy Human Review Corpus Summary

- Repo: `InternLM/lmdeploy`
- Source PR date window: `2026-01-01T00:00:00+00:00` to `2026-06-11T04:06:41+00:00` inclusive
- Generated at: `2026-06-11T04:07:24+00:00`
- Corpus file: `lmdeploy-review-corpus-2026.jsonl.gz`
- Threads: `421`
- Comments in corpus: `533`
- Human reviewer comments: `533`
- Agent reviewer comments: `0`

## Collection Policy

- Pull requests are selected by PR `created_at` in the requested date window.
- Pull requests authored by GitHub bots or obvious coding-agent accounts are excluded.
- Review comments are GitHub inline pull-review comments grouped by thread.
- Comments by Copilot, GitHub bots, and obvious coding-agent accounts are excluded unless `--include-agent-reviewers` is used.
- Comment bodies are kept in their original language; the corpus does not translate or drop non-English text.
- `diff_hunk` stores the code context that produced each review thread.

## Pull Request Stats

| Metric | Count |
| --- | ---: |
| `excluded_agent_prs` | 6 |
| `included_human_prs` | 318 |
| `included_human_prs_2026` | 318 |
| `search_result_items_seen` | 324 |
| `search_total_count_sum` | 324 |
| `window_prs` | 324 |

## Comment Stats

| Metric | Count |
| --- | ---: |
| `agent_reviewer_comments_on_target_prs` | 1115 |
| `all_review_comments_seen` | 1746 |
| `human_reviewer_comments_on_target_prs` | 533 |
| `threads` | 421 |

## Top Categories

| Category | Threads |
| --- | ---: |
| `models-quant` | 225 |
| `api-compat` | 223 |
| `pytorch-backend` | 200 |
| `correctness` | 161 |
| `turbomind-backend` | 132 |
| `style-maintainability` | 124 |
| `docs-examples` | 124 |
| `memory-cache` | 124 |
| `tests-ci` | 114 |
| `distributed-concurrency` | 92 |
| `gpu-kernel` | 84 |
| `build-deps` | 79 |
| `performance` | 74 |
| `observability` | 69 |
| `multimodal` | 67 |
| `general-review` | 2 |

## Code Languages

| Language | Threads |
| --- | ---: |
| `python` | 310 |
| `yaml` | 63 |
| `cpp` | 16 |
| `markdown` | 15 |
| `text` | 8 |
| `cuda` | 6 |
| `shell` | 3 |

## Comment Language Hints

| Hint | Comments |
| --- | ---: |
| `en_or_ascii` | 445 |
| `non_ascii_other` | 88 |

## Top Paths

| Path | Threads |
| --- | ---: |
| `lmdeploy/serve/openai/api_server.py` | 17 |
| `lmdeploy/pytorch/spec_decode/spec_agent.py` | 14 |
| `lmdeploy/serve/openai/responses/serving.py` | 13 |
| `lmdeploy/serve/core/async_engine.py` | 10 |
| `.github/workflows/api_eval_legacy.yml` | 10 |
| `lmdeploy/serve/processors/multimodal.py` | 9 |
| `lmdeploy/pytorch/engine/logits_process.py` | 8 |
| `lmdeploy/turbomind/models/mixtral.py` | 8 |
| `lmdeploy/messages.py` | 7 |
| `lmdeploy/pytorch/engine/model_agent/agent.py` | 6 |
| `lmdeploy/pytorch/spec_decode/proposers/eagle3.py` | 6 |
| `lmdeploy/pytorch/backends/cuda/graph_runner.py` | 6 |
| `src/turbomind/generation/guided_decoding.cc` | 6 |
| `lmdeploy/turbomind/__init__.py` | 6 |
| `lmdeploy/pytorch/backends/dlinfer/ascend/op_backend.py` | 5 |
| `lmdeploy/serve/parsers/_openai_harmony.py` | 5 |
| `lmdeploy/vl/model/base.py` | 5 |
| `benchmark/benchmark_guided.py` | 5 |
| `lmdeploy/lite/apis/auto_awq.py` | 5 |
| `.github/workflows/benchmark_legacy.yml` | 4 |
| `.github/workflows/daily_ete_test_legacy.yml` | 4 |
| `lmdeploy/pytorch/engine/executor/base.py` | 4 |
| `docs/en/advance/spec_decoding.md` | 4 |
| `lmdeploy/lite/apis/calibrate.py` | 4 |
| `lmdeploy/lite/quantization/awq.py` | 4 |
| `lmdeploy/turbomind/models/qwen3_5.py` | 4 |
| `lmdeploy/pytorch/backends/cuda/attention/__init__.py` | 3 |
| `lmdeploy/cli/utils.py` | 3 |
| `lmdeploy/cli/lite.py` | 3 |
| `lmdeploy/model.py` | 3 |

## Top Human Reviewers

| Reviewer | Comments |
| --- | ---: |
| `lvhan028` | 259 |
| `windreamer` | 87 |
| `RunningLeon` | 46 |
| `grimoire` | 42 |
| `CUHKSZzxy` | 38 |
| `lzhangzz` | 13 |
| `irexyc` | 11 |
| `lapy` | 6 |
| `yao-fengchen` | 5 |
| `zhulinJulia24` | 5 |
| `hd9568` | 5 |
| `jinminxi104` | 3 |
| `ziyangliu-666` | 3 |
| `zh-nj` | 2 |
| `CyCle1024` | 2 |
| `Tsundoku958` | 2 |
| `ZhijunLStudio` | 2 |
| `43758726` | 1 |
| `SuperMarioYL` | 1 |

## Query Examples

```bash
python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --query cuda --limit 5
python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --path lmdeploy/pytorch --category correctness --limit 8
python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --query 'turbomind' --format jsonl --limit 3
```
