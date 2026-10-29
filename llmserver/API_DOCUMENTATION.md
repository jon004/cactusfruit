# API Documentation

### 1. Generate Prompt (`POST /m/prompt`)
- **Description**: Appends a new message to the chat history, processes the conversation state using a specified model, and generates a completion response.
- **Configuration**: Can be passed via JSON body or custom HTTP headers (`X-Model-Path`, `X-Chat-Template`, `X-N-Gpu-Layers`, `X-N-Ctx`, `X-Role`, `X-Prompt`).
- **Request Body (JSON)**:
  - `model_path` *(string, required)*: File path to the Llama model.
  - `chat_template` *(string, optional)*: Custom Jinja template for chat formatting.
  - `role` *(string, required)*: The role of the message author (e.g., `"user"`).
  - `content` *(string, required)*: The text content of the message.
  - `n_gpu_layers` *(int, optional)*: Number of layers to offload to the GPU (default: `100`).
  - `n_ctx` *(int, optional)*: Context window size (default: `2048`).
  - Sampling parameters *(optional)*: `temperature`, `top_p`, `top_k`, `repetition_penalty`, `penalty_last_n`, `penalty_freq`, `penalty_present`, `max_new_tokens`.
- **Response (JSON)**:
  - `response`: The generated text response from the model.

---

### 2. Prefill Chat History (`POST /m/prefill`)
- **Description**: Seeds or preloads an existing message history into the session context without generating a new response.
- **Configuration**: Can be passed via JSON body or custom HTTP headers (`X-Model-Path`, `X-Chat-Template`, `X-N-Gpu-Layers`, `X-N-Ctx`).
- **Request Body (JSON)**:
  - `model_path` *(string, required)*
  - `chat_template` *(string, optional)*
  - `n_gpu_layers` *(int, optional)*
  - `n_ctx` *(int, optional)*
  - `messages` *(array of objects, required)*: List of historical messages containing `role` and `content` fields.
- **Response (JSON)**:
  - `status`: `"success"`

---

### 3. Read Context (`POST /m/read/context`)
- **Description**: Inspects and exports the current conversation history state as a JSON structure without forcing model offloading into VRAM (`load_to_vram = false`).
- **Configuration**: Can be passed via JSON body or custom HTTP headers (`X-Model-Path`, `X-Chat-Template`, `X-N-Gpu-Layers`, `X-N-Ctx`).
- **Request Body (JSON)**:
  - `model_path` *(string, required)*
  - `chat_template` *(string, optional)*
  - `n_gpu_layers` *(int, optional)*
  - `n_ctx` *(int, optional)*
- **Response (JSON)**:
  - Serialized JSON object containing the message history list (`{"messages": [...]}`).

---

### 4. Embed Search Query (`POST /m/embed-query`)
- **Description**: Generates a normalized vector embedding for a search query string, automatically prefixed with `search_query: `.
- **Configuration**: Can be passed via JSON body or custom HTTP headers (`X-Model-Path`, `X-Content`).
- **Request Body (JSON)**:
  - `model_path` *(string, required)*
  - `content` *(string, required)*: Text string to embed.
- **Response (JSON)**:
  - `embedding`: Array of floating-point values representing the vector.

---

### 5. Embed Document (`POST /m/embed-doc`)
- **Description**: Generates a normalized vector embedding for a document string, automatically prefixed with `search_document: `.
- **Configuration**: Can be passed via JSON body or custom HTTP headers (`X-Model-Path`, `X-Content`).
- **Request Body (JSON)**:
  - `model_path` *(string, required)*
  - `content` *(string, required)*: Text string to embed.
- **Response (JSON)**:
  - `embedding`: Array of floating-point values representing the vector.

---

### 6. Token Count (`POST /m/token/count`)
- **Description**: Tokenizes the input text using the embedder's vocabulary and returns the total token count.
- **Configuration**: Can be passed via JSON body or custom HTTP headers (`X-Model-Path`, `X-Content`).
- **Request Body (JSON)**:
  - `model_path` *(string, required)*
  - `content` *(string, required)*: Text to evaluate.
- **Response (JSON)**:
  - `token_count`: Integer count of tokens.

---

### 7. Reset Context (`POST /m/reset/context`)
- **Description**: Clears the conversation history, KV cache buffer, and active context state for a specified model.
- **Configuration**: Can be passed via JSON body or custom HTTP headers (`X-Model-Path`, `X-Chat-Template`, `X-N-Gpu-Layers`, `X-N-Ctx`).
- **Request Body (JSON)**:
  - `model_path` *(string, required)*
  - `chat_template` *(string, optional)*
  - `n_gpu_layers` *(int, optional)*
  - `n_ctx` *(int, optional)*
- **Response (Plain Text)**:
  - `"VRAM Cleared for model"`

---

### 8. Release Memory (`POST /m/release/memory`)
- **Description**: Performs a hard reset on model memory, releasing active generators and suspending active embedders to free all VRAM.
- **Request Body (JSON)**: None
- **Response (Plain Text)**:
  - `"VRAM Cleared"`

---

### 9. Get Status (`GET /m/status`)
- **Description**: Checks whether the LLM execution pipeline is currently busy processing a concurrent request.
- **Request Body**: None
- **Response (JSON)**:
  - `status`: Boolean value (`true` if busy, `false` otherwise).

---

### 10. Generate Prompt with Image (`POST /m/prompt/image`)
- **Description**: Appends a message with an attached image to the chat history and generates a completion. Bypasses Base64 overhead by ingesting raw binary streams (`application/octet-stream`) via HTTP request bodies, utilizing HTTP headers for configuration parameters. The image is evaluated alongside text via the vision projector (`mmproj`).
- **Request Headers**:
  - `Content-Type` *(string, required)*: Must be `application/octet-stream`.
  - `X-Model-Path` *(string, required)*: File path to the Llama text model (GGUF).
  - `X-Mmproj-Path` *(string, required)*: File path to the vision projector (GGUF).
  - `X-Role` *(string, required)*: The role of the message author (e.g., `"user"`).
  - `X-Prompt` *(string, required)*: The text prompt accompanying the image.
  - `X-N-Gpu-Layers` *(int, optional)*: Number of layers to offload to the GPU (default: `100`).
  - `X-N-Ctx` *(int, optional)*: Context window size (default: `2048`).
  - `X-Chat-Template` *(string, optional)*: Custom Jinja template for chat formatting.
- **Request Body**: 
  - Raw binary stream of the image file (e.g., JPEG, PNG via `curl --data-binary "@/path/to/image.jpg"`).
- **Response (JSON)**:
  - `response`: The generated text response from the model.