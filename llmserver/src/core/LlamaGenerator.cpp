#include "core/LlamaGenerator.h"

#include <iostream>
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <memory>

#ifndef GGML_ABORT
#define GGML_ABORT(...) do { fprintf(stderr, __VA_ARGS__); exit(EXIT_FAILURE); } while (0)
#endif

LlamaGenerator::LlamaGenerator(const std::string& model_path, const std::string& chat_template)
: model_path(model_path), chat_template(chat_template), model(nullptr)
{
    if (model_path.empty()) {
        throw std::invalid_argument("Model path cannot be empty!");
    }
}

bool LlamaGenerator::isLoaded() const {
    return model != nullptr;
}

void LlamaGenerator::load() {
    std::lock_guard<std::mutex> lock(mtx_);
    
    if (model) return; 

    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = n_gpu_layers; 

    model = llama_model_load_from_file(model_path.c_str(), model_params);
    if (!model) {
        throw std::runtime_error("Failed to load model from: " + model_path);
    }

    vocab = llama_model_get_vocab(model);
}

void LlamaGenerator::release() {
    std::lock_guard<std::mutex> lock(mtx_);
    if (model) {
        llama_model_free(model);
        model = nullptr;
    }
    vocab = nullptr;
}

LlamaGenerator::~LlamaGenerator() {
    release();
}

LlamaGenerator::LlamaGenerator(LlamaGenerator&& other) noexcept {
    std::lock_guard<std::mutex> lock(other.mtx_);
    moveFrom(std::move(other));
}

LlamaGenerator& LlamaGenerator::operator=(LlamaGenerator&& other) noexcept {
    if (this != &other) {
        std::unique_lock<std::mutex> lock1(mtx_, std::defer_lock);
        std::unique_lock<std::mutex> lock2(other.mtx_, std::defer_lock);
        std::lock(lock1, lock2);
        
        release();
        moveFrom(std::move(other));
    }
    return *this;
}

std::string LlamaGenerator::generate(llama_context *ctx, const std::string& prompt, const SamplingParams& params, TokenCallback on_token) {
    if (!ctx) throw std::runtime_error("generate(): ctx cannot be null");
    if (prompt.empty()) throw std::runtime_error("generate(): prompt cannot be empty");

    const bool is_first = llama_memory_seq_pos_max(llama_get_memory(ctx), 0) == -1;

    // 1. Tokenize the prompt
    const int n_prompt_tokens = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), NULL, 0, is_first, true);
    std::vector<llama_token> prompt_tokens(n_prompt_tokens);
    if (llama_tokenize(vocab, prompt.c_str(), prompt.size(), prompt_tokens.data(), prompt_tokens.size(), is_first, true) < 0) {
        GGML_ABORT("failed to tokenize the prompt\n");
    }

    const int n_batch = llama_n_batch(ctx);
    const int n_ctx = llama_n_ctx(ctx);

    // 2. Process prompt tokens in chunks
    for (int i = 0; i < (int)prompt_tokens.size(); i += n_batch) {
        int n_eval = (int)prompt_tokens.size() - i;
        if (n_eval > n_batch) {
            n_eval = n_batch;
        }

        int n_ctx_used = llama_memory_seq_pos_max(llama_get_memory(ctx), 0) + 1;
        if (n_ctx_used + n_eval > n_ctx) {
            fprintf(stderr, "context size exceeded during prompt processing\n");
            throw std::runtime_error("generate(): context size exceeded");
        }

        llama_batch batch = llama_batch_get_one(&prompt_tokens[i], n_eval);
        if (llama_decode(ctx, batch) != 0) {
            throw std::runtime_error("failed to decode prompt chunk\n");
        }
    }

    // 3. Dynamic Request-Scoped Sampler Setup wrapped safely
    struct SamplerDeleter {
        void operator()(llama_sampler* s) const { if (s) llama_sampler_free(s); }
    };
    
    llama_sampler_chain_params lparams = llama_sampler_chain_default_params();
    std::unique_ptr<llama_sampler, SamplerDeleter> smpl(llama_sampler_chain_init(lparams));
    
    llama_sampler_chain_add(smpl.get(), llama_sampler_init_top_k(params.top_k));
    llama_sampler_chain_add(smpl.get(), llama_sampler_init_top_p(params.top_p, 1));
    llama_sampler_chain_add(smpl.get(), llama_sampler_init_temp(params.temp));
    
    // Natively inject penalties using the 4-argument signature
    if (params.penalty != 1.0f || params.penalty_freq != 0.0f || params.penalty_present != 0.0f) {
        llama_sampler_chain_add(smpl.get(), llama_sampler_init_penalties(
            llama_vocab_n_tokens(vocab),
            params.penalty_last_n,
            params.penalty,
            params.penalty_freq,
            params.penalty_present
        ));
    }
    
    llama_sampler_chain_add(smpl.get(), llama_sampler_init_dist(LLAMA_DEFAULT_SEED));

    // CRITICAL: Feed historical prompt tokens into the sampler to establish penalty baseline
    for (const auto& token : prompt_tokens) {
        llama_sampler_accept(smpl.get(), token);
    }

    // 4. Generation Loop
    llama_token new_token_id;
    std::string response;
    int32_t tokens_generated = 0;
    
    llama_batch batch = llama_batch_get_one(nullptr, 0); 

    while (true) {
        // Sample the next token
        new_token_id = llama_sampler_sample(smpl.get(), ctx, -1);
        
        // IMPORTANT: Tell sampler we picked this token so repetition penalties apply to next evaluation
        llama_sampler_accept(smpl.get(), new_token_id);

        if (llama_vocab_is_eog(vocab, new_token_id)) {
            break;
        }

        char buf[256];
        int n = llama_token_to_piece(vocab, new_token_id, buf, sizeof(buf), 0, true);
        if (n < 0) {
            GGML_ABORT("failed to convert token to piece\n");
        }
        
        std::string token_str(buf, n);
        response += token_str;
        if (on_token) on_token(token_str);

        tokens_generated++;
        if (params.max_new_tokens > 0 && tokens_generated >= params.max_new_tokens) {
            break; // Stop generation if maximum limits reached
        }

        batch = llama_batch_get_one(&new_token_id, 1);

        int n_ctx_used = llama_memory_seq_pos_max(llama_get_memory(ctx), 0) + 1;
        if (n_ctx_used + 1 > n_ctx) {
            fprintf(stderr, "context size exceeded during generation\n");
            break; 
        }

        if (llama_decode(ctx, batch) != 0) {
            throw std::runtime_error("failed to decode sampled token\n");
        }
    }

    return response;
}

void LlamaGenerator::prefill(llama_context *ctx, const std::string &prompt) {
    if (!ctx || prompt.empty()) return;

    const bool is_first = llama_memory_seq_pos_max(llama_get_memory(ctx), 0) == -1;
    const int n_prompt_tokens = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), NULL, 0, is_first, true);
    std::vector<llama_token> prompt_tokens(n_prompt_tokens);
    llama_tokenize(vocab, prompt.c_str(), prompt.size(), prompt_tokens.data(), prompt_tokens.size(), is_first, true);

    int n_batch = llama_n_batch(ctx);

    for (int i = 0; i < (int)prompt_tokens.size(); i += n_batch) {
        int n_eval = (int)prompt_tokens.size() - i;
        if (n_eval > n_batch) n_eval = n_batch;

        llama_batch batch = llama_batch_get_one(&prompt_tokens[i], n_eval);
        if (llama_decode(ctx, batch) != 0) {
            throw std::runtime_error("llama_decode failed during prefill");
        }
    }
}

std::string LlamaGenerator::toChatTemplate(const std::vector<llama_chat_message>& messages, bool add_assistant) {
    if (messages.empty()) return "";

    const char* tmpl = chat_template.empty() ? nullptr : chat_template.c_str();

    int32_t required_size = llama_chat_apply_template(
        tmpl, messages.data(), messages.size(), add_assistant, nullptr, 0
    );

    if (required_size < 0) {
        throw std::runtime_error("Failed to get required buffer size for chat template");
    }

    std::vector<char> buffer(required_size + 1);

    int32_t used = llama_chat_apply_template(
        tmpl, messages.data(), messages.size(), add_assistant, buffer.data(), static_cast<int32_t>(buffer.size())
    );

    if (used < 0 || used > static_cast<int32_t>(buffer.size())) {
        throw std::runtime_error("Failed to apply chat template");
    }

    return std::string(buffer.data(), used);
}

int32_t LlamaGenerator::chatTemplateSize(const std::vector<llama_chat_message>& messages) const {
    if (messages.empty()) return 0;
    const char* tmpl = chat_template.empty() ? nullptr : chat_template.c_str();
    int32_t size = llama_chat_apply_template(tmpl, messages.data(), messages.size(), false, nullptr, 0);

    if (size < 0) {
        throw std::runtime_error("Failed to apply chat template.");
    }
    return size; 
}

void LlamaGenerator::moveFrom(LlamaGenerator&& other) noexcept {
    model = other.model;
    other.model = nullptr;
    
    vocab = other.vocab;
    other.vocab = nullptr;
    
    model_path = std::move(other.model_path);
    chat_template = std::move(other.chat_template);
    n_gpu_layers = other.n_gpu_layers;
}
