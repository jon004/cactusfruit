
import asyncio
import json
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from cactusfruit.sdk import LlmServerClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CactusFruit Generative Service")


def load_config():
    system_prompt = os.getenv("SYSTEM_PROMPT")
    model_name = os.getenv("MODEL_NAME")
    llm_server_url = os.getenv("LLM_SERVER_URL")

    if not system_prompt:
        raise RuntimeError("SYSTEM_PROMPT must be configured.")

    if not model_name:
        raise RuntimeError("MODEL_NAME must be configured.")

    if not llm_server_url:
        raise RuntimeError("LLM_SERVER_URL must be configured.")

    try:
        params = json.loads(os.getenv("MODEL_PARAMS", "{}"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "MODEL_PARAMS must contain valid JSON."
        ) from exc

    if not isinstance(params, dict):
        raise RuntimeError("MODEL_PARAMS must be a JSON object.")

    generation_params = {
        "n_predict": params.get("max_tokens", 256),
        "temperature": params.get("temperature", 0.1),
        "repeat_penalty": params.get("repetition_penalty", 1.1),
    }

    return system_prompt, model_name, llm_server_url, generation_params


SYSTEM_PROMPT, MODEL_NAME, LLM_SERVER_URL, GENERATION_PARAMS = load_config()

# Connect to the LLM server configured for this model in models.json.
llm_client = LlmServerClient(base_url=LLM_SERVER_URL)


class InferencePayload(BaseModel):
    prompt: str = Field(min_length=1)


@app.get("/ping")
async def ping():
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "llm_server": LLM_SERVER_URL,
    }


@app.post("/invocations")
async def invocations(payload: InferencePayload):
    # The current generate() call accepts a single role/content pair.
    # Include the configured instructions in the request text.
    full_prompt = (
        f"Instructions:\n{SYSTEM_PROMPT}\n\n"
        f"User input:\n{payload.prompt}"
    )

    try:
        response_text = await asyncio.to_thread(
            llm_client.generate,
            role="user",
            content=full_prompt,
            params=GENERATION_PARAMS,
        )

        return {"content": response_text}

    except Exception:
        logger.exception("Generation request failed")
        raise HTTPException(
            status_code=502,
            detail="The model generation request failed.",
        ) from None
