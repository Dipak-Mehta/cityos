import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google import genai

app = FastAPI(title="CITYOS AI", version="0.1.0")

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")


class AnalyzeRequest(BaseModel):
    intersection_id: str
    telemetry: dict[str, Any]
    risk: str = Field(default="UNKNOWN")


SYSTEM_PROMPT = """You are CITYOS, an AI infrastructure operations assistant.
Analyze traffic-intersection telemetry. Identify abnormal signals, explain likely causes,
state the operational risk, and recommend safe maintenance/monitoring actions.
Do not claim certainty. Do not directly control physical infrastructure.
Return concise JSON-like sections: Summary, Anomalies, Likely Cause, Risk, Recommended Actions.
"""


def build_prompt(request: AnalyzeRequest) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Intersection: {request.intersection_id}\n"
        f"Risk from CITYOS rules: {request.risk}\n"
        f"Telemetry: {request.telemetry}\n"
    )


async def ask_ollama(prompt: str) -> str:
    if not OLLAMA_MODEL:
        raise HTTPException(status_code=503, detail="OLLAMA_MODEL is not configured")
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")


async def ask_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text or ""


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "cityos-ai",
        "provider": AI_PROVIDER,
        "model": GEMINI_MODEL if AI_PROVIDER == "gemini" else OLLAMA_MODEL,
    }


@app.post("/api/v1/analyze")
async def analyze(request: AnalyzeRequest):
    prompt = build_prompt(request)
    try:
        if AI_PROVIDER == "gemini":
            answer = await ask_gemini(prompt)
        elif AI_PROVIDER == "ollama":
            answer = await ask_ollama(prompt)
        else:
            raise HTTPException(status_code=400, detail="AI_PROVIDER must be 'ollama' or 'gemini'")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama request failed: {exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}") from exc

    return {
        "provider": AI_PROVIDER,
        "model": GEMINI_MODEL if AI_PROVIDER == "gemini" else OLLAMA_MODEL,
        "intersection_id": request.intersection_id,
        "analysis": answer,
    }
