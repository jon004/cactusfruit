#!/usr/bin/env bash
set -e

# Display help message
show_help() {
    echo "Usage: ./build.sh [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help      Display this help message and exit"
    echo "  --cuda          Enable CUDA support during build"
    echo "  --debug         Build in Debug mode"
    echo ""
    echo "Description:"
    echo "  Initializes submodules, checks dependencies, and compiles the custom LLM server."
}

# Parse command-line arguments
BUILD_TYPE="Release"
USE_CUDA=OFF

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --cuda)
            USE_CUDA=ON
            shift
            ;;
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        *)
            echo "Unknown parameter passed: $1"
            echo "Run './build.sh --help' for more information."
            exit 1
            ;;
    esac
done

echo "=========================================="
echo " Initializing Git Submodules"
echo "=========================================="

# Find the root of the git repository (handles being run from inside subdirectories)
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

if [ -z "$GIT_ROOT" ]; then
    echo "Error: Not inside a git repository."
    exit 1
fi

# Update submodules from the repository root
git -C "$GIT_ROOT" submodule update --init --recursive

# Determine Metal acceleration for macOS
USE_METAL="OFF"
if [[ "$(uname)" == "Darwin" ]]; then
    USE_METAL="ON"
    echo "macOS detected. Enabling Metal acceleration."
fi

echo "=========================================="
echo " Building llm-server"
echo " Build Type : $BUILD_TYPE"
echo " CUDA       : $USE_CUDA"
echo " Metal      : $USE_METAL"
echo "=========================================="

# Create build directory
mkdir -p build
cd build

# Run CMake configuration with appropriate backend flags
cmake .. -DCMAKE_BUILD_TYPE="$BUILD_TYPE" -DUSE_CUDA="$USE_CUDA" -DGGML_CUDA="$USE_CUDA" -DGGML_METAL="$USE_METAL"

# Build the binary using available CPU cores
cmake --build . --config "$BUILD_TYPE" -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

echo "=========================================="
echo " Build complete!"
echo " Binary located at: build/llm-server"
echo "=========================================="
