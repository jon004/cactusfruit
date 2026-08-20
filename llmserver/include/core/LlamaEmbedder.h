#pragma once

#include <string>
#include <vector>
#include <mutex>
#include <thread>
#include <condition_variable>
#include <atomic>
#include "llama.h"

class LlamaEmbedder {
public:
    LlamaEmbedder(const std::string& model_path);
    ~LlamaEmbedder();

    std::vector<float> embedDocument(const std::string& document_text);
    std::vector<float> embedSearchQuery(const std::string& query_text);
    int getTokenCount(const std::string& text);
    void suspend();
    const std::string& getModelPath() const;

private:
    llama_model* model = nullptr;
    llama_context* ctx = nullptr;
    const llama_vocab* vocab = nullptr;

    std::mutex mtx; 
    int n_embd = 0;
    std::string model_path;

    // TTL Timer members
    std::thread ttl_thread;
    std::condition_variable cv;
    std::atomic<bool> worker_running{true};
    bool needs_suspend = false;
    void ttlWorker();

    std::vector<float> getEmbedding(const std::string& prefixed_text);
    std::vector<llama_token> tokenize(const std::string& text) const;

    void load();
};
