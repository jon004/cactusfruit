FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY crossencoder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG MODEL_ASSETS

RUN mkdir -p /models && \
    python3 -c "import json, subprocess; assets = json.loads('$MODEL_ASSETS'); \
    [subprocess.run(['curl', '-L', url, '-o', f'/models/{name}']) for name, url in assets.items()]"

COPY crossencoder/app.py /app/app.py

# Generic environment variable instead of RERANKER_MODEL_PATH
ENV MODEL_PATH="/models"

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
