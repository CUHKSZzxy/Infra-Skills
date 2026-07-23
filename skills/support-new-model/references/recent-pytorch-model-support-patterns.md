# Recent PyTorch Model-Support Patterns

Use this after reading the target HF config and before writing model code. These
patterns come from LMDeploy PyTorch model-support PRs merged in the year before
2026-06-16, after the engine and multimodal paths changed substantially.

## Recent PR Map

This table intentionally excludes Ascend-only work, Turbomind-only work, bug
fixes, and small compatibility/variant PRs. Use it for substantial PyTorch
model-adaptation examples.

| PR | Area | Main pattern |
| --- | --- | --- |
| `#4652` | Qwen3.5 MTP | Keep MTP fixes coordinated across config, cudagraph, paging state, spec agent, and graph runner |
| `#4411` | Qwen3 Omni | Add audio/multimodal plumbing end-to-end: config, model map, media IO, processor, PyTorch model, VLM wrapper, and tests |
| `#4611` | Qwen3.5 MTP DP | Make speculative/MTP support DP-aware across token dispatch, model-agent inputs, graph runner, and spec strategy state |
| `#4575` | InternS2 Preview | Compose Qwen3.5 plus InternS1-Pro paths; keep nested configs and side modules |
| `#4437` | Qwen3.5 MTP | Separate `*_mtp.py`, spec config, recurrent state handling |
| `#4351` | Qwen3.5 | GatedDelta/linear-attn state shapes, VLM, MoE, config builder |
| `#4355` | GLM5 | Reuse DeepSeek-v3.2-style model/config mapping |
| `#4346` | GLM4.7 MTP | Reuse DeepSeek MTP path plus GLM config/model map |
| `#4320` | GLM-4.7-Flash | Reuse DeepSeek/Qwen-style PyTorch components |
| `#4318` | InternS1-Pro | Qwen3-MoE text plus Qwen3-VL vision plus time-series side encoder |
| `#4093` | Qwen3-VL / VL-MoE | New-style VLM preprocess, M-RoPE, vision scatter |
| `#4039` | Qwen3-Next | GatedDelta/recurrent cache model support |
| `#4026` | DeepSeek-v3.2 | MLA/NSA/backend kernels plus model/config registration |
| `#3922` | SDAR / SDAR-MoE | New PyTorch strategy/model family |
| `#3952` | InternVL3.5-Flash | VLM model-agent and preprocessor adaptation |
| `#3863` | GLM-4.5 | MoE model file and module map |
| `#3846` | GLM-4-0414 / GLM-4.1V | Text plus VLM model/preprocessor registration |
| `#3820` | GPT-OSS bf16 | MoE/attention backend plus model/config |
| `#3765` | InternVL PyTorch | InternVL3 HF config/model/VLM path |
| `#3633` | InternVL3-8B-HF | Initial InternVL3 HF PyTorch support |

Compatibility follow-ups still matter, but keep them out of the model-support
map unless they introduce a substantial reusable architecture pattern.

## Implementation Patterns

- Start from a nearby working model, not from scratch. Recent support often
  composes existing pieces: InternS1-Pro reuses Qwen3-MoE text, Qwen3-VL
  vision, and a side time-series encoder; InternS2 Preview builds on Qwen3.5
  and InternS1-Pro; GLM variants reuse DeepSeek/Qwen-style MoE and MTP pieces.
- Treat `lmdeploy/pytorch/configurations/<model>.py` as first-class model
  support. Nested configs usually need quantization propagation into
  `text_config`, `cfg.hf_config`, `use_mrope`, recurrent/state shapes,
  check-env hooks, and draft/spec decoding mutations.
- Keep model registration exact and minimal: update `module_map.py` for
  architecture class names, `archs.py` for VLM support routing, and
  `vl/model/builder.py` only when a VLM preprocessor class is added.
- Use LMDeploy runtime primitives for the hot path: packed qkv/gate-up linear,
  fused MoE, backend attention, RMSNorm with residual, rotary helpers, and
  `StepContext` metadata instead of HF cache/mask objects.
- For VLMs, use new-style `VisionModel.preprocess(...)` and pass compact
  `MultiModalData` into the PyTorch input processor. Avoid legacy preprocess
  overrides unless the target checkout requires them.
- For multimodal models, prefer shared placeholder-expansion and media-merge
  utilities over duplicating prompt expansion in each model wrapper.
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
- For DP plus speculative/MTP paths, include at least one state/dispatch test
  that proves model-agent inputs, token dispatch, and spec-agent bookkeeping
  agree on batch and rank layout.
