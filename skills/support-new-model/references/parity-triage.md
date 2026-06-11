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

## Decision Rules

- Prompt or token mismatch means an input pipeline bug until proven otherwise.
- Module numeric mismatch at a newly ported boundary is usually a loader,
  tensor-layout, dtype, mask, or op-semantics issue.
- TP=1 parity with TP>1 text divergence is not enough to call the port wrong;
  inspect first-token logits and sharding/runtime paths.
- Exact generated text equality is a strong signal only after prompt parity,
  module parity, and the first differing token distribution have been checked.
