import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from mangum import Mangum

app = FastAPI()
LLAMA_URL = "http://127.0.0.1:8081"

class EmbeddingPayload(BaseModel):
    content: str
    model_path: str

@app.post("/embed-query")
async def embed_query(payload: EmbeddingPayload):
    async with httpx.AsyncClient() as client:
        # Standard llama-server uses /completion for embedding via n_predict: 0
        r = await client.post(f"{LLAMA_URL}/completion", json={
            "prompt": f"search_query: {payload.content}",
            "n_predict": 0,
            "embedding": True
        })
        return r.json()

@app.post("/embed-doc")
async def embed_doc(payload: EmbeddingPayload):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{LLAMA_URL}/completion", json={
            "prompt": f"search_document: {payload.content}",
            "n_predict": 0,
            "embedding": True
        })
        return r.json()

@app.post("/token/count")
async def token_count(payload: EmbeddingPayload):
    async with httpx.AsyncClient() as client:
        # Standard llama-server /tokenize endpoint
        r = await client.post(f"{LLAMA_URL}/tokenize", json={"content": payload.content})
        tokens = r.json().get("tokens", [])
        return {"token_count": len(tokens)}

handler = Mangum(app)
