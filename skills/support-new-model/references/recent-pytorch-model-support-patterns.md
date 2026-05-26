# Recent PyTorch Model-Support Patterns

Use this after reading the target HF config and before writing model code. These
patterns come from LMDeploy PyTorch model-support PRs merged in the year before
2026-05-26, after the engine and multimodal paths changed substantially.

## Recent PR Map

- New or large model families: Qwen3.5 `#4351`, InternS1-Pro `#4318`,
  InternS2 Preview `#4575`, Qwen3-VL `#4093`, Qwen3-Next `#4039`,
  DeepSeek-v3.2 `#4026`, SDAR `#3922`, InternVL3.5-Flash `#3952`,
  GLM-4.5 `#3863`, GLM-4.1V `#3846`, GPT-OSS `#3820`, InternVL3-HF
  `#3633`/`#3765`.
- Model variants and maintenance: Qwen3.5 MTP `#4437`, GLM4.7 MTP `#4346`,
  GLM5 `#4355`, GLM4.7-Flash `#4320`, Qwen3 MoE EPLB `#3582`, Qwen3 fused
  MoE weights `#3672`, Qwen3 MoE YaRN/hf-overrides `#3757`, Kimi-K2 builder
  `#4069`.
- Compatibility follow-ups matter: Transformers 5 changes, chat-template
  fixes, long-context fixes, and hardware-specific checks often land after the
  first model PR.

## Implementation Patterns

- Start from a nearby working model, not from scratch. Recent support often
  composes existing pieces: InternS1-Pro reuses Qwen3-MoE text, Qwen3-VL
  vision, and a side time-series encoder; InternS2 Preview builds on Qwen3.5
  and InternS1-Pro; GLM variants reuse DeepSeek/Qwen-style MoE and MTP pieces.
- Treat `configuration/<model>.py` as first-class model support. Nested configs
  usually need quantization propagation into `text_config`, `cfg.hf_config`,
  `use_mrope`, recurrent/state shapes, check-env hooks, and draft/spec decoding
  mutations.
- Keep model registration exact and minimal: update `module_map.py` for
  architecture class names, `archs.py` for VLM support routing, and
  `vl/model/builder.py` only when a VLM preprocessor class is added.
- Use LMDeploy runtime primitives for the hot path: packed qkv/gate-up linear,
  fused MoE, backend attention, RMSNorm with residual, rotary helpers, and
  `StepContext` metadata instead of HF cache/mask objects.
- For VLMs, use new-style `VisionModel.preprocess(...)` and pass compact
  `MultiModalData` into the PyTorch input processor. Avoid legacy preprocess
  overrides unless the target checkout requires them.
- For side modalities, add the whole plumbing path: media IO, modality enum,
  special token ids, placeholder expansion, `MultiModalData`, `prepare_inputs`,
  side encoder module, and masked scatter into `inputs_embeds`.
- For MoE models, implement router semantics separately from expert execution:
  match softmax/noaux/grouped routing, preserve top-k normalization behavior,
  support per-expert and fused checkpoint layouts, and keep router replay/EPLB
  metadata scoped to sparse layers.
- For GatedDelta/linear-attention models, do not only add a model file. Add
  state shapes, recurrent cache handling, kernel/backend checks, and fallback
  behavior for unsupported devices.
- For MTP/spec decoding, add or reuse a separate `*_mtp.py`, draft-model config
  rewrite, `model_paradigm='ar_spec'`, spec proposer, and TP/quant edge-case
  handling.
- Hardware and quant support often changes config policy rather than model
  math: add check-env guards, Volta/Ascend fallbacks, FP8/AWQ ignore-layer
  rules, and dtype controls where the target model requires them.

## Validation Pattern

- First verify config resolution and architecture mapping without loading full
  weights.
- Then verify weight loading, especially packed QKV, gate/up, expert weights,
  tied `lm_head`, ignored layers, and nested-prefix renames.
- For VLM/side modalities, verify placeholder-token count equals produced
  embedding count before judging generation quality.
- For MoE, validate routed expert ids, top-k weights, EPLB/logical-to-physical
  mapping, and router replay shape when enabled.
- For recurrent or MTP models, test both prefill and decode; many failures only
  appear after the first generated token.
