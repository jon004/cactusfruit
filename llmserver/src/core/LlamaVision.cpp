#include "core/LlamaVision.h"

#include <memory>
#include <stdexcept>

#include "mtmd.h"
#include "mtmd-helper.h"

LlamaVision::LlamaVision(const std::string& mmproj_path, llama_model* text_model)
: mmproj_path(mmproj_path), text_model(text_model) {
    if (mmproj_path.empty()) {
        throw std::invalid_argument("mmproj path cannot be empty!");
    }
    if (!text_model) {
        throw std::invalid_argument("LlamaVision requires a loaded text model!");
    }
}

LlamaVision::~LlamaVision() {
    release();
}

void LlamaVision::load() {
    std::lock_guard<std::mutex> lock(mtx_);

    if (mctx) return;

    mtmd_context_params params = mtmd_context_params_default();
    mctx = mtmd_init_from_file(mmproj_path.c_str(), text_model, params);
    if (!mctx) {
        throw std::runtime_error("Failed to load vision projector from: " + mmproj_path);
    }
}

void LlamaVision::release() {
    std::lock_guard<std::mutex> lock(mtx_);

    if (mctx) {
        mtmd_free(mctx);
        mctx = nullptr;
    }
}

const char* LlamaVision::getMarker() const {
    return mctx ? mtmd_get_marker(mctx) : nullptr;
}

std::vector<llama_token> LlamaVision::evalPrompt(llama_context* lctx, const std::string& prompt, const std::vector<uint8_t>& image_bytes) {
    std::lock_guard<std::mutex> lock(mtx_);

    if (!mctx) {
        throw std::runtime_error("LlamaVision::evalPrompt(): projector not loaded");
    }
    if (!lctx) {
        throw std::runtime_error("LlamaVision::evalPrompt(): context cannot be null");
    }
    if (prompt.empty()) {
        throw std::runtime_error("LlamaVision::evalPrompt(): prompt cannot be empty");
    }
    if (image_bytes.empty()) {
        throw std::invalid_argument("LlamaVision::evalPrompt(): image data cannot be empty");
    }

    // 1. Decode raw image bytes into a bitmap (jpg/png/bmp/gif via stb_image)
    mtmd_helper_bitmap_wrapper wrapper = mtmd_helper_bitmap_init_from_buf(
        mctx, image_bytes.data(), image_bytes.size(), /*placeholder=*/false
    );
    using BitmapPtr = std::unique_ptr<mtmd_bitmap, decltype(&mtmd_bitmap_free)>;
    BitmapPtr bitmap(wrapper.bitmap, &mtmd_bitmap_free);
    if (!bitmap) {
        throw std::runtime_error("Failed to decode image bytes (supported formats: jpg/png/bmp/gif)");
    }

    // 2. Tokenize the prompt: the media marker is swapped for an image chunk
    using ChunksPtr = std::unique_ptr<mtmd_input_chunks, decltype(&mtmd_input_chunks_free)>;
    ChunksPtr chunks(mtmd_input_chunks_init(), &mtmd_input_chunks_free);
    if (!chunks) {
        throw std::runtime_error("Failed to allocate input chunks");
    }

    llama_memory_t mem = llama_get_memory(lctx);
    const bool is_first = llama_memory_seq_pos_max(mem, 0) == -1;
    llama_pos n_past = is_first ? 0 : llama_memory_seq_pos_max(mem, 0) + 1;

    mtmd_input_text input = { prompt.c_str(), prompt.size(), /*add_special=*/is_first, /*parse_special=*/true };
    const mtmd_bitmap* bitmaps[1] = { bitmap.get() };

    int32_t rc = mtmd_tokenize(mctx, chunks.get(), &input, bitmaps, 1);
    if (rc == 1) {
        throw std::runtime_error("vision: number of media markers in prompt does not match number of images (expected exactly 1)");
    }
    if (rc != 0) {
        throw std::runtime_error("vision: image preprocessing failed");
    }

    // 3. Collect the prompt's text tokens (sampler penalty baseline)
    std::vector<llama_token> text_tokens;
    const size_t n_chunks = mtmd_input_chunks_size(chunks.get());
    for (size_t i = 0; i < n_chunks; i++) {
        const mtmd_input_chunk* chunk = mtmd_input_chunks_get(chunks.get(), i);
        if (mtmd_input_chunk_get_type(chunk) == MTMD_INPUT_CHUNK_TYPE_TEXT) {
            size_t n_tokens = 0;
            const llama_token* tokens = mtmd_input_chunk_get_tokens_text(chunk, &n_tokens);
            if (tokens && n_tokens > 0) {
                text_tokens.insert(text_tokens.end(), tokens, tokens + n_tokens);
            }
        }
    }

    // 4. Evaluate all chunks into the context (handles batching, non-causal masks, M-RoPE)
    llama_pos new_n_past = n_past;
    int32_t ec = mtmd_helper_eval_chunks(
        mctx, lctx, chunks.get(), n_past, /*seq_id=*/0, llama_n_batch(lctx), /*logits_last=*/true, &new_n_past
    );
    if (ec != 0) {
        throw std::runtime_error("vision: failed to evaluate image + text prompt");
    }

    return text_tokens;
}
