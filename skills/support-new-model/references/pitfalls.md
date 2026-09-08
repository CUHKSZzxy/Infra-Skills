# Common Pitfalls Catalog

Use these possible causes when the symptom matches; verify them in the target checkout.

| #   | Symptom                                                  | Root cause                                                       | Fix                                                                                                           |
| --- | -------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 1   | Missing/unexpected key errors on weight load             | `packed_modules_mapping` keys don't match HF param name suffixes | Check actual HF weight names: `list(model.state_dict().keys())[:20]` before coding                            |
| 2   | Wrong outputs, no error                                  | `stacked_params_mapping` for QKV in wrong shard order            | Map Q/K/V weights to shard IDs `'q'`, `'k'`, and `'v'` in that order; a wrong mapping silently corrupts output |
| 3   | Model not found / not routed to LMDeploy class           | Wrong `_arch` value                                              | Must match `hf_config.architectures[0]` literally (e.g. `'Qwen3VLForConditionalGeneration'`, not `'Qwen3VL'`) |
| 4   | Image features silently not injected                     | `image_token_id` is `None`                                       | Check the converted ID denotes the expected image token, not an unknown-token fallback                   |
| 5   | Confusing inference error mentioning `role='preprocess'` | `preprocess()` does not append `role='preprocess'` to messages   | `to_pytorch_aux()` searches for exactly `role='preprocess'`; old-style `preprocess()` must append it          |
| 6   | Config builder never triggered                           | `condition()` model_type mismatch                                | Must match the exact string in `config.json`, not a display name or alias                                     |
| 7   | MoE model produces wrong outputs or crashes              | Missing MoE routing logic                                        | MoE models need `num_experts`, `num_experts_per_tok`, and TopK gating in MLP; reference `qwen3_moe.py`        |
| 8   | CUDA graph capture fails                                 | Unsupported dynamic input or missing graph-buffer handling       | Keep decode graph-safe; override `support_cuda_graph(...)` for input-specific opt-out or add the required `CudaGraphMixin` buffer hooks |
