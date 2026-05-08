# Qwen3-VL PyTorch PR History

Snapshot date: 2026-05-08.

Scope: Qwen3-VL dense and Qwen3-VL-MoE PyTorch model, VL preprocessing, and
serving path changes.

## Main Files

- `lmdeploy/pytorch/models/qwen3_vl.py`
- `lmdeploy/pytorch/models/qwen3_vl_moe.py`
- `lmdeploy/vl/model/qwen3.py`
- `lmdeploy/vl/engine.py`
- `lmdeploy/serve/vl_async_engine.py`
- `lmdeploy/serve/openai/api_server.py`
- `lmdeploy/serve/openai/protocol.py`

## PR Timeline

| Date | PR | Commit | PyTorch relevance |
| --- | --- | --- | --- |
| 2025-11-07 | [#4093](https://github.com/InternLM/lmdeploy/pull/4093) | `bbc43690` | Added Qwen3-VL dense/MoE PyTorch models, VL builder support, docs, and architecture mapping. This is the baseline for image/video preprocessing and text/vision token merge behavior. |
| 2025-12-08 | [#4183](https://github.com/InternLM/lmdeploy/pull/4183) | `322b1331` | Added vision ids across messages, engines, OpenAI protocol, and VL model code. Validate both pipeline and serving entry points. |
| 2025-12-10 | [#4196](https://github.com/InternLM/lmdeploy/pull/4196) | `a34db184` | Added `mm_processor_args` for Qwen3-VL serving and VL engine paths. Processor arguments must survive API server, async engine, and local pipeline flows. |
| 2025-12-23 | [#4207](https://github.com/InternLM/lmdeploy/pull/4207) | `70b277d1` | Improved Qwen3-VL model code and REST profiling utilities. Use these profiling paths when changing preprocessing or engine/model-agent boundaries. |
| 2026-02-11 | [#4342](https://github.com/InternLM/lmdeploy/pull/4342) | `cb0af3fa` | Fixed Qwen3-VL-MoE long-context behavior through model-agent related changes. Include long-context MoE cases in validation. |
| 2026-02-11 | [#4348](https://github.com/InternLM/lmdeploy/pull/4348) | `f8181ee5` | Fixed Qwen3-VL with Transformers 5 by adjusting model and VL utility code. Processor/config API drift is a recurring failure mode. |
| 2026-03-25 | [#4457](https://github.com/InternLM/lmdeploy/pull/4457) | `25d9517a` | Added router replay and returned routed-expert data for Qwen3-VL-MoE. Review batch dimensions and return-type stability carefully. |

## Optimization Notes

- Qwen3-VL changes are rarely isolated to one model file. Check the VL model,
  processor, engine, async engine, and OpenAI protocol together.
- Keep image and video paths separate in validation. A text-plus-image smoke can
  miss video resize, frame metadata, or processor argument issues.
- Qwen3-VL-MoE needs both VLM and MoE validation. Routed-expert changes should
  include batch size greater than one.

## Validation Lanes

- Local pipeline with image input.
- Local pipeline with video input when supported by the branch.
- OpenAI-compatible serving request with vision content.
- `mm_processor_args` through API server and local pipeline.
- Transformers 5 processor/config compatibility.
- Qwen3-VL-MoE long-context case.
- Routed-expert output shape with batch size greater than one.
