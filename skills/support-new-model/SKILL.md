---
name: support-new-model
description: Use when adding or reviewing support for a new LLM or VLM architecture in LMDeploy's PyTorch backend, including architecture registration or multimodal preprocessing.
---

# Support A New LMDeploy Model

Use this for new architecture support, not for ordinary serving bugs. Start from
nearby working models and load reference files only when reaching that step.

## 1. Identify The Model Contract

Read the checkpoint config first:

- `architectures[0]`
- `model_type`
- hidden size, heads, kv heads, rope, MoE/GDN/MTP fields
- tokenizer/processor special tokens for VLMs
- modality contracts: image, video, audio placeholders and length fields

Then inspect nearby LMDeploy models and, for VLM/audio/video behavior, compare
HF plus one runtime such as vLLM or SGLang.

Load `references/key-files.md` when unsure which existing model to mirror.
Load `references/hf-to-lmdeploy-porting.md` when translating HF Transformers
inference code into LMDeploy PyTorch model code.
Load `references/recent-pytorch-model-support-patterns.md` when choosing a
modern implementation pattern from recent LMDeploy PyTorch model-support PRs.
Load `references/parity-triage.md` when a ported model runs but its output
differs from the reference and the cause is not yet localized.

## 2. LLM PyTorch Path

Usually needed:

- `lmdeploy/pytorch/models/<model_name>.py`
- `lmdeploy/pytorch/models/module_map.py`
- `lmdeploy/pytorch/configurations/<model_name>.py` only for non-standard or
  nested HF configs

Implementation checklist:

- create `Attention`, `MLP`, `DecoderLayer`, `Model`, `ForCausalLM`,
- register the exact HF architecture class name from `config.json`,
- make `packed_modules_mapping` match HF parameter names,
- make `stacked_params_mapping` shard indices match `load_weights()`,
- verify weights load without missing/unexpected keys.

Style defaults for LMDeploy model code:

- keep inference code concise; omit training-only flags, dropout branches,
  freeze switches, and optional output flags unless nearby LMDeploy models need
  them,
- pass `dtype` and `device` explicitly like adjacent model files; avoid adding
  local factory helpers for simple module construction,
- when replacing HF modules with LMDeploy builders, spell feature dimensions as
  keyword args such as `in_features=` and `out_features=`,
- remove reference-only branches and unused args after parity is established,
- keep comments sparse and useful; do not explain obvious assignments,
- after simplification or op replacement, rerun module-level and end-to-end
  numeric parity checks against the reference.

Load `references/llm-code-skeleton.md` only when writing the model/config code.

## 3. VLM Additional Path

Usually needed:

- `lmdeploy/vl/model/<model_name>.py`
- explicit import in `lmdeploy/vl/model/builder.py`
- supported architecture entry in `lmdeploy/archs.py`

Prefer the new-style path:

```text
MultimodalSpecialTokens -> VisionModel.get_input_prompt(...) -> preprocess(...)
```

Keep model files small. Add custom prompt or preprocessing code only when HF
behavior cannot be unified cleanly. For audio/video, do not assume related model
families expand placeholders or derive lengths the same way.

Load `references/vlm-preprocessor.md` only when implementing the preprocessor.
Load `references/pitfalls.md` when a quick check fails or the model has unusual
token, weight, or modality behavior.

## 4. Verification

Pick an idle GPU before runtime tests:

```bash
nvidia-smi
export CUDA_VISIBLE_DEVICES=<gpu_id>
```

Minimum checks:

```bash
python -m lmdeploy.pytorch.chat <model_path> --backend pytorch
pytest tests/test_lmdeploy/test_vl/
```

For VLMs, also run a tiny pipeline quick check:

```python
from lmdeploy import pipeline
pipe = pipeline('<model_path>')
print(pipe(('Describe this image.', 'path/to/image.jpg')).text)
```

When validation uses local cached checkpoints or media because network is
blocked, restore public/HF-style paths before committing tests.
