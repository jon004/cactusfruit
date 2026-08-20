#pragma once

#include <httplib.h>
#include <string>
#include <memory>
#include <atomic>
#include <functional>
#include <nlohmann/json.hpp>

#include "core/ModelMemoryManager.h"

using json = nlohmann::json;

/**
 * @class Server
 * @brief Stateless-style server that orchestrates VRAM via ModelMemoryManager.
 */
class Server {
public:
    Server();
    void loadResourcesAndRoutes();
    bool listen(int port = 8287);

private:
    httplib::Server svr;
        
    // The single source of truth for VRAM and model objects
    ModelMemoryManager memory_manager;

    std::atomic<bool> is_llm_busy{false};

    void loadResources();
    void loadRoutes();
    
    // Core execution wrapper
    bool executeWithLock(httplib::Response& res, std::function<void()> task);

    // Handlers
    void handlePostPrompt(const httplib::Request& req, httplib::Response& res);
    void handlePostPrefill(const httplib::Request& req, httplib::Response& res);
    void handlePostContext(const httplib::Request& req, httplib::Response& res);
    void handlePostReleaseMemory(const httplib::Request& req, httplib::Response& res);
    void handlePostResetContext(const httplib::Request& req, httplib::Response& res);
    void handlePostEmbedQuery(const httplib::Request& req, httplib::Response& res);
    void handlePostEmbedDocument(const httplib::Request& req, httplib::Response& res);
    void handlePostTokenCount(const httplib::Request& req, httplib::Response& res);
    void handleGetStatus(const httplib::Request& req, httplib::Response& res);
};
