---
name: support-new-model
description: Use when adding support for a new LLM or VLM architecture to LMDeploy's PyTorch backend — covers model file, module_map registration, config builder, VLM preprocessor, and arch registration. Load references/ files only when you reach that step.
---

# Tutorial: Adding a New Model to LMDeploy (PyTorch Backend)

## Before Writing Any Code

Study the reference implementations before touching any files. Load **references/key-files.md** for the quick reference table and which existing models to read first.

______________________________________________________________________

## Step-by-Step: LLM (PyTorch Backend)

### Step 1 — Create the PyTorch model file

**File:** `lmdeploy/pytorch/models/<model_name>.py`

Implement 5 classes (innermost → outermost): `Attention`, `MLP`, `DecoderLayer`, `Model`, `ForCausalLM`.

Load **references/llm-code-skeleton.md** for full class skeletons and required imports.

### Step 2 — Register in `module_map.py`

**File:** `lmdeploy/pytorch/models/module_map.py`

```python
MODULE_MAP.update({
    'MyModelForCausalLM': f'{LMDEPLOY_PYTORCH_MODEL_PATH}.my_model.MyModelForCausalLM',
})
```

The key is the exact HF architecture class name from `config.json`'s `architectures` field.

### Step 3 — Add config builder (if needed)

**File:** `lmdeploy/pytorch/configurations/<model_name>.py`

Skip for models with a standard flat HF config — `DefaultModelConfigBuilder` handles them automatically. Only needed for nested configs or unusual `model_type`. Load **references/llm-code-skeleton.md** for the config builder pattern.

______________________________________________________________________

## Step-by-Step: VLM (additional steps)

### Step 4 — Create the VL preprocessor

**File:** `lmdeploy/vl/model/<model_name>.py`

Load **references/vlm-preprocessor.md** for new-style vs old-style guide and code skeletons.

For new-style multimodal models, prefer the shared
`get_input_prompt -> VisionModel.preprocess(...)` path. Keep model files small:
resolve processors and special token IDs there, but add model-specific
preprocess/modeling code only when HF behavior cannot be unified cleanly.

When adding audio/video support, compare the HF processor and a nearby runtime
such as SGLang or vLLM. Preserve modality-specific contracts: offsets are
usually enough for placeholder spans, audio lengths may be derived from
`feature_attention_mask`, and video expansion can differ between related model
families.

After creating the file, add an explicit import in `lmdeploy/vl/model/builder.py`:

```python
from .my_model import MyModelVLModel  # noqa F401
```

### Step 5 — Register VLM arch in `archs.py`

**File:** `lmdeploy/archs.py`

```python
# inside check_vl_llm()
supported_archs = set([
    ...
    'MyModelForConditionalGeneration',  # add this line
])
```

______________________________________________________________________

## Checklist

**LLM (PyTorch backend):**

- \[ \] `pytorch/models/<model>.py` — all 5 classes implemented (`Attention`, `MLP`, `DecoderLayer`, `Model`, `ForCausalLM`)
- \[ \] `module_map.py` — HF architecture class name registered
- \[ \] `packed_modules_mapping` matches HF parameter naming scheme
- \[ \] `stacked_params_mapping` in `load_weights()` has correct shard indices
- \[ \] `pytorch/configurations/<model>.py` — added only if HF config is non-standard
- \[ \] Weights load cleanly from HF checkpoint (no missing/unexpected key errors)

**VLM (additional):**

- \[ \] `vl/model/<model>.py` — `build_preprocessor(self, trust_remote_code=False)` implemented; chose new-style or old-style
- \[ \] New-style: `MultimodalSpecialTokens` populated with correct token IDs for each modality
- \[ \] New-style: uses `VisionModel.get_input_prompt(...) -> preprocess(...)`; custom prompt code only when needed
- \[ \] `_arch` matches `config.json` `architectures[0]` exactly
- \[ \] each supported multimodal token ID is resolved from the tokenizer/processor (not None)
- \[ \] `vl/model/builder.py` — explicit import added
- \[ \] `archs.py` entry added

If anything fails, load **references/pitfalls.md** for the catalog of common failure modes.

______________________________________________________________________

## Verification

**Pick a free GPU first:**

```bash
nvidia-smi   # pick a GPU with 0% utilization and only a few MiB allocated
export CUDA_VISIBLE_DEVICES=<gpu_id>
```

**LLM basic test:**

```bash
python -m lmdeploy.pytorch.chat <model_path> --backend pytorch
```

**VLM basic test:**

```python
from lmdeploy import pipeline
pipe = pipeline('<model_path>')
result = pipe(('Describe this image.', 'path/to/image.jpg'))
print(result.text)
```

**Unit tests:**

```bash
pytest tests/test_lmdeploy/test_vl/     # VLM tests
pytest tests/test_lmdeploy/             # all unit tests
```

**Debug weight loading:**

```bash
LMDEPLOY_LOG_LEVEL=DEBUG python -m lmdeploy.pytorch.chat <model_path> --backend pytorch 2>&1 | grep -E "load|weight|miss"
```
