# API Documentation

### 1. Generate Prompt (`POST /m/prompt`)[cite: 6]
* **Description**: Appends a new message to the chat history, processes the conversation state using a specified model, and generates a completion response[cite: 5, 6].
* **Request Body (JSON)**:
  * `model_path` *(string, required)*: File path to the Llama model[cite: 6, 8].
  * `chat_template` *(string, optional)*: Custom Jinja template for chat formatting[cite: 6, 8].
  * `role` *(string, required)*: The role of the message author (e.g., `"user"`)[cite: 5, 6].
  * `content` *(string, required)*: The text content of the message[cite: 5, 6].
  * `n_gpu_layers` *(int, optional)*: Number of layers to offload to the GPU (default: `100`)[cite: 6, 8].
  * `n_ctx` *(int, optional)*: Context window size (default: `2048`)[cite: 6, 10].
  * Sampling parameters *(optional)*: `temperature`, `top_p`, `top_k`, `repetition_penalty`, `penalty_last_n`, `penalty_freq`, `penalty_present`, `max_new_tokens`[cite: 8].
* **Response (JSON)**:
  * `response`: The generated text response from the model[cite: 6].

---

### 2. Prefill Chat History (`POST /m/prefill`)[cite: 6]
* **Description**: Seeds or preloads an existing message history into the session context without generating a new response[cite: 5, 6].
* **Request Body (JSON)**:
  * `model_path` *(string, required)*[cite: 6, 8]
  * `chat_template` *(string, optional)*[cite: 6, 8]
  * `n_gpu_layers` *(int, optional)*[cite: 6, 8]
  * `n_ctx` *(int, optional)*[cite: 6, 10]
  * `messages` *(array of objects, required)*: List of historical messages containing `role` and `content` fields[cite: 6].
* **Response (JSON)**:
  * `status`: `"success"`[cite: 6]

---

### 3. Read Context (`POST /m/read/context`)[cite: 6]
* **Description**: Inspects and exports the current conversation history state as a JSON structure without forcing model offloading into VRAM (`load_to_vram = false`)[cite: 4, 5, 6].
* **Request Body (JSON)**:
  * `model_path` *(string, required)*[cite: 4, 6, 8]
  * `chat_template` *(string, optional)*[cite: 6, 8]
  * `n_gpu_layers` *(int, optional)*[cite: 4, 6, 8]
  * `n_ctx` *(int, optional)*[cite: 4, 6, 10]
* **Response (JSON)**:
  * Serialized JSON object containing the message history list (`{"messages": [...]}`)[cite: 5].

---

### 4. Embed Search Query (`POST /m/embed-query`)[cite: 6]
* **Description**: Generates a normalized vector embedding for a search query string, automatically prefixed with `search_query: `[cite: 2, 6, 7].
* **Request Body (JSON)**:
  * `model_path` *(string, required)*[cite: 2, 6, 7]
  * `content` *(string, required)*: Text string to embed[cite: 2, 6, 7].
* **Response (JSON)**:
  * `embedding`: Array of floating-point values representing the vector[cite: 2, 6].

---

### 5. Embed Document (`POST /m/embed-doc`)[cite: 6]
* **Description**: Generates a normalized vector embedding for a document string, automatically prefixed with `search_document: `[cite: 2, 6, 7].
* **Request Body (JSON)**:
  * `model_path` *(string, required)*[cite: 2, 6, 7]
  * `content` *(string, required)*: Text string to embed[cite: 2, 6, 7].
* **Response (JSON)**:
  * `embedding`: Array of floating-point values representing the vector[cite: 2, 6].

---

### 6. Token Count (`POST /m/token/count`)[cite: 6]
* **Description**: Tokenizes the input text using the embedder's vocabulary and returns the total token count[cite: 2, 6, 7].
* **Request Body (JSON)**:
  * `model_path` *(string, required)*[cite: 2, 6, 7]
  * `content` *(string, required)*: Text to evaluate[cite: 2, 6, 7].
* **Response (JSON)**:
  * `token_count`: Integer count of tokens[cite: 6].

---

### 7. Reset Context (`POST /m/reset/context`)[cite: 6]
* **Description**: Clears the conversation history, KV cache buffer, and active context state for a specified model[cite: 5, 6].
* **Request Body (JSON)**:
  * `model_path` *(string, required)*[cite: 4, 6, 8]
  * `chat_template` *(string, optional)*[cite: 6, 8]
  * `n_gpu_layers` *(int, optional)*[cite: 4, 6, 8]
  * `n_ctx` *(int, optional)*[cite: 4, 6, 10]
* **Response (Plain Text)**:
  * `"VRAM Cleared for model"`[cite: 6]

---

### 8. Release Memory (`POST /m/release/memory`)[cite: 6]
* **Description**: Performs a hard reset on model memory, releasing active generators and suspending active embedders to free all VRAM[cite: 4, 6].
* **Request Body (JSON)**: None
* **Response (Plain Text)**:
  * `"VRAM Cleared"`[cite: 6]

---

### 9. Get Status (`GET /m/status`)[cite: 6]
* **Description**: Checks whether the LLM execution pipeline is currently busy processing a concurrent request[cite: 6].
* **Request Body**: None
* **Response (JSON)**:
  * `status`: Boolean value (`true` if busy, `false` otherwise)[cite: 6].
  