import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from sentence_transformers import CrossEncoder

app = FastAPI()

# Model Path (packaged inside Docker)
MODEL_PATH = os.getenv("RERANKER_MODEL_PATH", "/models/ms-marco-MiniLM-L6-v2")

# Global model instance for warm starts
model = None

@app.on_event("startup")
async def startup():
    global model
    try:
        model = CrossEncoder(MODEL_PATH)
    except Exception as e:
        print(f"Failed to load reranker model: {e}")

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
    
    # Format: [Query, Document] pairs
    pairs = [[request.query, doc.get("raw_text", "")] for doc in request.documents]
    scores = model.predict(pairs)
    
    # Attach scores to the documents
    for i, doc in enumerate(request.documents):
        doc['rerank_score'] = float(scores[i])
        
    # Return sorted results
    return sorted(request.documents, key=lambda x: x['rerank_score'], reverse=True)
