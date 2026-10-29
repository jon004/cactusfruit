
#!/usr/bin/env bash
# deploy.sh - Local CactusFruit Docker development utility
set -Eeuo pipefail

MODELS_JSON="models.json"
IMAGE_NAMESPACE="cactusfruit"
CONTAINER_PREFIX="cactusfruit"
ENV_FILE=".cactusfruit/local.env"
CONTAINER_PORT=8000

BUILD_ENABLED=false
RUN_ENABLED=false
PURGE_ENABLED=false
SELECTED_MODULES=()

error_exit() {
    echo "ERROR: $*" >&2
    exit 1
}

show_help() {
    cat <<'EOF'
Usage:
  ./deploy.sh --modules [names...] [OPTIONS]

Options:
  --modules [names...]  Modules from models.json (pipeline is also supported)
  --build               Build Docker images for selected modules
  --run                 Run selected servers in the background
  --purge-docker        Purge Docker build cache before processing
  -h, --help            Show this help message

Examples:
  ./deploy.sh --modules embedder --build
  ./deploy.sh --modules embedder reranker --build --run
  ./deploy.sh --modules pipeline --run
  ./deploy.sh --modules embedder --purge-docker --build --run

Behavior:
  - --build and --run can be used together.
  - --run uses existing local images; it does not build implicitly.
  - Existing running containers are left untouched.
  - Host ports are allocated dynamically by Docker.
  - Service URLs are written to .cactusfruit/local.env.
EOF
}

# Parse arguments.
while (($#)); do
    case "$1" in
        --modules)
            shift
            while (($#)) && [[ "$1" != --* && "$1" != "-h" ]]; do
                SELECTED_MODULES+=("$1")
                shift
            done
            ;;
        --build)
            BUILD_ENABLED=true
            shift
            ;;
        --run)
            RUN_ENABLED=true
            shift
            ;;
        --purge-docker)
            PURGE_ENABLED=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error_exit "Unknown argument: $1"
            ;;
    esac
done

if [[ "$BUILD_ENABLED" == false && "$RUN_ENABLED" == false && "$PURGE_ENABLED" == false ]]; then
    show_help
    exit 0
fi

if [[ ! -f "$MODELS_JSON" ]]; then
    error_exit "Cannot find $MODELS_JSON. Run this script from the repository root."
fi

if ((${#SELECTED_MODULES[@]} == 0)); then
    error_exit "No modules specified. Use --modules followed by one or more module names."
fi

command -v docker >/dev/null 2>&1 || error_exit "Docker is not installed or not on PATH."
docker info >/dev/null 2>&1 || error_exit "Docker is not running or is inaccessible."

# Validate JSON and module names before making Docker changes.
python3 - "$MODELS_JSON" "${SELECTED_MODULES[@]}" <<'PY'
import json
import sys

path, *modules = sys.argv[1:]
try:
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    sys.exit(f"ERROR: Could not read valid JSON from {path}: {e}")

for name in modules:
    if name == "pipeline":
        continue
    if name not in config:
        sys.exit(f"ERROR: Module {name!r} is not defined in {path}.")
    if not isinstance(config[name], dict):
        sys.exit(f"ERROR: Configuration for {name!r} must be a JSON object.")
PY

# Avoid processing a module more than once.
declare -A SEEN_MODULES=()
UNIQUE_MODULES=()
for module in "${SELECTED_MODULES[@]}"; do
    if [[ -z "${SEEN_MODULES[$module]+x}" ]]; then
        UNIQUE_MODULES+=("$module")
        SEEN_MODULES["$module"]=1
    fi
done
SELECTED_MODULES=("${UNIQUE_MODULES[@]}")

# Purge first, before builds or container startup.
if [[ "$PURGE_ENABLED" == true ]]; then
    echo "Purging Docker build cache..."
    docker builder prune --all --force
fi

# Derive image and container names consistently.
image_name() {
    printf '%s/%s:local' "$IMAGE_NAMESPACE" "$1"
}

container_name() {
    printf '%s-%s' "$CONTAINER_PREFIX" "$1"
}

module_type() {
    local module="$1"

    if [[ "$module" == "pipeline" ]]; then
        printf 'pipeline'
    else
        python3 - "$MODELS_JSON" "$module" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    config = json.load(f)
print(config[sys.argv[2]].get("type", ""))
PY
    fi
}

module_config() {
    python3 - "$MODELS_JSON" "$1" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    config = json.load(f)
print(json.dumps(config[sys.argv[2]], separators=(",", ":")))
PY
}

module_llm_server() {
    python3 - "$MODELS_JSON" "$1" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    config = json.load(f)
print(config[sys.argv[2]].get("llm_server", ""))
PY
}

# Build requested images.
if [[ "$BUILD_ENABLED" == true ]]; then
    for module in "${SELECTED_MODULES[@]}"; do
        type="$(module_type "$module")"
        [[ -n "$type" ]] || error_exit "Module '$module' has no type configured."

        dockerfile="$type/Dockerfile"
        [[ -f "$dockerfile" ]] || error_exit "Dockerfile not found: $dockerfile"

        image="$(image_name "$module")"
        echo
        echo "Building module: $module"
        echo "  Type: $type"
        echo "  Image: $image"

        if [[ "$module" == "pipeline" ]]; then
            docker build \
                --tag "$image" \
                --file "$dockerfile" \
                .
        else
            config_json="$(module_config "$module")"
            assets_json="$(python3 - "$MODELS_JSON" "$module" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    config = json.load(f)
print(json.dumps(config[sys.argv[2]].get("assets", {}), separators=(",", ":")))
PY
)"
            docker build \
                --tag "$image" \
                --build-arg "MODEL_CONFIG=$config_json" \
                --build-arg "MODEL_ASSETS=$assets_json" \
                --build-arg "ENV=dev" \
                --file "$dockerfile" \
                .
        fi
    done
fi

# Run selected containers in the background.
if [[ "$RUN_ENABLED" == true ]]; then
    mkdir -p "$(dirname "$ENV_FILE")"
    touch "$ENV_FILE"
    chmod 600 "$ENV_FILE"

    for module in "${SELECTED_MODULES[@]}"; do
        image="$(image_name "$module")"
        name="$(container_name "$module")"

        if ! docker image inspect "$image" >/dev/null 2>&1; then
            error_exit "Image '$image' is missing. Build it first with --build."
        fi

        existing_id="$(docker ps -q --filter "name=^/${name}$")"
        if [[ -n "$existing_id" ]]; then
            port="$(docker port "$existing_id" "$CONTAINER_PORT/tcp" 2>/dev/null | head -n1 | awk -F: '{print $NF}')"
            if [[ -n "$port" ]]; then
                url="http://127.0.0.1:$port"
                echo "$module is already running at $url"
                continue
            fi
            error_exit "Container '$name' is running but port $CONTAINER_PORT is not published."
        fi

        # Don't silently replace stopped containers either.
        if docker container inspect "$name" >/dev/null 2>&1; then
            error_exit "Container '$name' exists but is stopped. Remove it explicitly with: docker rm '$name'"
        fi

        llm_server=""
        if [[ "$module" != "pipeline" ]]; then
            llm_server="$(module_llm_server "$module")"
        fi

        echo
        echo "Starting module: $module"

        run_args=(
            --detach
            --name "$name"
            --publish "127.0.0.1::$CONTAINER_PORT"
            --restart unless-stopped
        )

        if [[ -n "$llm_server" ]]; then
            run_args+=(--env "LLM_SERVER_URL=$llm_server")
        fi

        # Pass the full model configuration to the container for runtime use.
        if [[ "$module" != "pipeline" ]]; then
            config_json="$(module_config "$module")"
            run_args+=(--env "MODEL_CONFIG_ARG=$config_json")
        fi

        docker run "${run_args[@]}" "$image" >/dev/null

        port="$(docker port "$name" "$CONTAINER_PORT/tcp" | head -n1 | awk -F: '{print $NF}')"
        [[ -n "$port" ]] || error_exit "Could not determine the published port for '$name'."

        url="http://127.0.0.1:$port"
        env_key="CACTUSFRUIT_$(printf '%s' "$module" | tr '[:lower:]-' '[:upper:]_')_URL"

        # Replace this module's URL in the generated env file.
        tmp_file="$(mktemp)"
        grep -v "^${env_key}=" "$ENV_FILE" > "$tmp_file" || true
        printf '%s=%s\n' "$env_key" "$url" >> "$tmp_file"
        mv "$tmp_file" "$ENV_FILE"
        chmod 600 "$ENV_FILE"

        echo "Started $module"
        echo "  Container: $name"
        echo "  URL:       $url"
        echo "  Env var:   $env_key"
    done

    echo
    echo "Local service URLs are saved in $ENV_FILE"
    echo "Load them into your shell with:"
    echo "  set -a && source $ENV_FILE && set +a"
fi

echo
echo "Done."
