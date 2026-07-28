import asyncio
import httpx
import os
import json
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

LLAMA_URL = "http://127.0.0.1:8081/completion"

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_PARAMS_STR = os.getenv("MODEL_PARAMS", "{}")

if not SYSTEM_PROMPT or not MODEL_NAME:
    raise RuntimeError("CRITICAL: SYSTEM_PROMPT or MODEL_NAME environment variable is not set.")

# Parse the params injected by deploy.sh
try:
    PARAMS = json.loads(MODEL_PARAMS_STR)
except json.JSONDecodeError:
    PARAMS = {}

# Map models.json keys to llama.cpp's required keys
LLAMA_KWARGS = {
    "n_predict": PARAMS.get("max_tokens", 256),
    "temperature": PARAMS.get("temperature", 0.1),
    "repeat_penalty": PARAMS.get("repetition_penalty", 1.1)
}

queue = asyncio.Queue()
BATCH_WINDOW = 0.05
MAX_BATCH_SIZE = 4

# The client now ONLY sends the prompt
class InferencePayload(BaseModel):
    prompt: str

@app.on_event("startup")
async def startup():
    asyncio.create_task(batch_worker())

@app.get("/ping")
async def ping():
    # Attempt to hit llama.cpp's internal health check endpoint
    # (llama-server natively hosts a health check on /health)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("http://127.0.0.1:8081/health", timeout=1.0)
            if r.status_code == 200:
                return {"status": "ok", "model": MODEL_NAME}
        except Exception:
            pass
            
    # If llama-server is down or still loading the model, return a 503.
    # SageMaker will see this, understand the container is still booting, and retry.
    from fastapi import HTTPException
    raise HTTPException(status_code=503, detail="Model server is still loading")

@app.post("/invocations")
async def invocations(payload: InferencePayload):
    full_prompt = (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{payload.prompt}<|im_end|>\n"
        f"<|im_start|>assistant"
    )
    
    # Merge the prompt with the immutable model parameters
    llama_payload = {"prompt": full_prompt, **LLAMA_KWARGS}
    
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    await queue.put((llama_payload, future))
    return await future

async def batch_worker():
    while True:
        batch = []
        try:
            item = await asyncio.wait_for(queue.get(), timeout=BATCH_WINDOW)
            batch.append(item)
        except asyncio.TimeoutError:
            continue
        while len(batch) < MAX_BATCH_SIZE and not queue.empty():
            batch.append(queue.get_nowait())
        await process_batch(batch)

async def process_batch(batch):
    async with httpx.AsyncClient(timeout=120.0) as client:
        await asyncio.gather(
            *[call_llama(params, client, f) for params, f in batch],
            return_exceptions=True
        )

async def call_llama(params, client, future):
    try:
        r = await client.post(LLAMA_URL, json=params)
        r.raise_for_status()
        future.set_result(r.json())
    except Exception as e:
        future.set_exception(e)
