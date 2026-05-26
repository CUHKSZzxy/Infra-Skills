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

## Non-Image Modalities

For modalities such as time series, keep the same new-style flow but add the
modality contract explicitly.

- Add a `Modality` value and map processor output names in
  `VisionModel.ATTR_NAME_TO_MODALITY`.
- Add the main feature tensor name to `VisionModel.FEATURE_NAMES`.
- Add token ids to `MultimodalSpecialTokens`.
- Add a custom processor method when HF `AutoProcessor` cannot expand the
  placeholder correctly for runtime serving.
- Return processor outputs with `input_ids`, the feature tensor, feature
  metadata, and the modality token id.
- Convert those outputs to `MultiModalData` in the PyTorch input processor.

For InternS1-Pro-style time series, the custom processor normalizes and
truncates the raw signal, derives the number of placeholder tokens from
sampling rate plus patch/subsample lengths, and returns `ts_values`, `ts_lens`,
`ts_sr`, and `ts_token_id`. The PyTorch model then concatenates these fields in
`prepare_inputs_for_generation` and scatters the time-series encoder output into
`inputs_embeds` using the modality token mask.

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
