#include "core/Prompter.h"

#include <sstream>          
#include <cstdio>           
#include "llama.h"
#include "core/LlamaGenerator.h" 

inline llama_chat_message to_llama_chat_message(const AgentMessage& msg) {
    return { msg.role.c_str(), msg.content.c_str() };
}

Prompter::Prompter(LlamaGenerator& llm) 
: llm(llm), 
  ctx(nullptr, Prompter::LlamaContextDeleter) {
}

Prompter::~Prompter() {
    try {
        ctx.reset();
    } catch (...) {
        std::cerr << "Error during AgentBaseClass destruction" << std::endl;
    }
}

std::string Prompter::generate(const std::string& role, const std::string& content, const SamplingParams& params) {
    load();
    if (!ctx) {
        throw std::runtime_error("LLaMA context is not initialized");
    }
    if (content.empty()) {
        throw std::invalid_argument("Prompt content must not be empty");
    }
    if (role.empty()) {
        throw std::invalid_argument("Prompt role must not be empty");
    }
    if (content.length() > 10000) { 
        throw std::invalid_argument("Prompt content is too long.");
    }
    if (role.length() > 25) {
        throw std::invalid_argument("Prompt role is too long.");
    }
    
    message_history.push_back({ role, content });
    messagePreProcessing(message_history[message_history.size() - 1]);
    
    std::vector<llama_chat_message> temp_messages;
    temp_messages.reserve(message_history.size());
    for (const auto& msg : message_history) {
        temp_messages.push_back(to_llama_chat_message(msg));
    }
    std::string prompt = messagesToPrompt(temp_messages, true);

    std::string response = llm.generate(ctx.get(), prompt, params);

    message_history.push_back({ "assistant", response });
    temp_messages.push_back(to_llama_chat_message(message_history.back()));
    prev_templatized_chat_size = llm.chatTemplateSize(temp_messages);
    
    this->saveState();
    return response;
}

std::string Prompter::chatToJson() const {
    std::stringstream ss;
    ss << "{\"messages\": [";
    
    bool first = true;
    for (size_t i = 0; i < message_history.size(); ++i) {
        const auto& msg = message_history[i];
        if (!first) {
            ss << ",";
        }
        ss << "{\"role\":\"" << escapeJson(msg.role) 
           << "\",\"content\":\"" << escapeJson(msg.content) << "\"}";
        first = false;
    }
    
    ss << "]}";
    return ss.str();
}

void Prompter::resetContext() {
    ctx.reset();            
    kv_cache_buffer.clear(); 
    message_history.clear(); 
    prev_templatized_chat_size = 0;
}

void Prompter::prefill(const std::vector<std::pair<std::string, std::string>>& messages) {
    if (messages.empty()) {
        return;  
    }
    
    for (const auto& [role, content] : messages) {
        message_history.push_back({role, content});
    }

    load();  
    
    if (!ctx) {
        throw std::runtime_error("LLaMA context is not initialized after load");
    }
    
    prefillContextFromMessageHistory();
}

void Prompter::saveState() {
    if (!ctx) return;
    size_t state_size = llama_state_get_size(ctx.get());
    kv_cache_buffer.resize(state_size);

    llama_state_get_data(
        ctx.get(), 
        kv_cache_buffer.data(), 
        kv_cache_buffer.size() 
    );
}

void Prompter::loadState() {
    if (!ctx || kv_cache_buffer.empty()) return;

    if (kv_cache_buffer.size() > llama_state_get_size(ctx.get())) {
        std::cerr << "Warning: Saved state size mismatch." << std::endl;
        return;
    }

    llama_state_set_data(
        ctx.get(), 
        kv_cache_buffer.data(), 
        kv_cache_buffer.size() 
    );
}

void Prompter::load() {
    try {
        if (!llm.isLoaded()) {
            llm.load();
        }
        
        if (!ctx) {
            initContext();
        }

        llama_memory_t mem = llama_get_memory(ctx.get());
        bool contextLoaded = llama_memory_seq_pos_max(mem, 0) != -1;
        
        if (!contextLoaded && !message_history.empty()) {
            prefillContextFromMessageHistory();
        }
    } catch (...) {
        ctx.reset();
        throw;
    }
}

void Prompter::loadContextParams(llama_context_params& ctx_params) const {
    ctx_params.n_ctx = this->n_ctx;
    ctx_params.n_batch = 512;
    ctx_params.n_ubatch = 512;
}

void Prompter::systemPrefill(std::vector<AgentMessage>& /* message_history */) {
}

void Prompter::messagePreProcessing(AgentMessage& /* message */) {
}

void Prompter::initContext() {
    if (!ctx) {
        if (!llm.isLoaded() || !llm.getModel()) {
            throw std::runtime_error("Model is not loaded - cannot initialize context");
        }
        
        llama_context_params ctx_params = llama_context_default_params();
        loadContextParams(ctx_params);

        llama_context* new_ctx = llama_init_from_model(llm.getModel(), ctx_params);
        if (!new_ctx) {
            throw std::runtime_error("Failed to initialize LLaMA context");
        }
        ctx.reset(new_ctx);

        if (!kv_cache_buffer.empty()) {
            this->loadState();
            std::vector<llama_chat_message> temp_messages;
            for (const auto& msg : message_history) {
                temp_messages.push_back(to_llama_chat_message(msg));
            }
            prev_templatized_chat_size = llm.chatTemplateSize(temp_messages);
        }
    }
}

void Prompter::LlamaContextDeleter(llama_context* p) {
    if (p) {
        llama_free(p);
    }
}

std::string Prompter::generateWithLogging(const std::string& templatized_prompt, const SamplingParams& params) const {
    std::string generated_response = llm.generate(ctx.get(), templatized_prompt, params, [](std::string nextToken) {
        std::cout << nextToken;
    });
    std::cout << std::endl;
    return generated_response;
}

std::string Prompter::escapeJson(const std::string& s) {
    std::string result;
    result.reserve(s.length() * 2); 
    
    for (char c : s) {
        switch (c) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\b': result += "\\b"; break;
            case '\f': result += "\\f"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default:
                if (c >= 0 && c <= 0x1F) {
                    char buf[7];
                    snprintf(buf, sizeof(buf), "\\u%04x", (unsigned char)c);
                    result += buf;
                } else {
                    result += c;
                }
        }
    }
    return result;
}

std::string Prompter::messagesToPrompt(std::vector<llama_chat_message> messages, bool add_assistant) {
    std::string full_prompt = llm.toChatTemplate(messages, add_assistant);
    std::string truncated_prompt = full_prompt.substr(prev_templatized_chat_size);
    return truncated_prompt;
}

void Prompter::prefillContextFromMessageHistory() {
    std::vector<llama_chat_message> temp_messages;
    temp_messages.reserve(message_history.size());
    for (const auto& msg : message_history) {
        temp_messages.push_back(to_llama_chat_message(msg));
    }

    std::string prompt = messagesToPrompt(temp_messages, false);

    if (!prompt.empty()) {
        if (!ctx) {
            throw std::runtime_error("LLaMA context is not initialized in prefillContextFromMessageHistory");
        }
        
        llm.prefill(ctx.get(), prompt); 
    }
    
    prev_templatized_chat_size = llm.chatTemplateSize(temp_messages);
}
