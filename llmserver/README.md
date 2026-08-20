# LLM Server

A high-performance LLM inference server with CUDA and Metal acceleration support.

## Building

### Quick Start

Choose one of the following methods:

#### Method 1: Build Only (`build.sh`)
Use this if you already have dependencies installed and just want to compile the project.

```bash
./build.sh
```

**Flags:**
- `--force` - Force rebuild even if already built

**What it does:**
- Detects system resources (CPU cores, RAM)
- Automatically enables CUDA or Metal acceleration based on available hardware
- Builds the project in parallel using optimal job count
- Creates executable at `build/llm-server`

#### Method 2: Full Install (`install.sh`)
Use this for a complete setup including dependencies and model downloads.

```bash
./install.sh
```

**Flags:**
- `--force` - Force re-download models even if they exist
- `--skip-model` - Skip model downloads (build only)

**What it does:**
- Initializes git submodules
- Installs dependencies (macOS: brew, cmake, curl, brotli)
- Detects and configures acceleration (CUDA/Metal)
- Downloads pre-trained models:
  - 7B chat model (~4.1GB)
  - Small 0.5B model (~470MB) 
  - Embedding model (~80MB)
- Configures CMake build

## Acceleration Support

The build system automatically detects and enables hardware acceleration:

- **CUDA**: Enabled if `nvcc` compiler is found
- **Metal**: Enabled on macOS (Apple Silicon and Intel)

## System Requirements

- **Linux/macOS**: Build scripts tested on Linux and macOS
- **CMake**: Required for building
- **Memory**: 4GB+ RAM recommended for parallel builds
- **Storage**: ~5GB for models (if using install.sh)

## Output

After building, the executable will be located at:
```
build/llm-server
```

## Example Usage

```bash
# Start the server with default model
./build/llm-server

# Start with specific model
./build/llm-server --model models/7b-chatml-model.gguf
```
