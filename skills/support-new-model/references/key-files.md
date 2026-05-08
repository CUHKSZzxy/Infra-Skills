# Key Files & Reference Models

## Reference Implementations

Study the closest existing model thoroughly before writing any code.

| What you're building          | Read this file first                                                                                                                      |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| LLM (dense)                   | `lmdeploy/pytorch/models/qwen3.py`                                                                                                        |
| LLM (MoE)                     | `lmdeploy/pytorch/models/qwen3_moe.py`                                                                                                    |
| VLM preprocessor              | `lmdeploy/vl/model/qwen3.py`                                                                                                              |
| VLM (composite/nested config) | `lmdeploy/pytorch/models/qwen3_omni_moe_thinker.py` + `lmdeploy/pytorch/configurations/qwen3_omni.py` + `lmdeploy/vl/model/qwen3_omni.py` |

Also read the HF model's `config.json` to identify: `model_type`, `architectures`, layer counts, hidden dims, number of attention heads, MoE parameters (if applicable).

______________________________________________________________________

## Key Files Quick Reference

| File                                         | Purpose                                                         |
| -------------------------------------------- | --------------------------------------------------------------- |
| `lmdeploy/pytorch/models/<model>.py`         | Attention, MLP, DecoderLayer, Model, ForCausalLM                |
| `lmdeploy/pytorch/models/module_map.py`      | HF class name → LMDeploy class path mapping                     |
| `lmdeploy/pytorch/configurations/<model>.py` | Config builder — only needed for non-standard/nested HF configs |
| `lmdeploy/vl/model/<model>.py`               | VLM/multimodal preprocessing *(VLM only)*                       |
| `lmdeploy/vl/model/base.py`                  | `VisionModel` base class + `VISION_MODELS` registry             |
| `lmdeploy/vl/model/builder.py`               | Import location for new VLM classes                             |
| `lmdeploy/archs.py`                          | VLM: arch name → task mapping *(VLM only)*                      |
