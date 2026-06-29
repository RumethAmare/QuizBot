import asyncio
import json

import httpx

import main


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModel:
    def __init__(self, text="Generated quiz text"):
        self.text = text

    def generate_content(self, prompt):
        return FakeResponse(self.text)


class FailingModel:
    def generate_content(self, prompt):
        raise RuntimeError("provider failed")


async def send_request(method, url, **kwargs):
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, url, **kwargs)
    return response


def request(method, url, **kwargs):
    return asyncio.run(send_request(method, url, **kwargs))


def use_model(monkeypatch, model):
    monkeypatch.setattr(main, "get_model", lambda: model)


def test_read_root_returns_status_message():
    response = request("GET", "/")

    assert response.status_code == 200
    assert response.json() == {"message": "AI Quiz Generator is running."}


def test_read_status_returns_runtime_diagnostics(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL_NAME", "test-model")

    response = request("GET", "/status")

    assert response.status_code == 200
    assert response.json() == {
        "message": "AI Quiz Generator is running.",
        "model": "test-model",
        "google_api_key_configured": True,
        "google_api_key_fingerprint": main.get_api_key_fingerprint(),
    }


def test_debug_gemini_returns_success(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_NAME", "test-model")
    use_model(monkeypatch, FakeModel("ok"))

    response = request("GET", "/debug/gemini")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "model": "test-model",
        "response_preview": "ok",
    }


def test_debug_gemini_returns_provider_error(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_NAME", "test-model")
    use_model(monkeypatch, FailingModel())

    response = request("GET", "/debug/gemini")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "model": "test-model",
        "error": {"type": "RuntimeError", "message": "provider failed"},
    }


VALID_QUIZ = {
    "questions": [
        {
            "question": "What does HTML stand for?",
            "options": {
                "A": "HyperText Markup Language",
                "B": "HighText Machine Language",
                "C": "HyperTool Multi Language",
                "D": "Home Tool Markup Language",
            },
            "answer": "A",
        }
    ]
}


def test_generate_quiz_returns_structured_questions(monkeypatch):
    use_model(monkeypatch, FakeModel(json.dumps(VALID_QUIZ)))

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "HTML basics", "num_questions": 1},
    )

    assert response.status_code == 200
    assert response.json() == VALID_QUIZ


def test_generate_quiz_rejects_malformed_provider_json(monkeypatch):
    use_model(monkeypatch, FakeModel("not json"))

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "Python basics", "num_questions": 1},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Quiz generation returned an invalid quiz format."


def test_generate_quiz_rejects_missing_question_fields(monkeypatch):
    invalid_quiz = {"questions": [{"question": "Incomplete"}]}
    use_model(monkeypatch, FakeModel(json.dumps(invalid_quiz)))

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "Python basics", "num_questions": 1},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Quiz generation returned an invalid quiz format."


def test_generate_quiz_rejects_invalid_answer_letter(monkeypatch):
    invalid_quiz = {
        "questions": [
            {
                "question": "Pick one.",
                "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"},
                "answer": "E",
            }
        ]
    }
    use_model(monkeypatch, FakeModel(json.dumps(invalid_quiz)))

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "Python basics", "num_questions": 1},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Quiz generation returned an invalid quiz format."


def test_generate_quiz_rejects_empty_topic(monkeypatch):
    use_model(monkeypatch, FakeModel())

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "   ", "num_questions": 2},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Topic must not be empty."


def test_generate_quiz_rejects_invalid_question_count(monkeypatch):
    use_model(monkeypatch, FakeModel())

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "Python basics", "num_questions": 21},
    )

    assert response.status_code == 422


def test_generate_quiz_returns_controlled_error_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "Python basics", "num_questions": 2},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "GOOGLE_API_KEY is not configured."


def test_generate_quiz_returns_controlled_error_on_provider_failure(monkeypatch):
    use_model(monkeypatch, FailingModel())

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "Python basics", "num_questions": 2},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Quiz generation failed. Please try again later."
