#!/usr/bin/env python3
"""
Simple Interactive Chat Client for LLMServer

Updated to align with current API specifications and model path handling.
"""

import json
import os
from llm_chat_client import LLMChatClient

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_help():
    """Print help information."""
    print("\nAvailable commands:")
    print("  /clear                 - Clear the screen")
    print("  /exit                  - Exit the program")
    print("  /help                  - Show this help message")
    print("  /reset                 - Reset the conversation context")
    print("  /status                - Show server status")
    print("  /model <path>          - Switch the active Llama model file path")
    print("  /role <name>           - Set your message role (default: user)")
    print("  /context               - Show conversation history")
    print("  <message>              - Send a message to the LLM")
    print("\nExample: /model models/llama-3-8b.gguf")
    print("Example: /role assistant")
    print()

def print_context(context: list) -> None:
    """Print the conversation context in a readable format."""
    if not context:
        print("\nNo conversation history.")
        return
        
    print("\n=== Conversation Context ===")
    for msg in context:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        print(f"{role.upper()}: {content}")
    print("==========================\n")

def print_status(status: dict) -> None:
    """Print server status information."""
    print("\n=== Server Status ===")
    for key, value in status.items():
        print(f"{key}: {value}")
    print("===================\n")

def main():
    print("LLMServer Interactive Chat Client")
    print("Type '/help' for available commands\n")
    
    # Prompt user for an initial model path since the API requires it
    default_model = input("Enter default model path (e.g., models/llama.gguf): ").strip()
    if not default_model:
        default_model = "models/llama.gguf"
        
    client = LLMChatClient(default_model_path=default_model)
    
    # Check server status
    status = client.get_llm_status()
    print(f"Initial Server Status: {status}")
    
    try:
        while True:
            try:
                prompt_label = f"[{os.path.basename(client.default_model_path)}] You: "
                user_input = input(prompt_label).strip()
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.lower() == '/help':
                    print_help()
                    continue
                    
                if user_input.lower() == '/exit':
                    print("Goodbye!")
                    break
                    
                if user_input.lower() == '/reset':
                    if client.post_llm_reset():
                        print(f"Conversation context reset successfully.")
                    else:
                        print("Failed to reset conversation.")
                    continue
                    
                if user_input.lower() == '/status':
                    status = client.get_llm_status()
                    print_status(status)
                    continue
                    
                if user_input.lower() == '/clear':
                    clear_screen()
                    continue
                    
                if user_input.lower() == '/context':
                    print("\nFetching conversation context from server...")
                    context_data = client.get_llm_context()
                    if 'messages' in context_data:
                        print_context(context_data['messages'])
                    else:
                        print(f"\nResponse: {context_data}")
                    continue
                
                # Handle model switching (replacing the old agent system)
                if user_input.lower().startswith('/model '):
                    new_model = user_input[7:].strip()
                    if new_model:
                        client.default_model_path = new_model
                        print(f"Active model path set to: {new_model}")
                    else:
                        print("Please specify a model path.")
                    continue
                
                # Handle role setting
                if user_input.lower().startswith('/role '):
                    new_role = user_input[6:].strip()
                    if new_role:
                        client.set_role(new_role)
                        print(f"Role set to: {new_role}")
                    else:
                        print("Please specify a role.")
                    continue
                
                # Send message to LLM
                print("\n[Assistant] ", end='', flush=True)
                try:
                    response = client.post_llm_prompt(user_input)
                    print(f"{response}\n")
                except Exception as e:
                    print(f"\nError communicating with server: {str(e)}\n")
                
            except KeyboardInterrupt:
                print("\nUse '/exit' to quit or '/help' for commands.")
                continue
                
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")

if __name__ == "__main__":
    main()
