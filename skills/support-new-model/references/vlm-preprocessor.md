# VLM Preprocessor Guide

Two styles exist. Use new-style for new VLM or multimodal models unless the
target checkout only supports an older legacy path.

______________________________________________________________________

## New-Style (recommended for new models)

Inherit from `VisionModel` and keep the model file small. Usually override only
`build_preprocessor`; the base path handles `get_input_prompt -> preprocess`,
modality collection, HF processor dispatch, token-span offsets, and per-item
multimodal outputs.

The engine detects new-style automatically:

```python
_uses_new_preprocess = 'input_prompt' in sig and 'mm_processor_kwargs' in sig
```

Reference implementation: `lmdeploy/vl/model/qwen3.py`

```python
from lmdeploy.vl.model.base import VISION_MODELS, VisionModel
from lmdeploy.vl.model.base import MultimodalSpecialTokens

@VISION_MODELS.register_module()
class MyModelVLModel(VisionModel):
    _arch = ['MyModelForConditionalGeneration']

    def build_preprocessor(self, trust_remote_code: bool = False):
        from transformers import AutoProcessor
        self.processor = AutoProcessor.from_pretrained(self.model_path, trust_remote_code=trust_remote_code)
        tokenizer = self.processor.tokenizer
        # Set token IDs for each modality the model supports
        self.mm_tokens = MultimodalSpecialTokens(
            image_token_id=tokenizer.convert_tokens_to_ids('<image>'),
            video_token_id=tokenizer.convert_tokens_to_ids('<video>'),  # if supported
        )
        self.image_token_id = self.mm_tokens.image_token_id
```

______________________________________________________________________

## Old-Style (backward compat / no mixed-modality needed)

Override `preprocess(self, messages)` directly. Called before `wrap_for_pytorch`.

**Critical:** must append `role='preprocess'` to messages — `to_pytorch_aux()` searches for this exact role string.

```python
@VISION_MODELS.register_module()
class MyModelVLModel(VisionModel):
    _arch = ['MyModelForConditionalGeneration']

    def build_preprocessor(self): ...

    def preprocess(self, messages):
        # Process images, return updated messages with pixel_values attached
        # Must append a message with role='preprocess' for the engine to find it
        ...
```

______________________________________________________________________

## Registration

Both styles use `@VISION_MODELS.register_module()` for auto-discovery. Still requires an explicit import in `lmdeploy/vl/model/builder.py`:

```python
from .my_model import MyModelVLModel  # noqa F401
```
