#pragma once

#include <string>
#include <vector>
#include <mutex>
#include <cstdint>

#include "llama.h"

typedef struct mtmd_context mtmd_context;

/**
 * @class LlamaVision
 * @brief Thin RAII wrapper around an mtmd_context (mmproj vision projector),
 *        following the lazy load/release pattern of LlamaGenerator/LlamaEmbedder.
 *
 *        Binds to a loaded text model (llama_model*) at load() time; the owning
 *        LlamaGenerator is responsible for creating/releasing this object.
 */
class LlamaVision {
public:
    LlamaVision(const std::string& mmproj_path, llama_model* text_model);
    ~LlamaVision();

    LlamaVision(const LlamaVision&) = delete;
    LlamaVision& operator=(const LlamaVision&) = delete;

    void load();
    void release();
    bool isLoaded() const { return mctx != nullptr; }

    const std::string& getPath() const { return mmproj_path; }

    // Media marker string that must appear in the prompt text (model-specific).
    const char* getMarker() const;

    /**
     * @brief Decodes image bytes (jpg/png/bmp/gif), tokenizes the prompt with the
     *        media marker swapped in, and evaluates all chunks into lctx.
     * @return The prompt's text tokens (usable as a sampler penalty baseline).
     */
    std::vector<llama_token> evalPrompt(llama_context* lctx, const std::string& prompt, const std::vector<uint8_t>& image_bytes);

private:
    std::string mmproj_path;
    llama_model* text_model = nullptr;
    mtmd_context* mctx = nullptr;
    mutable std::mutex mtx_;
};
