# Qwen3-Omni PyTorch PR History

Snapshot date: 2026-05-09.

Scope: Qwen3-Omni thinker PyTorch model, audio/image/video preprocessing, and
shared new-style VL preprocessing.

## Main Files

- `lmdeploy/pytorch/models/qwen3_omni_moe_thinker.py`
- `lmdeploy/vl/model/qwen3_omni.py`
- `lmdeploy/vl/model/base.py`
- `lmdeploy/vl/model/preprocess_utils.py`
- `lmdeploy/vl/media/audio.py`

## Review Notes

- Qwen3-Omni video differs from Qwen3-VL-MoE timestamp/per-frame handling.
  Omni keeps a whole-video span and uses `video_second_per_grid` to scale video
  temporal MRoPE ids.
- HF Qwen3-Omni derives `video_second_per_grid` from `videos_kwargs['fps']`.
  When reviewing LMDeploy preprocessing, verify that `fps` survives the local
  pipeline/API path into the HF processor, especially for `fps != 1`.
- Audio support is Qwen3-Omni specific for now. Keep docs and parser behavior
  clear about that support boundary.
- Prefer offsets over parallel length fields such as `mm_token_num`; offsets
  already represent the placeholder span consumed by the PyTorch input
  processor.

## Validation Lanes

- Unit test image-only, audio-only, video-only, and mixed image/audio/video
  preprocessing.
- Include a video test with `fps != 1` that checks forwarded `videos_kwargs`
  and resulting temporal spacing.
- Run local `0_pipe.py` smoke for single image, single video, and single audio
  when model weights and a free GPU are available.
