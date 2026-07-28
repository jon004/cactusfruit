FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies first for better caching
COPY crossencoder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Accept the dictionary of URLs as a string
ARG MODEL_ASSETS

# Download dynamically based on the provided JSON
RUN mkdir -p /models/reranker && \
    python3 -c "import json, subprocess; assets = json.loads('$MODEL_ASSETS'); \
    [subprocess.run(['curl', '-L', url, '-o', f'/models/reranker/{name}']) for name, url in assets.items()]"

COPY crossencoder/app.py /app/app.py
ENV RERANKER_MODEL_PATH="/models/reranker"

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
