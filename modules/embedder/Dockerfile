FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY embedder/src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from src/ to /app
COPY embedder/src/app.py /app/app.py

# The handler remains app.lambda_handler
CMD ["app.lambda_handler"]
