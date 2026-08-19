FROM ubuntu:22.04 AS builder
ARG MODEL_CONFIG
ARG MODEL_ASSETS
ARG ENVIRONMENT="local"

WORKDIR /build

RUN apt-get update && apt-get install -y build-essential cmake git python3 curl

# Only build open-source llama-server if ENVIRONMENT is not local or dev
RUN if [ "$ENVIRONMENT" != "local" ] && [ "$ENVIRONMENT" != "dev" ]; then \
        git clone https://github.com/ggerganov/llama.cpp && \
        cd llama.cpp && cmake -B build && cmake --build build --config Release; \
    else \
        echo "Skipping open-source llama.cpp build because ENVIRONMENT is set to '$ENVIRONMENT'."; \
    fi

RUN mkdir -p /models && \
    python3 -c "import json, subprocess; config = json.loads('$MODEL_CONFIG'); \
    subprocess.run(['curl', '-L', config['url'], '-o', '/models/model.gguf'])"

FROM python:3.12-slim
ARG ENVIRONMENT="local"
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY embedder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Conditionally copy the open-source llama-server and models only if not local/dev
RUN --mount=type=bind,from=builder,source=/build,target=/tmp/builder \
    if [ "$ENVIRONMENT" != "local" ] && [ "$ENVIRONMENT" != "dev" ]; then \
        cp /tmp/builder/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server && \
        chmod +x /usr/local/bin/llama-server && \
        cp -r /tmp/builder/models /models; \
    else \
        echo "Skipping llama-server and model copy for local/dev environment."; \
    fi

COPY embedder/src/app.py .
COPY ../shared-libs/embedder.py .

ARG MODEL_CONFIG

RUN python3 -c "
import json
config = json.loads('''$MODEL_CONFIG''')
params = config.get('params', {})
with open('/app/.env', 'w') as f:
    f.write(f'THREADS={params.get(\"threads\", 4)}\n')
"

ENV THREADS=""
ENV ENVIRONMENT=${ENVIRONMENT}

HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://127.0.0.1:8081/health || exit 1

EXPOSE 8000

CMD ["sh", "-c", "set -a && [ -f /app/.env ] && . /app/.env && set +a && if [ \"$ENVIRONMENT\" != \"local\" ] && [ \"$ENVIRONMENT\" != \"dev\" ]; then llama-server -m /models/model.gguf --host 127.0.0.1 --port 8081 --threads ${THREADS:-4} --embedding & fi uvicorn app:app --host 0.0.0.0 --port 8000"]
