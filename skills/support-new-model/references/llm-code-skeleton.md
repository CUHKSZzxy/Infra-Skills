# LLM Code Skeletons

## Required Imports

```python
import torch
import torch.nn as nn
from lmdeploy.pytorch.model_inputs import StepContext, StepContextManager
from lmdeploy.pytorch.nn import (ApplyRotaryEmb, Attention, RMSNorm, SiluAndMul,
                                  build_rotary_embedding_from_config)
from lmdeploy.pytorch.nn.linear import (build_down_linear, build_gateup_linear,
                                         build_o_proj, build_qkv_proj)
from lmdeploy.pytorch.weight_loader.model_weight_loader import load_weight
from .patch import add_prefix
from .utils.cudagraph import CudaGraphMixin
from .utils.model import DeployModelMixinV1, build_embedding
```

______________________________________________________________________

## Attention Skeleton

```python
class MyModelAttention(nn.Module):
    def __init__(self, config, dtype=None, device=None, prefix=''):
        super().__init__()
        quantization_config = getattr(config, 'quantization_config', None)
        num_heads = config.num_attention_heads
        num_kv_heads = config.num_key_value_heads
        hidden_size = config.hidden_size
        head_dim = getattr(config, 'head_dim', hidden_size // num_heads)
        attention_bias = getattr(config, 'attention_bias', False)
        num_replicate_kv_heads = getattr(config, 'num_replicate_key_value_heads', 1)

        self.qkv_proj = build_qkv_proj(
            hidden_size,
            num_q_heads=num_heads,
            num_kv_heads=num_kv_heads,
            head_size=head_dim,
            bias=attention_bias,
            quant_config=quantization_config,
            dtype=dtype,
            device=device,
            num_replicate_kv_heads=num_replicate_kv_heads,
            prefix=add_prefix('qkv_proj', prefix),
        )
        self.apply_rotary_pos_emb = ApplyRotaryEmb()
        self.attn_fwd = Attention(
            num_heads,
            head_dim,
            num_kv_heads=num_kv_heads,
            v_head_size=head_dim,
            sliding_window=getattr(config, 'sliding_window', None),
        )
        self.o_proj = build_o_proj(
            num_heads * head_dim,
            hidden_size,
            bias=attention_bias,
            quant_config=quantization_config,
            dtype=dtype,
            device=device,
            is_tp=True,
            prefix=add_prefix('o_proj', prefix),
        )

    def forward(self, hidden_states, rotary_pos_emb, past_key_value, attn_metadata):
        qkv_states = self.qkv_proj(hidden_states).flatten(0, -2)
        query_states, key_states, value_states = self.qkv_proj.split_qkv(qkv_states)
        # Apply model-specific q/k normalization here when the HF model has it.
        # Apply rotary, call attn_fwd with KV cache tensors/scales, reshape, and project.
        ...
```

Mirror the nearest current model's cache tuple handling. Standard caches contain
K/V tensors, while quantized KV caches may also carry scale/zero tensors.

______________________________________________________________________

## MLP Skeleton

```python
class MyModelMLP(nn.Module):
    def __init__(self, config, dtype=None, device=None, prefix=''):
        super().__init__()
        quantization_config = getattr(config, 'quantization_config', None)
        self.gate_up_proj = build_gateup_linear(
            config.hidden_size,
            [config.intermediate_size, config.intermediate_size],
            bias=False,
            quant_config=quantization_config,
            dtype=dtype,
            device=device,
            is_tp=True,
            prefix=add_prefix('gate_up_proj', prefix),
        )
        self.down_proj = build_down_linear(
            config.intermediate_size,
            config.hidden_size,
            bias=False,
            quant_config=quantization_config,
            dtype=dtype,
            device=device,
            is_tp=True,
            prefix=add_prefix('down_proj', prefix),
        )
        self.act_fn = SiluAndMul(inplace=True)

    def forward(self, x):
        return self.down_proj(self.act_fn(self.gate_up_proj(x)))
```

______________________________________________________________________

## ForCausalLM Skeleton

```python
class MyModelForCausalLM(nn.Module, DeployModelMixinV1, CudaGraphMixin):
    # Maps packed param name → list of original HF param suffixes
    packed_modules_mapping = {
        'qkv_proj': ['q_proj', 'k_proj', 'v_proj'],
        'gate_up_proj': ['gate_proj', 'up_proj'],
    }

    def __init__(self, config, ctx_mgr: StepContextManager,
                 dtype=None, device=None, prefix=''):
        super().__init__()
        self.config = config
        self.ctx_mgr = ctx_mgr
        self.model = MyModelModel(
            config,
            dtype=dtype,
            device=device,
            prefix=add_prefix('model', prefix),
        )
        self.lm_head = self.build_lm_head(
            config.hidden_size,
            config.vocab_size,
            bias=False,
            dtype=dtype,
            device=device,
        )

    def get_input_embeddings(self):
        return self.model.embed_tokens

    def forward(self, input_ids, position_ids, past_key_values,
                attn_metadata=None, inputs_embeds=None, **kwargs):
        return self.model(
            input_ids=input_ids,
            position_ids=position_ids,
            past_key_values=past_key_values,
            attn_metadata=attn_metadata,
            inputs_embeds=inputs_embeds,
        )

    # prepare_inputs_for_generation and load_weights: copy from qwen3.py,
    # update stacked_params_mapping to match this model's HF weight names.
```

`DeployModelMixinV1.get_logits()` applies `lm_head`; do not duplicate it unless
the model needs different logits behavior. Before using any skeleton, compare
the helper signatures with the nearest model on the checked-out LMDeploy branch.

______________________________________________________________________

## Config Builder Skeleton

Only needed for non-standard HF configs (nested config, unusual `model_type`).

```python
from .builder import AutoModelConfigBuilder
from .default import DefaultModelConfigBuilder

class MyModelConfigBuilder(AutoModelConfigBuilder):
    @classmethod
    def condition(cls, hf_config):
        # Must match model_type from config.json exactly
        return hf_config.model_type == 'my_model'

    @classmethod
    def build(cls, hf_config, model_path=None, **kwargs):
        # Extract the text config if nested; patch fields if needed
        cfg = DefaultModelConfigBuilder.build(hf_config, model_path, **kwargs)
        cfg.hf_config = hf_config  # keep full config for VLM layers
        return cfg
```

Auto-discovery: subclasses of `AutoModelConfigBuilder` register via `__init_subclass__()` — no import needed elsewhere.
