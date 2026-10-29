
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV ENV_FILE_PATH=/app/.env

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY generative/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY generative/src/app.py ./app.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -fsS http://127.0.0.1:8000/ping || exit 1

CMD ["sh", "-c", \
     "python -m cactusfruit.dockerscripts.configloader && \
      set -a && . /app/.env && set +a && \
      exec uvicorn app:app --host 0.0.0.0 --port 8000"]
