# Parity Triage

Use this when an LMDeploy model-support change runs end to end but differs from
the reference output. The goal is to localize the mismatch before changing model
code.

## Order Of Checks

1. Compare rendered prompt text and token ids first. If these differ, stay in
   tokenizer, chat template, processor, or placeholder expansion code.
2. Compare modality preprocessing outputs and metadata before looking at LLM
   decode. Check tensor shapes, dtype conversions, lengths, masks, and any
   per-item metadata that controls downstream modules.
3. Compare module-level numeric outputs against the reference for the newly
   ported component. Prefer the smallest component boundary that can be run
   deterministically.
4. Run TP=1 before TP>1. If TP=1 matches and TP>1 diverges, inspect sharding,
   packed/merged weight loading, all-reduce behavior, and runtime numerical
   drift before blaming preprocessing.
5. For generation text mismatches, find the first differing generated token.
   Compare logits or logprobs around that step; near-tied alternatives can make
   exact text equality too strict for TP or backend comparisons.
6. Keep deterministic generation settings while debugging: temperature zero or
   greedy-equivalent settings, fixed max tokens, same chat template kwargs, and
   the same backend/model revision.

## Evidence To Save

- prompt text and token-id comparison
- reference and LMDeploy output ids up to the first mismatch
- top candidate logits/logprobs at the first mismatch
- module-level max absolute/relative error when available
- TP/backend/config matrix, including which variants pass and fail
- exact caveat when logs or metrics prove queued concurrency but not actual
  batched model-forward execution

## vLLM Tensor Parity

When using vLLM as the reference runtime for tensor dumps:

- Save rendered prompt text and token ids once, then feed the same token ids to
  both engines. For vLLM, prefer token-id prompts such as `TokensPrompt` instead
  of relying on a second chat-template render.
- Use a real script file for vLLM experiments. Inline stdin scripts can fail
  when vLLM or Python multiprocessing spawn tries to re-import `__main__`.
- For vLLM V1 hooks, set `VLLM_ENABLE_V1_MULTIPROCESSING=0` before importing
  vLLM; otherwise the model forward may run in an engine-core subprocess and
  parent-process hooks will not fire.
- Keep the first pass deterministic and small: TP=1, one prompt, one generated
  token, `temperature=0` or greedy-equivalent sampling, short max model length,
  and constrained batch/token budgets.
- Hook comparable semantic boundaries, not necessarily identical module names:
  embeddings, each decoder layer, attention, sparse/indexer top-k output, final
  norm, and logits. Record shape, dtype, max/mean absolute error, relative
  error, cosine similarity, and generated token ids.
- Normalize expected runtime layout differences before judging drift. LMDeploy
  may keep a leading batch dimension while vLLM flattens tokens; vLLM sparse
  indexer buffers may be padded to `max_num_batched_tokens`; sparse top-k lists
  may differ in order while having identical per-row sets.
- If the vLLM recipe path cannot initialize because of backend, KV-cache, or
  kernel availability, document the exact failing configuration and use the
  closest runnable reference only as a scoped signal. Do not claim parity for an
  intended recipe path that did not run.

## Decision Rules

- Prompt or token mismatch means an input pipeline bug until proven otherwise.
- Module numeric mismatch at a newly ported boundary is usually a loader,
  tensor-layout, dtype, mask, or op-semantics issue.
- TP=1 parity with TP>1 text divergence is not enough to call the port wrong;
  inspect first-token logits and sharding/runtime paths.
- Exact generated text equality is a strong signal only after prompt parity,
  module parity, and the first differing token distribution have been checked.
