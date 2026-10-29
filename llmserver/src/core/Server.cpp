#include "core/Server.h"
#include <iostream>
#include <string_view>
#include <cstdint>

Server::Server() = default;

void Server::loadResourcesAndRoutes() {
    loadRoutes();
}

void Server::loadRoutes() {
    svr.Post("/m/prompt",         [this](auto& req, auto& res) { handlePostPrompt(req, res); });
    svr.Post("/m/prompt/image",   [this](auto& req, auto& res) { handlePostPromptImage(req, res); });
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

// Helper utility to parse JSON safely if body is present, otherwise return empty json
static json parse_json_body_safe(const std::string& body_str) {
    if (body_str.empty()) return json::object();
    try {
        return json::parse(body_str);
    } catch (...) {
        return json::object();
    }
}

void Server::handlePostPrompt(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = parse_json_body_safe(req.body);

        std::string model_path = req.has_header("X-Model-Path") 
            ? req.get_header_value("X-Model-Path") 
            : body.at("model_path").get<std::string>();

        std::string chat_template = req.has_header("X-Chat-Template") 
            ? req.get_header_value("X-Chat-Template") 
            : body.value("chat_template", "");

        int n_gpu_layers = req.has_header("X-N-Gpu-Layers") 
            ? std::stoi(req.get_header_value("X-N-Gpu-Layers")) 
            : body.value("n_gpu_layers", 100);

        int n_ctx = req.has_header("X-N-Ctx") 
            ? std::stoi(req.get_header_value("X-N-Ctx")) 
            : body.value("n_ctx", 2048);

        std::string role = req.has_header("X-Role") 
            ? req.get_header_value("X-Role") 
            : body.at("role").get<std::string>();

        std::string content = req.has_header("X-Prompt") 
            ? req.get_header_value("X-Prompt") 
            : body.at("content").get<std::string>();

        Prompter* agent = memory_manager.getPrompter(
            model_path, 
            chat_template, 
            true,
            n_gpu_layers,
            n_ctx
        );
        
        SamplingParams parameters = SamplingParams::from_json(body);
        
        std::string response = agent->generate(role, content, parameters);
        res.set_content(json({{"response", response}}).dump(), "application/json");
    });
}

void Server::handlePostPromptImage(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        if (!req.has_header("X-Model-Path") || !req.has_header("X-Mmproj-Path") || 
            !req.has_header("X-Role") || !req.has_header("X-Prompt")) {
            throw std::invalid_argument("Missing required headers: X-Model-Path, X-Mmproj-Path, X-Role, X-Prompt");
        }
        std::string model_path = req.get_header_value("X-Model-Path");
        std::string mmproj_path = req.get_header_value("X-Mmproj-Path");
        std::string role = req.get_header_value("X-Role");
        std::string prompt = req.get_header_value("X-Prompt");
        int n_gpu_layers = req.has_header("X-N-Gpu-Layers") 
            ? std::stoi(req.get_header_value("X-N-Gpu-Layers")) 
            : 100;
        int n_ctx = req.has_header("X-N-Ctx") 
            ? std::stoi(req.get_header_value("X-N-Ctx")) 
            : 2048;
        std::string chat_template = req.has_header("X-Chat-Template") 
            ? req.get_header_value("X-Chat-Template") 
            : "";

        Prompter* agent = memory_manager.getPrompter(
            model_path,
            chat_template,
            true,
            n_gpu_layers,
            n_ctx
        );

        if (req.body.empty()) {
            throw std::invalid_argument("Request body cannot be empty");
        }

        std::vector<uint8_t> image_bytes(req.body.begin(), req.body.end());
        if (image_bytes.empty()) {
            throw std::invalid_argument("Invalid or empty image data payload");
        }

        SamplingParams parameters;
        std::string response = agent->generateWithImage(
            role,
            prompt,
            image_bytes,
            mmproj_path,
            parameters
        );
        res.set_content(json({{"response", response}}).dump(), "application/json");
    });
}

void Server::handlePostPrefill(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = parse_json_body_safe(req.body); 

        std::string model_path = req.has_header("X-Model-Path") 
            ? req.get_header_value("X-Model-Path") 
            : body.at("model_path").get<std::string>();

        std::string chat_template = req.has_header("X-Chat-Template") 
            ? req.get_header_value("X-Chat-Template") 
            : body.value("chat_template", "");

        int n_gpu_layers = req.has_header("X-N-Gpu-Layers") 
            ? std::stoi(req.get_header_value("X-N-Gpu-Layers")) 
            : body.value("n_gpu_layers", 100);

        int n_ctx = req.has_header("X-N-Ctx") 
            ? std::stoi(req.get_header_value("X-N-Ctx")) 
            : body.value("n_ctx", 2048);

        Prompter* agent = memory_manager.getPrompter(
            model_path, 
            chat_template, 
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
        json body = parse_json_body_safe(req.body);

        std::string model_path = req.has_header("X-Model-Path") 
            ? req.get_header_value("X-Model-Path") 
            : body.at("model_path").get<std::string>();

        std::string chat_template = req.has_header("X-Chat-Template") 
            ? req.get_header_value("X-Chat-Template") 
            : body.value("chat_template", "");

        int n_gpu_layers = req.has_header("X-N-Gpu-Layers") 
            ? std::stoi(req.get_header_value("X-N-Gpu-Layers")) 
            : body.value("n_gpu_layers", 100);

        int n_ctx = req.has_header("X-N-Ctx") 
            ? std::stoi(req.get_header_value("X-N-Ctx")) 
            : body.value("n_ctx", 2048);

        Prompter* agent = memory_manager.getPrompter(
            model_path, 
            chat_template, 
            false,
            n_gpu_layers,
            n_ctx
        );
        res.set_content(agent->chatToJson(), "application/json");
    });
}

void Server::handlePostEmbedQuery(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = parse_json_body_safe(req.body);

        std::string model_path = req.has_header("X-Model-Path") 
            ? req.get_header_value("X-Model-Path") 
            : body.at("model_path").get<std::string>();

        std::string content = req.has_header("X-Content") 
            ? req.get_header_value("X-Content") 
            : body.at("content").get<std::string>();

        LlamaEmbedder* emb = memory_manager.getEmbedder(model_path);
        auto vec = emb->embedSearchQuery(content);
        res.set_content(json({{"embedding", vec}}).dump(), "application/json");
    });
}

void Server::handlePostEmbedDocument(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = parse_json_body_safe(req.body);

        std::string model_path = req.has_header("X-Model-Path") 
            ? req.get_header_value("X-Model-Path") 
            : body.at("model_path").get<std::string>();

        std::string content = req.has_header("X-Content") 
            ? req.get_header_value("X-Content") 
            : body.at("content").get<std::string>();

        LlamaEmbedder* emb = memory_manager.getEmbedder(model_path);
        auto vec = emb->embedDocument(content);
        res.set_content(json({{"embedding", vec}}).dump(), "application/json");
    });
}

void Server::handlePostTokenCount(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = parse_json_body_safe(req.body);

        std::string model_path = req.has_header("X-Model-Path") 
            ? req.get_header_value("X-Model-Path") 
            : body.at("model_path").get<std::string>();

        std::string content = req.has_header("X-Content") 
            ? req.get_header_value("X-Content") 
            : body.at("content").get<std::string>();

        LlamaEmbedder* emb = memory_manager.getEmbedder(model_path);
        int token_count = emb->getTokenCount(content);
        res.set_content(json({{"token_count", token_count}}).dump(), "application/json");
    });
}

void Server::handlePostResetContext(const httplib::Request& req, httplib::Response& res) {
    executeWithLock(res, [&]() {
        json body = parse_json_body_safe(req.body);

        std::string model_path = req.has_header("X-Model-Path") 
            ? req.get_header_value("X-Model-Path") 
            : body.at("model_path").get<std::string>();

        std::string chat_template = req.has_header("X-Chat-Template") 
            ? req.get_header_value("X-Chat-Template") 
            : body.value("chat_template", "");

        int n_gpu_layers = req.has_header("X-N-Gpu-Layers") 
            ? std::stoi(req.get_header_value("X-N-Gpu-Layers")) 
            : body.value("n_gpu_layers", 100);

        int n_ctx = req.has_header("X-N-Ctx") 
            ? std::stoi(req.get_header_value("X-N-Ctx")) 
            : body.value("n_ctx", 2048);

        Prompter* agent = memory_manager.getPrompter(
            model_path, 
            chat_template, 
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
