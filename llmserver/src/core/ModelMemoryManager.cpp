#include "core/ModelMemoryManager.h"
#include <filesystem>

void ModelMemoryManager::releaseAll() {
    if (active_gen) active_gen->release();
    if (active_emb) active_emb->suspend();
    
    active_gen = nullptr;
    active_emb = nullptr;
    active_path = "";
    std::cout << "[MemoryManager] VRAM Hard Reset." << std::endl;
}

Prompter* ModelMemoryManager::getPrompter(const std::string& path, const std::string& tmpl, bool load_to_vram, int n_gpu_layers, int n_ctx) {
    if (!std::filesystem::exists(path)) {
        throw std::runtime_error("MODEL_NOT_FOUND: " + path);
    }
    
    // 1. Find or create the cached pair
    auto it = std::find_if(agent_cache.begin(), agent_cache.end(),
                           [&](const auto& a) { return a.gen->model_path == path; });

    CachedAgent* entry = nullptr;
    if (it != agent_cache.end()) {
        entry = &(*it);
    } else {
        auto gen = std::make_unique<LlamaGenerator>(path, tmpl);
        auto prompter = std::make_unique<Prompter>(*gen);
        agent_cache.push_back({std::move(gen), std::move(prompter)});
        entry = &agent_cache.back();
    }

    // Apply dynamic hardware configuration requested by the client
    bool config_changed = false;
    if (entry->gen->getGpuLayers() != n_gpu_layers) {
        entry->gen->setGpuLayers(n_gpu_layers);
        config_changed = true;
    }
    
    if (entry->prompter->getContextSize() != n_ctx) {
        entry->prompter->setContextSize(n_ctx);
        config_changed = true;
    }

    // If config changed, and this is the active model, we need to clear active_gen so it reloads
    if (config_changed && active_gen == entry->gen.get()) {
        active_gen = nullptr;
    }

    // 2. Check if we need to load model
    if (!load_to_vram) {
        return entry->prompter.get();
    }

    // If already loaded and the paths match
    if (active_gen == entry->gen.get() && active_path == path) {
        return entry->prompter.get();
    }

    // 3. Release current and load new one
    releaseAll();
    
    std::cout << "[MemoryManager] Loading Model into VRAM: " << path << std::endl;
    entry->gen->load(); 
    
    active_gen = entry->gen.get();
    active_path = path;

    return entry->prompter.get();
}

LlamaEmbedder* ModelMemoryManager::getEmbedder(const std::string& path) {
    if (!std::filesystem::exists(path)) {
        throw std::runtime_error("MODEL_NOT_FOUND: " + path);
    }
    
    if (active_emb && active_path == path) return active_emb;

    releaseAll();

    auto it = std::find_if(embedder_cache.begin(), embedder_cache.end(),
                           [&](const auto& e) { return e->getModelPath() == path; });

    if (it != embedder_cache.end()) {
        active_emb = it->get();
    } else {
        auto new_emb = std::make_unique<LlamaEmbedder>(path);
        active_emb = new_emb.get();
        embedder_cache.push_back(std::move(new_emb));
    }

    active_path = path;
    return active_emb;
}
