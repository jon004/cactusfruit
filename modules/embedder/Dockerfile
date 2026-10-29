# syntax=docker/dockerfile:1.4
FROM ubuntu:22.04 AS builder

ARG MODEL_CONFIG
ARG ENV=dev

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential cmake git python3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build llama.cpp only for profiles using an embedded model server.
RUN if [ "$ENV" != "dev" ] && [ "$ENV" != "local" ]; then \
        git clone --depth 1 https://github.com/ggml-org/llama.cpp \
        && cmake -S llama.cpp -B llama.cpp/build \
            -DCMAKE_BUILD_TYPE=Release \
        && cmake --build llama.cpp/build --config Release -j2; \
    else \
        echo "Skipping llama.cpp build for $ENV"; \
    fi

# Download the configured GGUF model for embedded-server profiles.
RUN if [ "$ENV" != "dev" ] && [ "$ENV" != "local" ]; then \
        MODEL_CONFIG="$MODEL_CONFIG" python3 -c \
        'import json, os, urllib.request; c=json.loads(os.environ["MODEL_CONFIG"]); urllib.request.urlretrieve(c["url"], "/tmp/model.gguf")' \
        && mkdir -p /models \
        && mv /tmp/model.gguf /models/model.gguf; \
    else \
        echo "Skipping model download for $ENV"; \
    fi


FROM python:3.12-slim

ARG ENV=dev

ENV ENVIRONMENT=${ENV}
ENV ENV_FILE_PATH=/app/.env
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY embedder/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY embedder/src/app.py ./app.py

# Copy llama-server and the downloaded model only when required.
RUN --mount=type=bind,from=builder,source=/build,target=/tmp/builder \
    if [ "$ENV" != "dev" ] && [ "$ENV" != "local" ]; then \
        install -m 0755 \
            /tmp/builder/llama.cpp/build/bin/llama-server \
            /usr/local/bin/llama-server \
        && mkdir -p /models \
        && cp /tmp/builder/models/model.gguf /models/model.gguf; \
    else \
        echo "No embedded model server for $ENV"; \
    fi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -fsS http://127.0.0.1:8000/ping || exit 1

CMD ["sh", "-c", "\
    if [ -n \"${MODEL_CONFIG:-}\" ]; then \
        export MODEL_CONFIG_ARG=\"$MODEL_CONFIG\"; \
    fi; \
    python -m cactusfruit.dockerscripts.configloader \
    && set -a \
    && . /app/.env \
    && set +a \
    && if [ \"$ENVIRONMENT\" != \"dev\" ] && [ \"$ENVIRONMENT\" != \"local\" ]; then \
        export LLM_SERVER_URL=http://127.0.0.1:8081; \
        llama-server \
            -m /models/model.gguf \
            --host 127.0.0.1 \
            --port 8081 \
            --threads \"${THREADS:-4}\" \
            --embedding & \
        server_pid=$!; \
        ready=0; \
        for attempt in $(seq 1 60); do \
            if curl -fsS http://127.0.0.1:8081/health >/dev/null; then \
                ready=1; \
                break; \
            fi; \
            if ! kill -0 \"$server_pid\" 2>/dev/null; then \
                echo 'llama-server exited during startup'; \
                exit 1; \
            fi; \
            sleep 1; \
        done; \
        if [ \"$ready\" -ne 1 ]; then \
            echo 'llama-server did not become ready'; \
            exit 1; \
        fi; \
    fi; \
    exec uvicorn app:app --host 0.0.0.0 --port 8000 \
"]
