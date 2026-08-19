# appEmbedder.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from Embedder import Embedder

app = FastAPI()
embedder = Embedder()

class EmbeddingPayload(BaseModel):
    content: str

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/invocations")
async def invocations(payload: EmbeddingPayload):
    try:
        vector = embedder.embed_document(payload.content)
        return {"embedding": vector}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed-query")
async def embed_query(payload: EmbeddingPayload):
    try:
        vector = embedder.embed_query(payload.content)
        return {"embedding": vector}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed-doc")
async def embed_doc(payload: EmbeddingPayload):
    try:
        vector = embedder.embed_document(payload.content)
        return {"embedding": vector}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/token/count")
async def token_count(payload: EmbeddingPayload):
    try:
        count = embedder.token_count(payload.content)
        return {"token_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
