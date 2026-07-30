#!/bin/bash
# deploy.sh - Unified deployment utility
set -euo pipefail

error_exit() { echo "ERROR: $1" >&2; exit 1; }

MODELS_JSON="models.json"
DEPLOY_JSON="deploy-to.json"
PIPELINE_ECR_REPO="pipeline"

# Help message
show_help() {
    local available_models="None (models.json not found)"
    if [[ -f "$MODELS_JSON" ]]; then
        available_models=$(python3 -c "import json; print(', '.join(json.load(open('$MODELS_JSON')).keys()))")
    fi

    cat << EOF
Usage: ./deploy.sh [OPTIONS]

Unified deployment utility for building and pushing LocalDoby module containers.

Options:
  --modules [names...]  Specify one or more modules to process (e.g., --modules pipeline embedder reranker)
  --all-modules         Automatically select all models defined in models.json plus pipeline
  --profile [name]      Select deployment profile from deploy-to.json (default: "dev")
  --build               Build Docker images for specified modules
  --push                Push built images to ECR repositories (disabled if profile is "dev" or not found in deploy-to.json)
  --purge-docker        Clean up Docker build cache (runs before processing)
  -h, --help            Show this help message and exit

Available Models in $MODELS_JSON:
  $available_models
  + pipeline (hardcoded service module)

Workflow:
  1. Validates module existence and directory presence.
  2. Builds container images (passing MODELS_CONFIG and MODEL_ASSETS build args/environment variables).
  3. Pushes images to AWS ECR across configured regions with 'latest' and timestamp tags (skipped if profile is "dev").

Example:
  ./deploy.sh --build --modules pipeline embedder --purge-docker
EOF
    exit 0
}

# Default state (changed default profile to "dev" so push won't break if flag is omitted)
BUILD_ENABLED=false
PUSH_ENABLED=false
PURGE_ENABLED=false
PROFILE=""
SELECTED_MODULES=()

# Parse Args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --modules) 
            shift
            while [[ "$#" -gt 0 && ! "$1" =~ ^-- ]]; do 
                SELECTED_MODULES+=("$1")
                shift
            done
            continue ;;
        --all-modules)
            ALL_MODULES_ENABLED=true
            shift ;;
        --profile) PROFILE="$2"; shift ;;
        --build) BUILD_ENABLED=true ;;
        --push) PUSH_ENABLED=true ;;
        --purge-docker) PURGE_ENABLED=true ;;
        -h|--help) show_help ;;
        *) 
            echo "Unknown argument: $1"
            show_help ;;
    esac
    shift
done

# If profile flag is not set, default to "dev"
if [[ -z "$PROFILE" ]]; then
    PROFILE="dev"
fi

# Pre-flight checks
command -v docker >/dev/null 2>&1 || error_exit "Docker is not installed."
command -v aws >/dev/null 2>&1 || error_exit "AWS CLI is not installed."

# Auto-generate deploy-to.json if it doesn't exist
if [[ ! -f "$DEPLOY_JSON" ]]; then
    echo "Configuration file '$DEPLOY_JSON' not found."
    read -p "Enter your AWS IAM Role ARN (e.g., arn:aws:iam::ACCOUNT_ID:role/role-name): " INPUT_ARN
    
    if [[ -z "$INPUT_ARN" ]]; then
        error_exit "IAM Role ARN cannot be empty."
    fi

    echo "Generating $DEPLOY_JSON..."
    cat << EOF > "$DEPLOY_JSON"
{
    "default": {
        "iam_role_arn": "$INPUT_ARN",
        "aws_regions": [
            "us-east-1"
        ]
    }
}
EOF
    echo "Successfully created $DEPLOY_JSON."
fi

[[ -f "$DEPLOY_JSON" ]] || error_exit "$DEPLOY_JSON not found."

# If --all-modules is specified, populate SELECTED_MODULES from models.json keys plus pipeline
if [[ "${ALL_MODULES_ENABLED:-false}" == true ]]; then
    [[ -f "$MODELS_JSON" ]] || error_exit "$MODELS_JSON not found."
    read -ra SELECTED_MODULES <<< "$(python3 -c "import json; print(' '.join(list(json.load(open('$MODELS_JSON')).keys()) + ['pipeline']))")"
fi

if [[ ${#SELECTED_MODULES[@]} -eq 0 ]]; then
    error_exit "No modules specified. Use --modules or --all-modules."
fi

# Profile validation and safe handling for "dev" profile
REGIONS=""
if [[ "$PROFILE" == "dev" ]]; then
    echo "Profile is set to 'dev'. Pushing to ECR is disabled for this profile."
    PUSH_ENABLED=false
else
    if ! python3 -c "import json; exit(0 if '$PROFILE' in json.load(open('$DEPLOY_JSON')) else 1)"; then
        error_exit "Profile '$PROFILE' not found in $DEPLOY_JSON."
    fi
    REGIONS=$(python3 -c "import json; print(' '.join(json.load(open('$DEPLOY_JSON'))['$PROFILE']['aws_regions']))")
fi

if [[ "$PURGE_ENABLED" == true ]]; then
    echo "Purging build cache..."
    docker builder prune -a -f || error_exit "Failed to purge docker cache."
fi

# Generate timestamp tag format YYYY.MM.DD.HH.MM.SS (valid for Docker tags)
IMAGE_TAG_TIMESTAMP=$(date +"%Y.%m.%d.%H.%M.%S")
BASE_IMAGE_TAG="latest"

for mod_name in "${SELECTED_MODULES[@]}"; do
    echo "Processing: $mod_name"
    
    # 1. Validate configuration and directory (now under modules/)
    if [[ "$mod_name" == "pipeline" ]]; then
        [[ -d "modules/pipeline" ]] || error_exit "Directory 'modules/pipeline' does not exist."
        MODEL_TYPE="pipeline"
        ECR_REPO="$PIPELINE_ECR_REPO"
    else
        [[ -f "$MODELS_JSON" ]] || error_exit "$MODELS_JSON not found."
        MODEL_TYPE=$(python3 -c "import json; print(json.load(open('$MODELS_JSON')).get('$mod_name', {}).get('type', ''))")
        [[ -z "$MODEL_TYPE" ]] && error_exit "Model '$mod_name' not defined in $MODELS_JSON."
        [[ -d "modules/$MODEL_TYPE" ]] || error_exit "Directory 'modules/$MODEL_TYPE' does not exist."
        ECR_REPO="$mod_name"
    fi
    
    # 2. Extract metadata
    IMAGE_TAG="localdoby:$mod_name"

    # 3. Build only if enabled (pointing to modules/ path)
    if [[ "$BUILD_ENABLED" == true ]]; then
        echo "Building $mod_name..."
        
        if [[ "$mod_name" == "pipeline" ]]; then
            docker build \
                -t "${IMAGE_TAG}:${BASE_IMAGE_TAG}" \
                -t "${IMAGE_TAG}:${IMAGE_TAG_TIMESTAMP}" \
                --build-arg ENV="$PROFILE" \
                -f "modules/pipeline/Dockerfile" . || error_exit "Build failed for $mod_name."
        else
            MODEL_CONFIG_JSON=$(python3 -c "import json; print(json.dumps(json.load(open('$MODELS_JSON'))['$mod_name']))")
            ASSETS_JSON=$(python3 -c "import json; print(json.dumps(json.load(open('$MODELS_JSON'))['$mod_name'].get('assets', {})))")
            
            docker build \
                -t "${IMAGE_TAG}:${BASE_IMAGE_TAG}" \
                -t "${IMAGE_TAG}:${IMAGE_TAG_TIMESTAMP}" \
                --build-arg MODEL_CONFIG="$MODEL_CONFIG_JSON" \
                --build-arg MODEL_ASSETS="$ASSETS_JSON" \
                --build-arg MODELS_JSON="$MODEL_CONFIG_JSON" \
                --build-arg ENV="$PROFILE" \
                -f "modules/$MODEL_TYPE/Dockerfile" . || error_exit "Build failed for $mod_name."
        fi
    fi

    # 4. Push only if enabled
    if [[ "$PUSH_ENABLED" == true ]]; then
        for region in $REGIONS; do
            AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text || error_exit "Failed to get AWS account ID.")
            REGISTRY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${region}.amazonaws.com/${ECR_REPO}"

            echo "Ensuring ECR repository exists: $ECR_REPO in $region..."
            aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$region" >/dev/null 2>&1 || \
                aws ecr create-repository --repository-name "$ECR_REPO" --region "$region" >/dev/null || \
                error_exit "Failed to create or find ECR repository '$ECR_REPO'."

            echo "Authenticating with ECR ($region)..."
            aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$REGISTRY_URI"

            echo "Pushing ${mod_name} with tags ${BASE_IMAGE_TAG} and ${IMAGE_TAG_TIMESTAMP} to ${REGISTRY_URI}..."
            
            docker tag "${IMAGE_TAG}:${BASE_IMAGE_TAG}" "${REGISTRY_URI}:${BASE_IMAGE_TAG}"
            docker tag "${IMAGE_TAG}:${IMAGE_TAG_TIMESTAMP}" "${REGISTRY_URI}:${IMAGE_TAG_TIMESTAMP}"
            
            docker push "${REGISTRY_URI}:${BASE_IMAGE_TAG}"
            docker push "${REGISTRY_URI}:${IMAGE_TAG_TIMESTAMP}"
        done
    fi
done
