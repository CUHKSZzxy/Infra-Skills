# LMDeploy API Server, AsyncEngine, MP Engine, And ZMQ RPC

Use this map when a serve issue crosses the HTTP, preprocessing, RPC, and
PyTorch engine boundary.

## Mental Model

For `lmdeploy serve api_server --backend pytorch`, the API process is the
client side of the inference boundary:

```text
FastAPI api_server
  -> AsyncEngine or VLAsyncEngine
    -> MPEngine / ZMQMPEngine proxy
      -> AsyncRPCClient

localhost ZMQ RPC

mp_engine_proc child process
  -> AsyncRPCServer
    -> EngineWorkerBase
      -> real PyTorch Engine
        -> RequestManager / EngineLoop / Scheduler / Executor
```

`api_server` owns HTTP routing and OpenAI-compatible response shaping.
`AsyncEngine` owns prompt preprocessing, sessions, handle pooling,
detokenization, and metrics. It is not the raw RPC client, but it usually uses
an RPC-backed engine proxy in PyTorch API serving.

`ZMQMPEngine` is the client-side proxy in the API process. It starts the child
process, waits for its random localhost RPC port, and forwards engine calls
through `AsyncRPCClient`.

The real PyTorch `Engine` lives in the child process. `AsyncRPCServer`
dispatches to `EngineWorkerBase`, whose instance methods call the real engine
and stream `EngineOutput` chunks back over RPC.

## Request Flow

```text
POST /v1/chat/completions
-> route validates request, creates Session, builds GenerationConfig
-> VariableInterface.async_engine.generate(...)
-> prompt/template/tokenization and optional multimodal preprocessing
-> session.request_handle() gets an engine handle
-> handle.async_stream_infer(...)
-> MPEngineInstance sends instance_async_stream_infer over ZMQ
-> EngineWorkerBase calls EngineInstance.async_stream_infer in child process
-> EngineInstance sends ADD_SESSION and ADD_MESSAGE to RequestManager
-> EngineLoop/Scheduler/Executor run prefill/decode
-> EngineOutput chunks return through RequestManager, RPC, AsyncEngine
-> route emits SSE chunks or aggregates final JSON
```

Even non-streaming HTTP routes commonly use `stream_response=True` internally
so the engine can batch and schedule incrementally; the route decides whether
to stream or aggregate for the client.

## Code Anchors

- `lmdeploy/serve/openai/api_server.py`: FastAPI routes, `serve()`, and
  `VariableInterface.async_engine`.
- `lmdeploy/serve/core/async_engine.py`: `AsyncEngine.generate`,
  preprocessing, request handles, detokenization, and output conversion.
- `lmdeploy/serve/core/vl_async_engine.py`: VLM-specific encoder and
  multimodal processor wiring.
- `lmdeploy/pytorch/engine/engine.py`: real PyTorch engine and
  `Engine.from_pretrained`; MP mode diverts to `build_mp_engine`.
- `lmdeploy/pytorch/engine/mp_engine/base.py`: `MPEngine` and
  `MPEngineInstance` proxy behavior.
- `lmdeploy/pytorch/engine/mp_engine/zmq_engine.py`: child process startup,
  RPC server creation, and worker registration.
- `lmdeploy/pytorch/engine/mp_engine/zmq_rpc.py`: localhost ROUTER/DEALER RPC,
  pickle payloads, and streaming pull protocol.
- `lmdeploy/pytorch/engine/engine_instance.py`: converts inference calls into
  `ADD_SESSION`, `ADD_MESSAGE`, `STOP_SESSION`, and `END_SESSION` requests.
- `lmdeploy/pytorch/engine/request.py`: request queue, sender, response event,
  and engine-loop task management.

## Debugging Implications

- Slow before route logs: HTTP accept/routing or middleware.
- Slow before `AsyncEngine.generate` logs: route validation or request shaping.
- Slow after prompt preprocessing but before engine work: RPC serialization,
  large payload transfer, or child process receive/deserialize.
- Slow after `ADD_MESSAGE`: scheduler queueing, prefill/decode, executor, or
  GPU kernels.
- Client disconnects and aborts must travel back through session handle,
  MP proxy, RPC, worker, and engine instance cleanup.

For TurboMind, do not assume this PyTorch MP/ZMQ shape; `AsyncEngine` builds
the TurboMind backend path instead.
