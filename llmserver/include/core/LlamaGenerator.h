#pragma once

#include <string>       
#include <vector>       
#include <functional>   
#include <stdexcept>    
#include <mutex>        
#include "llama.h"
#include <nlohmann/json.hpp> 

typedef struct llama_model llama_model;
typedef struct llama_context llama_context;
typedef struct llama_vocab llama_vocab;
typedef struct llama_batch llama_batch;
typedef struct llama_chat_message llama_chat_message; 

struct SamplingParams {
    float temp = 0.4f;
    float top_p = 0.95f;
    int32_t top_k = 40;
    
    float penalty = 1.0f; // Default to 1.0 (no penalty applies)
    int32_t penalty_last_n = 64;
    float penalty_freq = 0.0f;
    float penalty_present = 0.0f;
    
    int32_t max_new_tokens = -1;

    static SamplingParams from_json(const nlohmann::json& j) {
        SamplingParams p;
        p.temp = j.value("temperature", 0.4f);
        p.top_p = j.value("top_p", 0.95f);
        p.top_k = j.value("top_k", 40);
        p.penalty = j.value("repetition_penalty", 1.0f);
        p.penalty_last_n = j.value("penalty_last_n", 64);
        p.penalty_freq = j.value("penalty_freq", 0.0f);
        p.penalty_present = j.value("penalty_present", 0.0f);
        p.max_new_tokens = j.value("max_new_tokens", -1);
        return p;
    }
};

class LlamaGenerator {
public:
    using TokenCallback = std::function<void(const std::string&)>;

    llama_model* model = nullptr;   

    std::string model_path;   
    std::string chat_template;

    LlamaGenerator(const std::string& model_path, const std::string& chat_template = "");
    ~LlamaGenerator();

    LlamaGenerator(const LlamaGenerator&) = delete;
    LlamaGenerator& operator=(const LlamaGenerator&) = delete;
    LlamaGenerator(LlamaGenerator&& other) noexcept;
    LlamaGenerator& operator=(LlamaGenerator&& other) noexcept;

    std::string generate(llama_context *ctx, const std::string& prompt, const SamplingParams& params = SamplingParams(), TokenCallback on_token = nullptr);

    void prefill(llama_context *ctx, const std::string &prompt);

    void load();      
    void release();     
    bool isLoaded() const; 
    llama_model* getModel() const { return model; }

    int getGpuLayers() const { return n_gpu_layers; }
    void setGpuLayers(int layers) { 
        if (n_gpu_layers != layers) {
            n_gpu_layers = layers; 
            release(); // Forces a reload next time load() is called
        }
    }

    std::string toChatTemplate(const std::vector<llama_chat_message>& messages, bool add_assistant = true);
    int32_t chatTemplateSize(const std::vector<llama_chat_message>& messages) const;

private:
    mutable std::mutex mtx_;
    const llama_vocab* vocab = nullptr;   
    int n_gpu_layers = 100; // Represents offloading everything to GPU (equivalent to device_map="auto")

    void moveFrom(LlamaGenerator&& other) noexcept;
};