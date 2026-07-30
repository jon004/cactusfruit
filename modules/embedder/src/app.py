import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
LLAMA_URL = "http://127.0.0.1:8081"

class EmbeddingPayload(BaseModel):
    content: str

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/invocations")
async def invocations(payload: EmbeddingPayload):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{LLAMA_URL}/completion", json={
                "prompt": payload.content,
                "n_predict": 0,
                "embedding": True
            }, timeout=30.0)
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed-query")
async def embed_query(payload: EmbeddingPayload):
    async with httpx.AsyncClient() as client:
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
        r = await client.post(f"{LLAMA_URL}/tokenize", json={"content": payload.content})
        tokens = r.json().get("tokens", [])
        return {"token_count": len(tokens)}
