# Stage 1: Builder
FROM ubuntu:22.04 AS builder
RUN apt-get update && apt-get install -y build-essential cmake git python3 curl

# Accept configuration and assets injected by deploy.sh
ARG MODEL_CONFIG
ARG MODEL_ASSETS

WORKDIR /build

# Build llama.cpp
RUN git clone https://github.com/ggerganov/llama.cpp && \
    cd llama.cpp && cmake -B build && cmake --build build --config Release

# Setup model directory and download the main GGUF file from URL config
RUN mkdir -p /models && \
    python3 -c "import json, subprocess; config = json.loads('$MODEL_CONFIG'); \
    subprocess.run(['curl', '-L', config['url'], '-o', '/models/model.gguf'])"

# Stage 2: Final Runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY generative/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy binary and models from builder
COPY --from=builder /build/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server
COPY --from=builder /models /models
COPY generative/src/app.py .

RUN chmod +x /usr/local/bin/llama-server

# Set default System Prompt
ENV SYSTEM_PROMPT="You are a helpful assistant."

# Healthcheck for AWS/SageMaker environments
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://127.0.0.1:8081/health || exit 1

EXPOSE 8000

# Start server and orchestration
CMD ["sh", "-c", "llama-server -m /models/model.gguf --host 127.0.0.1 --port 8081 --threads 8 --parallel 4 --cont-batching --jinja --chat-template chatml & uvicorn app:app --host 0.0.0.0 --port 8000"]
