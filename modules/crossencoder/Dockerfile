
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/models

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY crossencoder/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ARG MODEL_ASSETS

RUN mkdir -p /models \
    && MODEL_ASSETS_JSON="$MODEL_ASSETS" python - <<'PY'
import json
import os
import subprocess

assets = json.loads(os.environ.get("MODEL_ASSETS_JSON") or "{}")

if not assets:
    raise SystemExit("MODEL_ASSETS is empty; cannot build the crossencoder image.")

for filename, url in assets.items():
    if not filename or "/" in filename or filename in {".", ".."}:
        raise SystemExit(f"Invalid model asset filename: {filename!r}")

    destination = f"/models/{filename}"
    print(f"Downloading {filename} from {url}")

    subprocess.run(
        [
            "curl",
            "--fail",
            "--location",
            "--retry", "3",
            "--silent",
            "--show-error",
            url,
            "--output", destination,
        ],
        check=True,
    )
PY

COPY crossencoder/src/app.py ./app.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD curl -fsS http://127.0.0.1:8000/ping || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
