#pragma once

#include <string>
#include <vector>
#include <memory>
#include <stdexcept>
#include <iostream>
#include <utility>

#include "llama.h"
#include "core/LlamaGenerator.h"

struct AgentMessage {
    std::string role;
    std::string content;
};

class Prompter {
public:
    explicit Prompter(LlamaGenerator& llm);
    virtual ~Prompter();

    Prompter(const Prompter&) = delete;
    Prompter& operator=(const Prompter&) = delete;
    
    std::string generate(const std::string& role, const std::string& content, const SamplingParams& params = SamplingParams());
    
    std::string chatToJson() const;
    void resetContext();
    void prefill(const std::vector<std::pair<std::string, std::string>>& messages);

    void saveState();
    void loadState();

    int getContextSize() const { return n_ctx; }
    void setContextSize(int ctx_size) { 
        if (n_ctx != ctx_size) {
            n_ctx = ctx_size;
            ctx.reset();
            kv_cache_buffer.clear();
            prev_templatized_chat_size = 0;
        }
    }

protected:
    std::vector<uint8_t> kv_cache_buffer;
    void load();
    virtual void loadContextParams(llama_context_params& ctx_params) const;
    
    virtual void systemPrefill(std::vector<AgentMessage>& message_history);
    virtual void messagePreProcessing(AgentMessage& message);
    
    void initContext();

private:
    int32_t prev_templatized_chat_size = 0;
    int n_ctx = 2048; 
    LlamaGenerator& llm;
    std::vector<AgentMessage> message_history;

    static void LlamaContextDeleter(llama_context* p);
    std::unique_ptr<llama_context, decltype(&LlamaContextDeleter)> ctx; 

    std::string generateWithLogging(const std::string& templatized_prompt, const SamplingParams& params) const;
    static std::string escapeJson(const std::string& s);
    std::string messagesToPrompt(std::vector<llama_chat_message> messages, bool add_assistant = true);
    void prefillContextFromMessageHistory();
};
