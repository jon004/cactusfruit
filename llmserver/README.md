# LLM Server

A custom C++ inference server built on `llama.cpp`, designed for a strict memory
budget (target: < 4 GB) while providing features the upstream `llama-server`
does not:

- **Per-model conversation state** — chat history and KV-cache context are
  retained across requests for each model, with incremental evaluation of only
  the new tokens per turn.
- **Sequential model pooling** — exactly one model is resident at a time;
  switching models frees the previous one without losing its conversation.
- **Vision (multimodal) support** — images are evaluated alongside text via a
  model's vision projector (`mmproj`), ingested via high-performance raw binary streams (`application/octet-stream`).
- **Text embeddings and token counting** — exposed as endpoints for retrieval
  and chunking pipelines.
- **Universal Header & JSON Support** — configuration parameters can be passed flexibly via JSON bodies or custom HTTP headers (`X-Model-Path`, `X-N-Gpu-Layers`, `X-N-Ctx`, `X-Chat-Template`, etc.).

CUDA (Linux/NVIDIA) and Metal (Apple Silicon) acceleration are supported; the
build script auto-detects Metal on macOS.

---

## Contents
- [Build](#build)
- [Getting models](#getting-models)
- [Run](#run)
- [API summary](#api-summary)
- [Example requests](#example-requests)
- [Model lifecycle & memory pooling](#model-lifecycle--memory-pooling)
- [Context management](#context-management)
- [Vision notes](#vision-notes)
- [Manual testing client](#manual-testing-client)
- [Requirements](#requirements)

---

## Build

```bash
./build.sh
```

`build.sh` does everything: initializes git submodules (`llama.cpp`, `nlohmann/json`, `cpp-httplib`), detects hardware acceleration, and compiles with CMake. The resulting binary is at:

```
build/llm-server
```

Flags:

| Flag | Effect |
| --- | --- |
| `--cuda` | Enable CUDA acceleration (Linux/NVIDIA) |
| `--debug` | Build in Debug mode |
| `-h`, `--help` | Show help |

On macOS, Metal acceleration is enabled automatically. The multimodal library
(`mtmd`) needed for vision is built via `LLAMA_BUILD_MTMD` in `CMakeLists.txt`;
no extra configuration is required.

> The server does **not** download models and has no model registry — every
> request names a model file path, and the server loads it on demand.

## Getting models

Models are GGUF files placed manually. A `models/` directory works well (it is
git-ignored). Validated example — Qwen2.5-VL-3B with vision:

```bash
mkdir -p models
# text model (~2.3 GB, Q4_K_M)
curl -L -C - -o models/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf \
  https://huggingface.co/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf
# vision projector (~1.1 GB) — only needed for image input
curl -L -C - -o models/Qwen2.5-VL-3B-Instruct-mmproj-fp16.gguf \
  https://huggingface.co/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-mmproj-fp16.gguf
```

Any GGUF supported by the bundled `llama.cpp` works — the chat template is read
from the GGUF itself, so no template configuration is needed.

## Run

```bash
./build/llm-server
```

- Binds to **`127.0.0.1:8287`** (localhost only). Override with `--port <n>` / `-p <n>`.
- Nothing is loaded at startup; models load lazily on first request that names them.
- The server processes **one request at a time**; concurrent requests receive `429 Server Busy`.

## API summary

All request/response bodies can be JSON or configured via custom HTTP headers (`X-Model-Path`, `X-N-Ctx`, `X-N-Gpu-Layers`, etc.). Full schemas: [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md).

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/m/prompt` | POST | Send a message and generate a completion (stateful per model) |
| `/m/prompt/image` | POST | Vision completion via raw binary stream (`application/octet-stream`) and HTTP headers |
| `/m/prefill` | POST | Seed message history without generating |
| `/m/read/context` | POST | Dump current conversation history as JSON |
| `/m/reset/context` | POST | Clear history and context for a model |
| `/m/release/memory` | POST | Hard reset — free all model/embedder VRAM |
| `/m/embed-query` | POST | Embedding of a search query |
| `/m/embed-doc` | POST | Embedding of a document |
| `/m/token/count` | POST | Token count of a text |
| `/m/status` | GET | Whether the server is currently busy |

Common request configuration fields: `model_path` (required — local GGUF path, or via `X-Model-Path`),
`n_ctx` (context window, default `2048`, or via `X-N-Ctx`), `n_gpu_layers` (default `100`, or via `X-N-Gpu-Layers`),
`chat_template` (optional override; otherwise read from the GGUF), plus
sampling parameters (`temperature`, `top_p`, `top_k`, `repetition_penalty`,
`max_new_tokens`, ...).

## Example requests

Text (using JSON body):

```bash
curl -s localhost:8287/m/prompt -d '{
  "model_path": "models/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf",
  "role": "user",
  "content": "Give me a one-sentence summary of the tundra.",
  "n_ctx": 4096
}'
# -> {"response": "..."}
```

Vision (using raw binary stream (`application/octet-stream`) and HTTP headers):

```bash
curl -X POST http://127.0.0.1:8287/m/prompt/image \
  -H "X-Model-Path: models/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf" \
  -H "X-Mmproj-Path: models/Qwen2.5-VL-3B-Instruct-mmproj-fp16.gguf" \
  -H "X-Role: user" \
  -H "X-Prompt: Describe this image in one sentence." \
  -H "X-N-Ctx: 8192" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@photo.jpg"
# -> {"response": "..."}
```

## Model lifecycle & memory pooling

Exactly **one model is resident at a time** (generator XOR embedder), keeping
the hardware footprint bounded:

- **Sequential calls on the same `model_path`**: cache hit — the model stays
  loaded and nothing is reloaded between calls.
- **Requesting a different `model_path`**: the current model's weights are
  released and the new one is loaded.
- **Embedder requests** (`/m/embed-query`, `/m/embed-doc`,
  `/m/token/count`) also evict a resident generator — the model is loaded in
  embedder mode instead. The next generation request pays a reload. Avoid
  interleaving token counts between generation calls when latency matters.
- **Changing `n_ctx` or `n_gpu_layers`** on the same model forces a reload
  with the new configuration.
- **`/m/release/memory`**: explicit hard reset, freeing all weights.

**Conversations survive model swaps.** When a generator is evicted, its
message history and a snapshot of the conversation state are kept; requesting
that model again restores the full conversation. A swap costs a weights
reload from disk, not the conversation.

**Eviction is automatic — `/m/release/memory` is optional.** You never need
to call it to reclaim memory: requesting a different model (or any embedder
request) implicitly frees the current one. It exists for when you want to be
explicit, e.g. guaranteeing headroom between pipeline phases.

Like an implicit swap, `/m/release/memory` also **preserves conversations** —
it frees weights and the KV cache from VRAM, but each model's message history
and state snapshot are retained, so the next request for that model reloads
the weights and picks the conversation back up where it left off.

## Context management

Each `model_path` owns an independent, stateful session:

- **History accumulation** — every `/m/prompt` (or `/m/prompt/image`) appends
  the user message and the assistant reply; the KV cache persists between
  calls.
- **Incremental evaluation** — each call only tokenizes and evaluates the
  *new* tokens since the previous turn, not the whole history.
- **State snapshots** — the conversation state is captured after every
  generation and restored whenever the context is recreated (model swap,
  config change).
- **`/m/prefill`** seeds history without generating; **`/m/read/context`**
  inspects it; **`/m/reset/context`** clears the session for that model.
- **Changing `n_ctx` mid-session** rebuilds the context; the message history
  is re-prefilled on the next call.
- **Context overflow** fails the request with an error (HTTP 500) rather than
  silently truncating — size `n_ctx` accordingly.

## Vision notes

- Requires a vision-capable text model plus its `mmproj` projector file; both
  paths are passed per request.
- The projector loads lazily on the first vision request only — text-only
  traffic never touches it.
- Images consume context tokens (hundreds to ~1.5k depending on resolution);
  use a larger `n_ctx` (e.g. `8192`).
- Supported image formats: jpg, png, bmp, gif.
- High-performance binary streaming (`application/octet-stream`) avoids Base64 overhead completely.

## Manual testing client

[`manualtesting/`](manualtesting/) contains an interactive Python chat client.
Note: its default `base_url` is `http://localhost:8080`, which is wrong for
this server — point it at `http://localhost:8287` (or start the server with
`--port 8080`).

## Requirements

- **macOS or Linux** (Metal auto-enabled on macOS; CUDA via `--cuda`)
- **git** (submodules), **CMake ≥ 3.24**, C/C++ toolchain
- RAM sized to your model + context (e.g. Qwen2.5-VL-3B Q4_K_M runs
  comfortably within 8 GB unified memory)
- Disk: models are fetched manually — plan for their size (~2.3 GB for the
  example text model)