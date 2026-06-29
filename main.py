import hashlib
import json
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
OPTION_KEYS = ["A", "B", "C", "D"]
DEFAULT_CORS_ORIGINS = [
    "null",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://quizbot-api-v2.onrender.com",
    "https://quizbot-frontend-v2.onrender.com",
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
Create a {num_questions}-question multiple choice quiz on the topic "{topic}".
Return strict JSON only. Do not include markdown, code fences, or commentary.
The JSON must use exactly this shape:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": {{
        "A": "First option",
        "B": "Second option",
        "C": "Third option",
        "D": "Fourth option"
      }},
      "answer": "A"
    }}
  ]
}}
Rules:
- Include exactly {num_questions} questions.
- Each question must have exactly four options with keys A, B, C, and D.
- The answer must be one of A, B, C, or D.
- Do not include the correct answer inside the question text.
"""


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def parse_quiz_response(text: str, expected_count: int) -> dict:
    try:
        payload = json.loads(strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned malformed quiz JSON.") from exc

    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list) or len(questions) != expected_count:
        raise ValueError("Gemini returned an invalid question list.")

    validated_questions = []
    for question_item in questions:
        if not isinstance(question_item, dict):
            raise ValueError("Gemini returned an invalid question item.")

        question_text = question_item.get("question")
        options = question_item.get("options")
        answer = question_item.get("answer")

        if not isinstance(question_text, str) or not question_text.strip():
            raise ValueError("Gemini returned a question without text.")

        if not isinstance(options, dict):
            raise ValueError("Gemini returned a question without options.")

        normalized_options = {
            str(key).upper(): value
            for key, value in options.items()
        }
        if sorted(normalized_options.keys()) != OPTION_KEYS:
            raise ValueError("Gemini returned invalid option keys.")

        for option_key in OPTION_KEYS:
            option_text = normalized_options[option_key]
            if not isinstance(option_text, str) or not option_text.strip():
                raise ValueError("Gemini returned an empty option.")
            normalized_options[option_key] = option_text.strip()

        normalized_answer = str(answer).upper() if answer is not None else ""
        if normalized_answer not in OPTION_KEYS:
            raise ValueError("Gemini returned an invalid answer.")

        validated_questions.append(
            {
                "question": question_text.strip(),
                "options": normalized_options,
                "answer": normalized_answer,
            }
        )

    return {"questions": validated_questions}


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
    except RuntimeError as exc:
        return {
            "ok": False,
            "model": get_model_name(),
            "error": {"type": "ConfigurationError", "message": str(exc)},
        }

    try:
        response = model.generate_content("Reply with exactly: ok")
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

    try:
        return parse_quiz_response(quiz_text, req.num_questions)
    except ValueError as exc:
        logger.info("Gemini structured quiz validation failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Quiz generation returned an invalid quiz format.",
        ) from exc
