# src/app.py

import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from cactusfruit.sdk import LlmServerClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_SERVER_URL = os.getenv("LLM_SERVER_URL")

if not LLM_SERVER_URL:
    raise RuntimeError("LLM_SERVER_URL must be configured.")

llm_client = LlmServerClient(base_url=LLM_SERVER_URL)

app = FastAPI(title="CactusFruit Embedder Service")


class EmbeddingPayload(BaseModel):
    content: str = Field(min_length=1)


@app.get("/ping")
async def ping():
    return {"status": "ok"}


async def run_sdk_call(method, content: str, result_key: str):
    try:
        result = await asyncio.to_thread(method, content)
        return {result_key: result}
    except Exception:
        logger.exception("Embedder operation failed: %s", result_key)
        raise HTTPException(
            status_code=500,
            detail="The embedding operation failed.",
        ) from None


@app.post("/invocations")
async def invocations(payload: EmbeddingPayload):
    return await run_sdk_call(
        llm_client.embed_document,
        payload.content,
        "embedding",
    )


@app.post("/embed-query")
async def embed_query(payload: EmbeddingPayload):
    return await run_sdk_call(
        llm_client.embed_query,
        payload.content,
        "embedding",
    )


@app.post("/embed-doc")
async def embed_doc(payload: EmbeddingPayload):
    return await run_sdk_call(
        llm_client.embed_document,
        payload.content,
        "embedding",
    )


@app.post("/token/count")
async def token_count(payload: EmbeddingPayload):
    return await run_sdk_call(
        llm_client.token_count,
        payload.content,
        "token_count",
    )
