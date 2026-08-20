#include "core/LlamaEmbedder.h"
#include <stdexcept>
#include <cmath>
#include <iostream>
#include <algorithm>
#include <mutex>
#include <limits>

LlamaEmbedder::LlamaEmbedder(const std::string& model_path) : model_path(model_path) {
    llama_backend_init();
    // Start background TTL monitor
    ttl_thread = std::thread(&LlamaEmbedder::ttlWorker, this);
}

LlamaEmbedder::~LlamaEmbedder() {
    {
        std::lock_guard<std::mutex> lock(mtx);
        worker_running = false;
    }
    cv.notify_all();
    if (ttl_thread.joinable()) {
        ttl_thread.join();
    }
    suspend();
    llama_backend_free();
}

void LlamaEmbedder::ttlWorker() {
    while (worker_running) {
        std::unique_lock<std::mutex> lock(mtx);
        
        // 1. Wait until a request completes and sets needs_suspend to true
        cv.wait(lock, [this] { return needs_suspend || !worker_running; });

        if (!worker_running) break;

        // 2. Wait for 30 seconds. 
        // If a new request comes in, it will notify the CV and 'interrupted' will be true.
        bool interrupted = cv.wait_for(lock, std::chrono::seconds(30), [this] { 
            return !needs_suspend || !worker_running; 
        });

        // 3. THE FIX: Check if we timed out AND if suspension is still required.
        if (!interrupted && needs_suspend && worker_running) {
            std::cout << "[LlamaEmbedder] TTL expired, suspending model..." << std::endl;
            suspend();
            needs_suspend = false; // Reset the flag after suspending
        }
    }
}

std::vector<float> LlamaEmbedder::embedDocument(const std::string& text) { 
    return getEmbedding("search_document: " + text); 
}

std::vector<float> LlamaEmbedder::embedSearchQuery(const std::string& text) { 
    return getEmbedding("search_query: " + text); 
}

int LlamaEmbedder::getTokenCount(const std::string& text) {
    std::lock_guard<std::mutex> lock(mtx);
    
    // Load model if not already loaded (needed for vocab)
    load();
    
    if (!model) {
        throw std::runtime_error("LlamaEmbedder: Failed to initialize model for tokenization.");
    }
    
    if (!vocab) {
        throw std::runtime_error("LlamaEmbedder: Vocabulary not available - model may not be properly loaded.");
    }
    
    auto tokens = tokenize(text);
    return (int)tokens.size();
}

void LlamaEmbedder::suspend() {
    if (ctx) { llama_free(ctx); ctx = nullptr; }
    if (model) { llama_model_free(model); model = nullptr; }
    std::cout << "LlamaEmbedder suspended: VRAM freed." << std::endl;
}

const std::string& LlamaEmbedder::getModelPath() const {
    return model_path;
}

std::vector<float> LlamaEmbedder::getEmbedding(const std::string& text) {


    std::lock_guard<std::mutex> lock(mtx);
    
    // Cancel any pending suspension because we are active now
    needs_suspend = false;
    cv.notify_all();

    load();
    
    if (!model || !ctx) {
        throw std::runtime_error("LlamaEmbedder: Failed to initialize model or context.");
    }

    auto tokens = tokenize(text);
    int n_tokens = (int)tokens.size();

    // Handle case where tokenization returns no tokens
    if (n_tokens == 0) {
        std::cout << "Warning: Tokenization returned 0 tokens for text: " << text.substr(0, 100) << "..." << std::endl;
        // Return zero embedding of correct dimension
        load(); // Ensure model is loaded to get n_embd
        return std::vector<float>(n_embd, 0.0f);
    }

    llama_batch batch = llama_batch_init(n_tokens, 0, 1);
    for (int i = 0; i < n_tokens; i++) {
        batch.token[i] = tokens[i];
        batch.pos[i] = i;
        batch.n_seq_id[i] = 1;
        batch.seq_id[i][0] = 0;
        batch.logits[i] = false;
    }
    // Enable logits for the last token to get embeddings
    if (n_tokens > 0) {
        batch.logits[n_tokens - 1] = true;
    }
    batch.n_tokens = n_tokens;

    // Clear previous KV cache values (irrelevant for embeddings)
    llama_memory_clear(llama_get_memory(ctx), true);

    if (llama_decode(ctx, batch) != 0) {
        llama_batch_free(batch);
        throw std::runtime_error("llama_decode failed");
    }

    float* embd = llama_get_embeddings_seq(ctx, 0);
    if (embd == nullptr) {
        llama_batch_free(batch);
        return std::vector<float>(n_embd, 0.0f);
    }

    std::vector<float> result(n_embd);
    std::copy(embd, embd + n_embd, result.begin());

    float norm = 0.0f;
    for (float x : result) norm += x * x;
    norm = std::sqrt(norm);
    if (norm > 1e-6f) { for (float& x : result) x /= norm; }

    llama_batch_free(batch);
    
    // Signal that we are done and the 30s timer should start
    needs_suspend = true;
    cv.notify_all();

    return result;
}

std::vector<llama_token> LlamaEmbedder::tokenize(const std::string& text) const {
    if (!vocab) {
        throw std::runtime_error("Vocabulary not initialized for tokenization");
    }
    
    // First call to get the number of tokens needed
    int n_tokens = llama_tokenize(vocab, text.c_str(), (int)text.size(), NULL, 0, false, false);
    
    if (n_tokens == std::numeric_limits<int32_t>::min()) {
        throw std::runtime_error("Tokenization failed: input text too large");
    }
    
    if (n_tokens < 0) {
        // Negative value means we need to call again with the right buffer size
        n_tokens = -n_tokens;
    }
    
    std::vector<llama_token> tokens(n_tokens);
    int result = llama_tokenize(vocab, text.c_str(), (int)text.size(), tokens.data(), n_tokens, false, false);
    
    if (result != n_tokens) {
        throw std::runtime_error("Tokenization failed: inconsistent token count");
    }
    
    return tokens;
}

void LlamaEmbedder::load() {
    if (model) return;
    llama_model_params m_params = llama_model_default_params();
    m_params.n_gpu_layers = 100; // Load fully to GPU if possible
    model = llama_model_load_from_file(model_path.c_str(), m_params);
    if (!model) throw std::runtime_error("Failed to load embedder model");

    llama_context_params c_params = llama_context_default_params();
    c_params.embeddings = true;
    ctx = llama_init_from_model(model, c_params);
    if (!ctx) throw std::runtime_error("Failed to create embedder context");

    vocab = llama_model_get_vocab(model);
    n_embd = llama_model_n_embd(model);
}
