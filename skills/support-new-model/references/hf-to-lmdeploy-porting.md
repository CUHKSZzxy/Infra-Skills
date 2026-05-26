# HF To LMDeploy Porting Notes

Use this when comparing a Hugging Face Transformers implementation with an
LMDeploy PyTorch backend model. The goal is not to copy HF forward code; the
goal is to preserve the checkpoint contract while replacing inference-time ops
with LMDeploy runtime primitives.

## Porting Shape

1. Keep HF parameter names in mind, then decide which runtime modules should be
   packed or fused in LMDeploy.
2. Build LMDeploy modules around backend-aware helpers, not raw `nn.Linear`
   except where no LMDeploy helper exists.
3. Move mask, cache, position, and multimodal bookkeeping out of HF-style
   forward code and into `StepContext`, input processors, and attention
   metadata.
4. Make `load_weights()` bridge the HF checkpoint names into the packed
   LMDeploy parameter names.
5. Verify weight loading before debugging generation quality.

## Common Operator Replacements

| HF pattern | LMDeploy pattern |
| --- | --- |
| separate `q_proj`, `k_proj`, `v_proj` | `build_qkv_proj(...)` plus `split_qkv(...)` |
| separate `gate_proj`, `up_proj` | `build_gateup_linear(...)` |
| `act(gate_proj(x)) * up_proj(x)` | `SiluAndMul` or the matching fused activation |
| output/down projection | `build_o_proj(...)` or `build_down_linear(...)` |
| `nn.Embedding` | `build_embedding(...)` |
| RMSNorm, optionally after residual add | `RMSNorm(...).forward(x, residual)` |
| HF rotary helper functions | `build_rotary_embedding_from_config(...)` and `ApplyRotaryEmb` when supported |
| HF cache update and attention mask | `Attention(..., k_cache, v_cache, attn_metadata)` |
| HF `GenerationMixin.prepare_inputs_for_generation` | model `prepare_inputs_for_generation(..., context=StepContext)` |
| Python expert loop with `index_add_` | `build_fused_moe(...)` with routed top-k ids and weights |
| router `softmax` plus `topk` | `SoftmaxTopK` or a model-specific router helper such as `NoauxTCRouter` |
| `experts.<id>.gate_proj/up_proj/down_proj` | `experts.gate_up` and `experts.down` with expert id and shard id loaders |
| HF side encoder for a non-text modality | separate LMDeploy module plus `MultiModalData` and masked scatter into `inputs_embeds` |
| HF placeholder expansion for side features | `VisionModel.preprocess(...)` or a custom modality processor that emits exact token spans |

## Dense LLM Checklist

- Build `Attention`, `MLP`, `DecoderLayer`, base `Model`, and `ForCausalLM`.
- In attention, flatten packed QKV to `(-1, heads, head_dim)` before
  `split_qkv`; apply any q/k norm before rotary.
- Let backend `Attention` handle KV-cache fill, paged decode, and prefill
  dispatch. Do not recreate HF causal masks inside the model.
- Return hidden states from `forward`; let `DeployModelMixinV1.get_logits()`
  apply `lm_head`.
- Add `packed_modules_mapping` for every packed projection so quant and weight
  utilities understand the relationship.
- In `load_weights()`, skip rotary cache tensors and tied `lm_head.weight`
  when appropriate, then map each HF shard to the packed parameter with the
  correct shard id.

## MoE Checklist

- Read MoE config fields: `decoder_sparse_step`, `mlp_only_layers`,
  `moe_intermediate_size`, `num_experts`, `num_experts_per_tok`,
  `norm_topk_prob`, router grouping/scoring fields, shared expert fields, and
  EP/EPLB flags.
- Mirror HF sparse-vs-dense layer predicates exactly; dense layers should keep
  the dense MLP path while sparse layers use fused MoE.
- For Qwen-style softmax routers, build the gate as non-TP linear from hidden
  dim to number of experts, call `SoftmaxTopK`, and pass `norm_topk_prob` as
  `renormalize` to `build_fused_moe`.
- For other router families, use the matching router helper such as
  `NoauxTCRouter` instead of assuming softmax top-k.
- Replace HF expert Python loops with
  `build_fused_moe(hidden_dim, moe_intermediate_size, num_experts, top_k, ...)`.
- Add expert loader mapping for every expert id: gate/up load into
  `experts.gate_up` with shard ids `gate`/`up`; down loads into
  `experts.down` with shard id `down`.
- Handle both checkpoint layouts when present: per-expert
  `experts.<id>.*_proj` and fused tensors such as `fused_w1w3`/`fused_w2` or
  `experts.gate_up_proj`/`experts.down_proj`; check transpose and chunk order
  before loading.
- If router replay or expert tracing is enabled, only sparse blocks should
  write routed experts; dense MLP paths must ignore replay metadata or avoid
  receiving it.
- For VLM-MoE, reuse VLM preprocessing and vision code when only the text tower
  is MoE; swap the language model and keep M-RoPE/deepstack handling.
- For EP/EPLB, confirm logical-to-physical expert id mapping and per-rank
  expert-list loaders before blaming kernel output.

## VLM Checklist

- Keep HF processor usage in `lmdeploy/vl/model/<model>.py` when possible; use
  LMDeploy `VisionModel.preprocess(...)` to collect processor outputs and
  placeholder offsets.
- Convert processor outputs into `MultiModalData` in the PyTorch model input
  processor. Store feature tensors, token ranges, modality token ids, and grid
  metadata needed at runtime.
- For M-RoPE models, set `cfg.use_mrope = True` in the config builder and
  attach per-token `mrope_pos_ids` to `MultiModalData` instead of passing HF
  `mm_token_type_ids` through model forward.
- Build the vision encoder with backend helpers for linear/attention where
  possible, but keep simple ops such as patch `Conv3d` when they are part of
  the checkpoint contract.
- In `prepare_inputs_for_generation`, build the compact tensors needed by
  forward: pixel/video tensors, multimodal masks, grid metadata, vision
  cu-seqlens, and precomputed vision position embeddings.
- Scatter vision embeddings into token embeddings with the multimodal mask,
  then pass only the resulting `inputs_embeds` plus compact metadata to the
  language model.

## Side Encoder / Time-Series Checklist

- Read the side-module config first, such as `ts_config`, token ids,
  start/end tokens, input feature dimensions, downsampling strides, projector
  output size, and any sampling-rate dependent formulas.
- Keep transport, preprocessing, embedding, and language-model scatter as
  separate steps. Media IO decodes raw payloads; the VLM preprocessor
  normalizes/truncates and expands placeholders; the PyTorch side module
  produces embeddings; the main model scatters them into `inputs_embeds`.
- If the modality is new to LMDeploy, add it consistently to `Modality`,
  `VisionModel.ATTR_NAME_TO_MODALITY`, `VisionModel.FEATURE_NAMES`,
  `MultimodalSpecialTokens`, the serve multimodal parser, and the PyTorch
  input processor's `MultiModalData` conversion.
- Preserve the HF token-count formula exactly. For time-series modules this
  often combines sampling rate, patch size, stride, and later subsampling; the
  number of placeholder tokens must equal the number of embeddings scattered.
- Build reusable side encoders as separate modules, for example
  `<model>_time_series.py`. Use LMDeploy linear/norm helpers for checkpointed
  projections, but keep simple checkpoint-compatible ops such as `Conv1d`,
  positional buffers, and local transformer/Whisper blocks when no backend
  replacement exists.
- When weights or full LLM integration are not available yet, first land the
  side encoder as a standalone module with a focused parity test against the HF
  or research reference. Validate each checkpointed submodule plus end-to-end
  output on GPU when possible, and report both max absolute diff and shape or
  length equality. Treat large relative diff near zero-valued reference outputs
  as secondary to the absolute tolerance.
- Port inference-only modules, not training APIs. Drop `freeze` flags,
  `self.training` branches, dropout, output-attention/hidden-state flags,
  `return_dict` variants, and dead modes such as unused self-attention or
  index-return branches unless the target runtime path actually consumes them.
- Prefer explicit constructor `dtype` and `device` arguments, then store them on
  `self.dtype` and `self.device` when later submodules need consistent tensor
  creation. Do not invent helper factories such as `_resolve_factory_kwargs`
  unless the local LMDeploy model files already use that pattern.
- If a side encoder depends on a common HF block such as BERT, replace it with
  a local LMDeploy inference implementation when practical instead of keeping a
  runtime dependency on `transformers.BertModel`. Keep names aligned with the
  HF checkpoint contract, and remove project-specific prefixes that are not in
  the real HF state dict.
- Order standalone encoder files bottom-up: small helpers first, composite
  encoders next, and the top-level chunk/model wrapper at the bottom.
- In `prepare_inputs_for_generation`, collect side-modality `MultiModalData`
  by modality, concatenate feature tensors and metadata such as lengths or
  sampling rates, and build one multimodal mask from the side token id.
- In model `forward`, compute side embeddings only when raw side inputs are
  present, then scatter into token embeddings with the multimodal mask before
  calling the language model.
- For models that use M-RoPE for image/video, explicitly decide whether the
  side modality participates. InternS1-Pro-style time-series inputs use normal
  text positions while image/video still use M-RoPE.
- Store the original nested HF config on `cfg.hf_config` when the runtime
  wrapper needs non-text configs such as `vision_config` or `ts_config` after
  the model config builder derives text-engine fields.

## Registration And Config

- `module_map.py` maps the exact HF architecture class name to the LMDeploy
  PyTorch class.
- VLMs also need `lmdeploy/archs.py`, `lmdeploy/vl/model/builder.py`, and a
  `VISION_MODELS` registration.
- For nested HF configs, make a config builder that copies quantization config
  into the text config when needed and stores the original HF config on
  `cfg.hf_config`.

## Review Traps

- Do not assume HF `attention_mask` or `Cache` objects exist in LMDeploy model
  forward. Check `StepContext` and backend attention metadata instead.
- Do not leave HF q/k/v or gate/up parameter names in `named_parameters()` after
  packing unless `load_weights()` intentionally renames them.
- Do not normalize top-k weights twice. Qwen-style router returns top-k probs,
  and LMDeploy fused MoE can renormalize based on `norm_topk_prob`.
- Do not assume one checkpoint layout for MoE expert weights. Qwen3-MoE and
  Qwen3-VL-MoE loaders support different fused expert layouts.
- Do not duplicate VLM code for VLM-MoE when the text tower can inherit MoE and
  the VLM wrapper can be reused.
- Do not let side-modality placeholder count drift from side-encoder output
  length. A mismatch may only surface as a masked-scatter shape error during
  prefill.
- Do not assume image/video M-RoPE handling also applies to scientific side
  modalities. Check scheduler position-id logic for each modality.
- For videos, check whether HF expands one placeholder per video or per frame;
  Qwen3-VL-style timestamp prompts may require per-frame multimodal items.
- For M-RoPE, verify both prefill and decode position ids. Decode usually
  advances stored M-RoPE positions from scheduler history rather than
  recomputing HF rope deltas in forward.
