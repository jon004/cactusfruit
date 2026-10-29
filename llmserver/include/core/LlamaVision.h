#pragma once

#include <string>
#include <vector>
#include <mutex>
#include <cstdint>

#include "llama.h"

typedef struct mtmd_context mtmd_context;

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
    const char* getMarker() const;

    std::vector<llama_token> evalPrompt(llama_context* lctx, const std::string& prompt, const std::vector<uint8_t>& image_bytes);

private:
    std::string mmproj_path;
    llama_model* text_model = nullptr;
    mtmd_context* mctx = nullptr;
    mutable std::mutex mtx_;
};
