#include "core/Server.h"
#include <iostream>

Server::Server() = default;

void Server::loadResourcesAndRoutes() {
    loadRoutes();
}

void Server::loadRoutes() {
    svr.Post("/m/prompt",         [this](auto& req, auto& res) { handlePostPrompt(req, res); });
    svr.Post("/m/prefill",        [this](auto& req, auto& res) { handlePostPrefill(req, res); });
    svr.Post("/m/read/context",   [this](auto& req, auto& res) { handlePostContext(req, res); });
    svr.Post("/m/embed-query",    [this](auto& req, auto& res) { handlePostEmbedQuery(req, res); });
    svr.Post("/m/embed-doc",      [this](auto& req, auto& res) { handlePostEmbedDocument(req, res); });
    svr.Post("/m/token/count",    [this](auto& req, auto& res) { handlePostTokenCount(req, res); });
    svr.Post("/m/reset/context",  [this](auto& req, auto& res) { handlePostResetContext(req, res); });
    svr.Post("/m/release/memory", [this](auto& req, auto& res) { handlePostReleaseMemory(req, res); });
    svr.Get("/m/status",          [this](auto& req, auto& res) { handleGetStatus(req, res); });
}

bool Server::listen(int port) {
    std::cout << "[Server] Listening on 127.0.0.1:" << port << "..." << std::endl;
    return svr.listen("127.0.0.1", port);
}

void Server::handlePostPrompt(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = json::parse(req.body);
        
        int n_gpu_layers = body.value("n_gpu_layers", 100);
        int n_ctx = body.value("n_ctx", 2048);

        Prompter* agent = memory_manager.getPrompter(
            body.at("model_path"), 
            body.value("chat_template", ""), 
            true,
            n_gpu_layers,
            n_ctx
        );
        
        SamplingParams parameters = SamplingParams::from_json(body);
        
        std::string response = agent->generate(body.at("role"), body.at("content"), parameters);
        res.set_content(json({{"response", response}}).dump(), "application/json");
    });
}

void Server::handlePostPrefill(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = json::parse(req.body);
        
        int n_gpu_layers = body.value("n_gpu_layers", 100);
        int n_ctx = body.value("n_ctx", 2048);

        Prompter* agent = memory_manager.getPrompter(
            body.at("model_path"), 
            body.value("chat_template", ""), 
            true,
            n_gpu_layers,
            n_ctx
        );
        
        std::vector<std::pair<std::string, std::string>> history;
        for (auto& item : body.at("messages")) {
            history.push_back({item.at("role"), item.at("content")});
        }
        
        agent->prefill(history);
        res.set_content(json({{"status", "success"}}).dump(), "application/json");
    });
}

void Server::handlePostContext(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = json::parse(req.body);
        
        int n_gpu_layers = body.value("n_gpu_layers", 100);
        int n_ctx = body.value("n_ctx", 2048);

        // load_to_vram = false (peek without unloading GPU)
        Prompter* agent = memory_manager.getPrompter(
            body.at("model_path"), 
            body.value("chat_template", ""), 
            false,
            n_gpu_layers,
            n_ctx
        );
        
        res.set_content(agent->chatToJson(), "application/json");
    });
}

void Server::handlePostEmbedQuery(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = json::parse(req.body);
        LlamaEmbedder* emb = memory_manager.getEmbedder(body.at("model_path"));
        auto vec = emb->embedSearchQuery(body.at("content"));
        res.set_content(json({{"embedding", vec}}).dump(), "application/json");
    });
}

void Server::handlePostEmbedDocument(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = json::parse(req.body);
        LlamaEmbedder* emb = memory_manager.getEmbedder(body.at("model_path"));
        auto vec = emb->embedDocument(body.at("content"));
        res.set_content(json({{"embedding", vec}}).dump(), "application/json");
    });
}

void Server::handlePostTokenCount(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = json::parse(req.body);
        LlamaEmbedder* emb = memory_manager.getEmbedder(body.at("model_path"));
        int token_count = emb->getTokenCount(body.at("content"));
        res.set_content(json({{"token_count", token_count}}).dump(), "application/json");
    });
}

void Server::handlePostResetContext(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = json::parse(req.body);
        
        int n_gpu_layers = body.value("n_gpu_layers", 100);
        int n_ctx = body.value("n_ctx", 2048);

        Prompter* agent = memory_manager.getPrompter(
            body.at("model_path"), 
            body.value("chat_template", ""), 
            false,
            n_gpu_layers,
            n_ctx
        );

        agent->resetContext();
        res.set_content("VRAM Cleared for model", "text/plain");
    });
}

void Server::handlePostReleaseMemory(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        memory_manager.releaseAll();
        res.set_content("VRAM Cleared", "text/plain");
    });
}

void Server::handleGetStatus(const httplib::Request& req, httplib::Response& res) {
    res.set_content(json({{"status", is_llm_busy.load()}}).dump(), "application/json");
}

bool Server::executeWithLock(httplib::Response& res, std::function<void()> task) {
    if (is_llm_busy.exchange(true)) {
        res.status = 429;
        res.set_content("Server Busy", "text/plain");
        return false;
    }
    try {
        task();
    } catch (const std::exception& e) {
        std::string error_msg = e.what();
        
        if (error_msg.find("MODEL_NOT_FOUND") != std::string::npos) {
            res.status = 404;
            res.set_content(json({{"error", "Model file not found"}, {"path", error_msg}}).dump(), "application/json");
        } else {
            res.status = 500;
            res.set_content(json({{"error", "Internal Server Error"}, {"message", error_msg}}).dump(), "application/json");
        }
    }
    is_llm_busy.store(false);
    return true;
}
