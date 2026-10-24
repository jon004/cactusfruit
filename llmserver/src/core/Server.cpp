#include "core/Server.h"
#include <iostream>
#include <string_view>
#include <cstdint>

// Decodes base64 (with optional data-URI prefix) into raw bytes.
// Returns false on invalid input; whitespace is ignored.
static bool base64Decode(const std::string& in, std::vector<uint8_t>& out) {
    auto val = [](char c) -> int {
        if (c >= 'A' && c <= 'Z') return c - 'A';
        if (c >= 'a' && c <= 'z') return c - 'a' + 26;
        if (c >= '0' && c <= '9') return c - '0' + 52;
        if (c == '+') return 62;
        if (c == '/') return 63;
        return -1;
    };

    // strip a data-URI prefix, e.g. "data:image/png;base64,"
    std::string_view s(in);
    auto comma = s.find(',');
    if (s.substr(0, 5) == "data:" && comma != std::string_view::npos) {
        s = s.substr(comma + 1);
    }

    out.clear();
    out.reserve(s.size() / 4 * 3);

    uint32_t buf = 0;
    int bits = 0;
    int pad = 0;
    for (char c : s) {
        if (c == '\n' || c == '\r' || c == ' ' || c == '\t') continue;
        if (c == '=') { pad++; continue; }
        if (pad > 0) return false; // data after padding
        int v = val(c);
        if (v < 0) return false;    // invalid character
        buf = (buf << 6) | static_cast<uint32_t>(v);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            out.push_back(static_cast<uint8_t>((buf >> bits) & 0xFF));
        }
    }
    return !out.empty();
}

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

void Server::handlePostPromptImage(const httplib::Request& req, httplib::Response& res) {
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

        // Decode the base64 image (jpg/png/bmp/gif; data-URI prefix tolerated)
        std::vector<uint8_t> image_bytes;
        if (!base64Decode(body.at("image").get<std::string>(), image_bytes)) {
            throw std::invalid_argument("Invalid or empty base64 image data");
        }

        SamplingParams parameters = SamplingParams::from_json(body);

        std::string response = agent->generateWithImage(
            body.at("role"),
            body.at("content"),
            image_bytes,
            body.at("mmproj_path"),
            parameters
        );
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
