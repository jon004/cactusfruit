import json
import os

def main():
    config_raw = os.environ.get("MODEL_CONFIG_ARG", "{}")
    try:
        config = json.loads(config_raw)
    except json.JSONDecodeError:
        config = {}

    params = config.get("params", {})
    
    env_content = [
        f"SYSTEM_PROMPT={config.get('system_prompt', 'You are a helpful assistant.')}",
        f"MODEL_NAME={config.get('type', 'generative')}",
        f"MODEL_PARAMS={json.dumps(params)}",
        f"THREADS={params.get('threads', 8)}",
        f"PARALLEL={params.get('parallel', 4)}"
    ]

    with open("/app/.env", "w") as f:
        f.write("\n".join(env_content) + "\n")

if __name__ == "__main__":
    main()
