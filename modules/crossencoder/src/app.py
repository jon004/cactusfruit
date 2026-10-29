# src/app.py

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import CrossEncoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "/models")
model: CrossEncoder | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model

    try:
        logger.info("Loading crossencoder model from %s", MODEL_PATH)
        model = CrossEncoder(MODEL_PATH)
        logger.info("Crossencoder model loaded successfully")
    except Exception:
        logger.exception("Failed to load crossencoder model")
        raise

    yield

    model = None


app = FastAPI(title="CactusFruit Crossencoder Service", lifespan=lifespan)


class RerankRequest(BaseModel):
    query: str = Field(min_length=1)
    documents: list[dict[str, Any]]


@app.get("/ping")
async def ping():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    return {"status": "ok"}


@app.post("/invocations")
async def invocations(request: RerankRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    if not request.documents:
        return []

    texts = []
    for index, document in enumerate(request.documents):
        raw_text = document.get("raw_text")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise HTTPException(
                status_code=422,
                detail=f"Document at index {index} must contain non-empty raw_text.",
            )
        texts.append(raw_text)

    pairs = [[request.query, text] for text in texts]

    try:
        scores = await asyncio.to_thread(model.predict, pairs)

        results = []
        for document, score in zip(request.documents, scores):
            result = document.copy()
            result["rerank_score"] = float(score)
            results.append(result)

        return sorted(
            results,
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Reranking request failed")
        raise HTTPException(
            status_code=500,
            detail="The reranking request failed.",
        ) from None
