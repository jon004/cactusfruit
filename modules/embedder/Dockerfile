FROM ubuntu:22.04 AS builder
ARG MODEL_CONFIG
ARG MODEL_ASSETS

WORKDIR /build

RUN apt-get update && apt-get install -y build-essential cmake git python3 curl

RUN git clone https://github.com/ggerganov/llama.cpp && \
    cd llama.cpp && cmake -B build && cmake --build build --config Release

RUN mkdir -p /models && \
    python3 -c "import json, subprocess; config = json.loads('$MODEL_CONFIG'); \
    subprocess.run(['curl', '-L', config['url'], '-o', '/models/model.gguf'])"

FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY embedder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /build/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server
COPY --from=builder /models /models
COPY embedder/src/app.py .

RUN chmod +x /usr/local/bin/llama-server

ARG MODEL_CONFIG

RUN python3 -c "
import json
config = json.loads('''$MODEL_CONFIG''')
params = config.get('params', {})
with open('/app/.env', 'w') as f:
    f.write(f'THREADS={params.get(\"threads\", 4)}\n')
"

ENV THREADS=""

HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://127.0.0.1:8081/health || exit 1

EXPOSE 8000

CMD ["sh", "-c", "set -a && [ -f /app/.env ] && . /app/.env && set +a && llama-server -m /models/model.gguf --host 127.0.0.1 --port 8081 --threads ${THREADS:-4} --embedding & uvicorn app:app --host 0.0.0.0 --port 8000"]
