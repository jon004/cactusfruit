# main.py
import os
from llmserverclient import LlmServerClient

def main():
    model_path = "/Users/jon/.localdoby/models/qwen2.5-vl-3b/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf"
    mmproj_path = "/Users/jon/.localdoby/models/qwen2.5-vl-3b/Qwen2.5-VL-3B-Instruct.mmproj-fp16.gguf"
    image_name = "caty-kitty-went-to-sleep-386953015-1850325431.jpg"

    client = LlmServerClient(generator_model_path=model_path)

    print("=== 1. Testing Text Generation (POST /m/prompt) ===")
    prompt_text = "Give me a one-sentence summary of the tundra."
    print(f"Prompt: {prompt_text}")
    
    try:
        response_text = client.generate(
            role="user",
            content=prompt_text,
            n_ctx=4096
        )
        print(f"Response: {response_text}\n")
    except Exception as e:
        print(f"Text generation failed: {e}\n")

    print("=== 2. Testing Vision Generation (POST /m/prompt/image) ===")
    if os.path.exists(image_name):
        print(f"Loading image from local directory: {image_name}")
        with open(image_name, "rb") as f:
            image_bytes = f.read()

        vision_prompt = "Describe this image in one sentence."
        print(f"Prompt: {vision_prompt}")
        try:
            vision_response = client.generate_with_image(
                role="user",
                content=vision_prompt,
                image_bytes=image_bytes,
                mmproj_path=mmproj_path,
                n_ctx=8192
            )
            print(f"Response: {vision_response}\n")
        except Exception as e:
            print(f"Vision generation failed: {e}\n")
    else:
        print(f"Image not found at '{image_name}', skipping vision test.\n")

if __name__ == "__main__":
    main()
