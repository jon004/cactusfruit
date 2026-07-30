import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from sentence_transformers import CrossEncoder

app = FastAPI()

# Generic model path read from environment
MODEL_PATH = os.getenv("MODEL_PATH", "/models")

model = None

@app.on_event("startup")
async def startup():
    global model
    try:
        model = CrossEncoder(MODEL_PATH)
    except Exception as e:
        print(f"Failed to load model: {e}")

class RerankRequest(BaseModel):
    query: str
    documents: List[Dict]

@app.get("/ping")
async def ping():
    if model is None:
        raise HTTPException(status_code=503, detail="Model loading")
    return {"status": "ok"}

@app.post("/invocations")
async def invocations(request: RerankRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    pairs = [[request.query, doc.get("raw_text", "")] for doc in request.documents]
    scores = model.predict(pairs)
    
    for i, doc in enumerate(request.documents):
        doc['rerank_score'] = float(scores[i])

    return sorted(request.documents, key=lambda x: x['rerank_score'], reverse=True)
