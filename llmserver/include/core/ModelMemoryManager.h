#pragma once

#include <string>
#include <vector>
#include <memory>
#include <algorithm>
#include <iostream>

#include "core/LlamaGenerator.h"
#include "core/LlamaEmbedder.h"
#include "core/Prompter.h"

// Helper to keep the Generator and its Prompter paired in the cache
struct CachedAgent {
    std::unique_ptr<LlamaGenerator> gen;
    std::unique_ptr<Prompter> prompter;
};

class ModelMemoryManager {
public:
    ModelMemoryManager() = default;

    /**
     * @brief Get a prompter for a specific model.
     * @param load_to_vram If true, it will unload the current model and load this one into VRAM.
     * @param n_gpu_layers Dynamic request-based VRAM offloading size.
     * @param n_ctx Dynamic maximum context width allocation.
     */
    Prompter* getPrompter(const std::string& path, const std::string& tmpl, bool load_to_vram = true, int n_gpu_layers = 100, int n_ctx = 2048);
    
    LlamaEmbedder* getEmbedder(const std::string& path);

    void releaseAll();

private:
    std::vector<CachedAgent> agent_cache;
    std::vector<std::unique_ptr<LlamaEmbedder>> embedder_cache;

    std::string active_path;
    LlamaGenerator* active_gen = nullptr;
    LlamaEmbedder* active_emb = nullptr;
};
