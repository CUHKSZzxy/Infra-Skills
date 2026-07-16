# Dense LLM Porting Shape

Use this as a contract checklist, not as code to copy. Helper signatures and
cache metadata evolve; inspect the nearest model in the target checkout before
writing imports or constructor calls.

## Current Anchors

- Dense decoder: `lmdeploy/pytorch/models/qwen3.py`
- MoE decoder: `lmdeploy/pytorch/models/qwen3_moe.py`
- Recurrent or hybrid model: `lmdeploy/pytorch/models/qwen3_5.py`
- Config builders: `lmdeploy/pytorch/configurations/`

## Construction Contracts

Read dimensions and optional behavior from the HF config. Propagate the nearest
model's quantization, tensor-parallel, dtype, device, and prefix arguments.

```text
head_dim = config.head_dim or hidden_size // num_attention_heads
qkv projection:
  input  = hidden_size
  output = q_heads * head_dim + kv_heads * k_head_dim + kv_heads * v_head_dim
output projection:
  input  = q_heads * v_head_dim
  output = hidden_size
gate/up projection:
  input  = hidden_size
  packed outputs = [intermediate_size, intermediate_size]
down projection:
  input  = intermediate_size
  output = hidden_size
```

Do not assume K and V head dimensions are equal. Add q/k normalization,
sliding-window behavior, replicated KV heads, output gates, or recurrent state
only when the target architecture and nearby implementation require them.

## Attention Forward Shape

```text
packed_qkv = qkv_proj(hidden_states)
packed_qkv = flatten_tokens(packed_qkv)
q, k, v = split_qkv(packed_qkv)
q, k = optional_qk_norm(q, k)
q, k = apply_rotary(q, k, position_embedding)
attention_output = backend_attention(
    q, k, v,
    kv_cache_payload,
    attention_metadata,
    optional_cache_scale_zero_metadata,
)
attention_output = reshape_like_hidden_states(attention_output)
return o_proj(attention_output)
```

Let backend attention own KV-cache fill, paged decode, and prefill dispatch.
Mirror the nearest model's cache tuple handling because quantized caches may add
scale/zero tensors beyond K and V.

## Model Wrapper Contract

- Build the base model with explicit `dtype`, `device`, and nested prefix.
- Build the LM head through `DeployModelMixinV1.build_lm_head()`.
- Return hidden states from `forward`; inherited `get_logits()` applies the LM
  head unless the architecture needs different logits behavior.
- Make `prepare_inputs_for_generation()` return exactly the inputs accepted by
  `forward`, including `position_ids`, caches, attention metadata, and optional
  embeddings.
- Keep CUDA-graph support aligned with the current mixin and any extra dynamic
  input buffers required by the model.

## Weight Loading

Map checkpoint suffixes to packed runtime parameters using the shard IDs
expected by each parameter loader.

```text
q_proj    -> qkv_proj, shard 'q'
k_proj    -> qkv_proj, shard 'k'
v_proj    -> qkv_proj, shard 'v'
gate_proj -> gate_up_proj, shard 0
up_proj   -> gate_up_proj, shard 1
```

Before generation, verify:

- `packed_modules_mapping` matches real HF suffixes,
- tied LM-head and rotary cache tensors are skipped when appropriate,
- every loaded parameter exists after prefix rewriting,
- fused or per-expert checkpoint layouts use the matching loader path.

## Config Builder

Add a custom builder only for nonstandard or nested configs. Match `model_type`
exactly, derive the text-engine fields through the current default builder, and
retain the original HF config only when VLM or side modules need it. Config
builders auto-register when their module is discovered under
`lmdeploy/pytorch/configurations/`.
