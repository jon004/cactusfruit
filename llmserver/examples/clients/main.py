# main.py
import os
<<<<<<< Updated upstream
from llmserverclient import LlmServerClient

def main():
    model_path = "/Users/jon/.localdoby/models/qwen2.5-vl-3b/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf"
    mmproj_path = "/Users/jon/.localdoby/models/qwen2.5-vl-3b/Qwen2.5-VL-3B-Instruct.mmproj-fp16.gguf"
    image_name = "caty-kitty-went-to-sleep-386953015-1850325431.jpg"

    client = LlmServerClient(generator_model_path=model_path)

    print("=== 1. Testing Text Generation (POST /m/prompt) ===")
    prompt_text = "Give me a one-sentence summary of the tundra."
    print(f"Prompt: {prompt_text}")
=======
import sys
import requests
from llmserverclient import LlmServerClient

def download_file(url: str, dest_path: str):
    print(f"Downloading {url} to {dest_path}...")
    response = requests.get(url, stream=True, allow_redirects=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    
    downloaded = 0
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="", flush=True)
    print("\nDownload complete!")

def main():
    # Resolve absolute paths based on main.py's location (/Users/jon/Code/cactusfruit/llmserver/examples/clients)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(current_dir, "models", "qwen2.5-vl-3b")
    
    default_model_path = os.path.join(models_dir, "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf")
    default_mmproj_path = os.path.join(models_dir, "mmproj-model-f16.gguf")
    image_path = os.path.join(current_dir, "caty-kitty-went-to-sleep-386953015-1850325431.jpg")

    model_path = default_model_path
    mmproj_path = default_mmproj_path

    # Check if models exist locally
    if not os.path.exists(model_path) or not os.path.exists(mmproj_path):
        print(f"Required model files not found locally at '{models_dir}'.")
        
        download_choice = input("Would you like to download the Qwen2.5-VL-3B model and vision projector automatically? (y/N): ").strip().lower()
        
        if download_choice == 'y':
            os.makedirs(models_dir, exist_ok=True)
            
            if not os.path.exists(model_path):
                print("Downloading text model (~1.9 GB)...")
                download_file(
                    "https://huggingface.co/lmstudio-community/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
                    model_path
                )
            else:
                print("Text model already exists locally, skipping download.")

            if not os.path.exists(mmproj_path):
                print("Downloading vision projector (~1.25 GB)...")
                download_file(
                    "https://huggingface.co/lmstudio-community/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/mmproj-model-f16.gguf",
                    mmproj_path
                )
            else:
                print("Vision projector already exists locally, skipping download.")
        else:
            print("\nDownload declined.")
            path_choice = input("Would you like to provide a custom absolute path to an existing model instead? (y/N): ").strip().lower()
            if path_choice == 'y':
                model_path = input("Enter absolute path to your text model (.gguf): ").strip()
                mmproj_path = input("Enter absolute path to your vision projector (.gguf): ").strip()
                if not os.path.exists(model_path) or not os.path.exists(mmproj_path):
                    print("Error: Provided model paths do not exist. Exiting.")
                    sys.exit(1)
            else:
                print("No model provided. Exiting.")
                sys.exit(0)

    # Initialize client with absolute paths
    client = LlmServerClient(generator_model_path=model_path)

    print(f"\nUsing Absolute Model Path: {model_path}")
    print(f"Using Absolute Vision Projector Path: {mmproj_path}")

    print("\n=== 1. Testing Text Generation (POST /m/prompt) ===")
    prompt_tex = "Give me a one-sentence summary of the tundra."
    print(f"Prompt: {prompt_tex}")
>>>>>>> Stashed changes
    
    try:
        response_text = client.generate(
            role="user",
<<<<<<< Updated upstream
            content=prompt_text,
=======
            content=prompt_tex,
>>>>>>> Stashed changes
            n_ctx=4096
        )
        print(f"Response: {response_text}\n")
    except Exception as e:
        print(f"Text generation failed: {e}\n")

    print("=== 2. Testing Vision Generation (POST /m/prompt/image) ===")
<<<<<<< Updated upstream
    if os.path.exists(image_name):
        print(f"Loading image from local directory: {image_name}")
        with open(image_name, "rb") as f:
=======
    
    if not os.path.exists(image_path):
        print(f"Sample image not found locally.")
        img_choice = input("Do you want to download a sample test image from Hugging Face? (y/N): ").strip().lower()
        if img_choice == 'y':
            sample_img_url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/tasks/cat.jpg"
            try:
                download_file(sample_img_url, image_path)
            except Exception as e:
                print(f"Failed to download sample image: {e}")

    if os.path.exists(image_path):
        print(f"Loading image from local path: {image_path}")
        with open(image_path, "rb") as f:
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
        print(f"Image not found at '{image_name}', skipping vision test.\n")
=======
        print(f"Image not found, skipping vision test.\n")
>>>>>>> Stashed changes

if __name__ == "__main__":
    main()
