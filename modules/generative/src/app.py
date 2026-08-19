# appGenerative.py
import asyncio
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from Generator import Generator

app = FastAPI()

generator = Generator()

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

# Map model parameters for generation requests
GENERATION_PARAMS = {
    "n_predict": PARAMS.get("max_tokens", 256),
    "temperature": PARAMS.get("temperature", 0.1),
    "repeat_penalty": PARAMS.get("repetition_penalty", 1.1)
}

queue = asyncio.Queue()
BATCH_WINDOW = 0.05
MAX_BATCH_SIZE = 4

class InferencePayload(BaseModel):
    prompt: str

@app.on_event("startup")
async def startup():
    asyncio.create_task(batch_worker())

@app.get("/ping")
async def ping():
    return {"status": "ok", "model": MODEL_NAME}

@app.post("/invocations")
async def invocations(payload: InferencePayload):
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    await queue.put((payload.prompt, future))
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
    await asyncio.gather(
        *[call_generator(prompt, f) for prompt, f in batch],
        return_exceptions=True
    )

async def call_generator(prompt, future):
    try:
        response_text = generator.generate(role="user", content=prompt, params=GENERATION_PARAMS)
        future.set_result({"content": response_text})
    except Exception as e:
        future.set_exception(e)
