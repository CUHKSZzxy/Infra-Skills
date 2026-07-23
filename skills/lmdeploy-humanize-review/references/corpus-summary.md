# LMDeploy Human Review Corpus Summary

- Repo: `InternLM/lmdeploy`
- Source PR date window: `2026-01-01T00:00:00+00:00` to `2026-07-17T12:30:47+00:00` inclusive
- Generated at: `2026-07-17T12:31:38+00:00`
- Corpus file: `lmdeploy-review-corpus-2026.jsonl.gz`
- Threads: `495`
- Comments in corpus: `620`
- Human reviewer comments: `620`
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
| `excluded_agent_prs` | 8 |
| `included_human_prs` | 397 |
| `included_human_prs_2026` | 397 |
| `search_result_items_seen` | 405 |
| `search_total_count_sum` | 405 |
| `window_prs` | 405 |

## Comment Stats

| Metric | Count |
| --- | ---: |
| `agent_reviewer_comments_on_target_prs` | 1273 |
| `all_review_comments_seen` | 1991 |
| `human_reviewer_comments_on_target_prs` | 620 |
| `threads` | 495 |

## Top Categories

| Category | Threads |
| --- | ---: |
| `api-compat` | 257 |
| `models-quant` | 254 |
| `pytorch-backend` | 231 |
| `correctness` | 188 |
| `turbomind-backend` | 154 |
| `docs-examples` | 144 |
| `memory-cache` | 142 |
| `style-maintainability` | 136 |
| `tests-ci` | 131 |
| `distributed-concurrency` | 102 |
| `gpu-kernel` | 97 |
| `multimodal` | 88 |
| `build-deps` | 86 |
| `performance` | 80 |
| `observability` | 75 |
| `general-review` | 2 |

## Code Languages

| Language | Threads |
| --- | ---: |
| `python` | 362 |
| `yaml` | 66 |
| `markdown` | 21 |
| `cpp` | 20 |
| `text` | 9 |
| `shell` | 7 |
| `cuda` | 6 |
| `jetson` | 2 |
| `extensionless` | 1 |
| `ps1` | 1 |

## Comment Language Hints

| Hint | Comments |
| --- | ---: |
| `en_or_ascii` | 524 |
| `non_ascii_other` | 95 |
| `zh_or_cjk` | 1 |

## Top Paths

| Path | Threads |
| --- | ---: |
| `lmdeploy/serve/openai/api_server.py` | 18 |
| `lmdeploy/pytorch/spec_decode/spec_agent.py` | 14 |
| `lmdeploy/serve/openai/responses/serving.py` | 13 |
| `lmdeploy/serve/core/async_engine.py` | 12 |
| `lmdeploy/serve/processors/multimodal.py` | 10 |
| `.github/workflows/api_eval_legacy.yml` | 10 |
| `lmdeploy/pytorch/engine/model_agent/agent.py` | 9 |
| `lmdeploy/pytorch/engine/logits_process.py` | 8 |
| `lmdeploy/turbomind/models/mixtral.py` | 8 |
| `lmdeploy/messages.py` | 7 |
| `lmdeploy/vl/model/base.py` | 7 |
| `src/turbomind/generation/guided_decoding.cc` | 7 |
| `lmdeploy/pytorch/engine/executor/base.py` | 6 |
| `lmdeploy/pytorch/spec_decode/proposers/eagle3.py` | 6 |
| `lmdeploy/pytorch/backends/cuda/graph_runner.py` | 6 |
| `lmdeploy/turbomind/__init__.py` | 6 |
| `lmdeploy/pytorch/backends/dlinfer/ascend/op_backend.py` | 5 |
| `lmdeploy/serve/parsers/_openai_harmony.py` | 5 |
| `lmdeploy/serve/openai/protocol.py` | 5 |
| `benchmark/benchmark_guided.py` | 5 |
| `lmdeploy/lite/apis/auto_awq.py` | 5 |
| `lmdeploy/cli/utils.py` | 4 |
| `.github/workflows/benchmark_legacy.yml` | 4 |
| `.github/workflows/daily_ete_test_legacy.yml` | 4 |
| `docs/en/advance/spec_decoding.md` | 4 |
| `lmdeploy/lite/apis/calibrate.py` | 4 |
| `lmdeploy/lite/quantization/awq.py` | 4 |
| `lmdeploy/turbomind/models/qwen3_5.py` | 4 |
| `lmdeploy/pytorch/backends/cuda/attention/__init__.py` | 3 |
| `lmdeploy/pipeline.py` | 3 |

## Top Human Reviewers

| Reviewer | Comments |
| --- | ---: |
| `lvhan028` | 292 |
| `windreamer` | 87 |
| `RunningLeon` | 64 |
| `grimoire` | 51 |
| `CUHKSZzxy` | 50 |
| `irexyc` | 16 |
| `lzhangzz` | 13 |
| `lapy` | 6 |
| `yao-fengchen` | 5 |
| `zhulinJulia24` | 5 |
| `hd9568` | 5 |
| `yimdev` | 4 |
| `jinminxi104` | 3 |
| `ziyangliu-666` | 3 |
| `zh-nj` | 2 |
| `CyCle1024` | 2 |
| `Tsundoku958` | 2 |
| `ZhijunLStudio` | 2 |
| `waynehacking8` | 2 |
| `chuenchen309` | 2 |
| `43758726` | 1 |
| `SuperMarioYL` | 1 |
| `Shylin26` | 1 |
| `littlegy` | 1 |

## Query Examples

```bash
python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --query cuda --limit 5
python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --path lmdeploy/pytorch --category correctness --limit 8
python3 skills/lmdeploy-humanize-review/scripts/query_lmdeploy_review_corpus.py --query 'turbomind' --format jsonl --limit 3
```
