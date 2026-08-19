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

COPY generative/requirements.txt .
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

COPY generative/src/app.py .

# Copy both potential shared library variants into temporary locations so we can select conditionally
COPY shared-libs/local/generator.py /tmp/generator_local.py
COPY shared-libs/deployed/generator.py /tmp/generator_deployed.py

# Conditionally choose the correct shared library based on the environment
RUN if [ "$ENVIRONMENT" = "local" ] || [ "$ENVIRONMENT" = "dev" ]; then \
        cp /tmp/generator_local.py ./Generator.py; \
        echo "Using local shared library"; \
    else \
        cp /tmp/generator_deployed.py ./Generator.py; \
        echo "Using deployed shared library"; \
    fi && \
    rm -f /tmp/generator_local.py /tmp/generator_deployed.py

ARG MODEL_CONFIG
ENV MODEL_CONFIG_ARG=$MODEL_CONFIG

COPY shared-libs/configloader.py /tmp/configloader.py
RUN python3 /tmp/configloader.py && rm -f /tmp/configloader.py

ENV SYSTEM_PROMPT=""
ENV MODEL_NAME=""
ENV MODEL_PARAMS=""
ENV THREADS=""
ENV PARALLEL=""
ENV ENVIRONMENT=${ENVIRONMENT}

HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://127.0.0.1:8081/health || exit 1

EXPOSE 8000

CMD ["sh", "-c", "set -a && [ -f /app/.env ] && . /app/.env && set +a && if [ \"$ENVIRONMENT\" != \"local\" ] && [ \"$ENVIRONMENT\" != \"dev\" ]; then llama-server -m /models/model.gguf --host 127.0.0.1 --port 8081 --threads ${THREADS:-8} --parallel ${PARALLEL:-4} --cont-batching --jinja --chat-template chatml & fi uvicorn app:app --host 0.0.0.0 --port 8000"]
