import logging
import os
from functools import lru_cache

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache
def get_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured.")

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL_NAME", DEFAULT_MODEL_NAME)
    return genai.GenerativeModel(model_name)


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
