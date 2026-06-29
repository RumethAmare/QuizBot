import hashlib
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import google.generativeai as genai


load_dotenv()

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 20
DEFAULT_MODEL_NAME = "gemini-2.5-flash"
DEFAULT_CORS_ORIGINS = [
    "null",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://quizbot-hi5v.onrender.com",
    "https://quizbot-frontend-hi5v.onrender.com",
]


class QuizRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    num_questions: int = Field(..., ge=1, le=MAX_QUESTIONS)


app = FastAPI()


def get_allowed_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS")
    if not configured_origins:
        return DEFAULT_CORS_ORIGINS

    return [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL_NAME", DEFAULT_MODEL_NAME)


def get_api_key_fingerprint() -> str | None:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def get_provider_error_detail(exc: Exception) -> dict[str, str]:
    return {
        "type": exc.__class__.__name__,
        "message": str(exc)[:500],
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def get_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured.")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(get_model_name())


def build_quiz_prompt(topic: str, num_questions: int) -> str:
    return f"""
Create a {num_questions}-question multiple choice quiz on the topic '{topic}'.
For each question, provide:
- The question
- 4 options labeled A, B, C, D
- The correct answer at the end in this format: 'Answer: X'
Format the output cleanly and clearly.
"""


@app.get("/")
async def read_root():
    return {"message": "AI Quiz Generator is running."}


@app.get("/status")
async def read_status():
    return {
        "message": "AI Quiz Generator is running.",
        "model": get_model_name(),
        "google_api_key_configured": bool(os.getenv("GOOGLE_API_KEY")),
        "google_api_key_fingerprint": get_api_key_fingerprint(),
    }


@app.get("/debug/gemini")
async def debug_gemini():
    try:
        model = get_model()
        response = model.generate_content("Reply with exactly: ok")
    except RuntimeError as exc:
        return {
            "ok": False,
            "model": get_model_name(),
            "error": {"type": "ConfigurationError", "message": str(exc)},
        }
    except Exception as exc:
        logger.exception("Gemini debug probe failed.")
        return {
            "ok": False,
            "model": get_model_name(),
            "error": get_provider_error_detail(exc),
        }

    return {
        "ok": True,
        "model": get_model_name(),
        "response_preview": getattr(response, "text", "").strip()[:100],
    }


@app.post("/generate_quiz")
async def generate_quiz(req: QuizRequest):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic must not be empty.")

    try:
        model = get_model()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    prompt = build_quiz_prompt(topic, req.num_questions)

    try:
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.exception("Gemini quiz generation failed.")
        logger.info("Gemini error detail: %s", get_provider_error_detail(exc))
        raise HTTPException(
            status_code=502,
            detail="Quiz generation failed. Please try again later.",
        ) from exc

    quiz_text = getattr(response, "text", "").strip()
    if not quiz_text:
        raise HTTPException(
            status_code=502,
            detail="Quiz generation returned an empty response.",
        )

    return {"quiz": quiz_text}
