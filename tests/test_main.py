import asyncio

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
    main.get_model.cache_clear()
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
    }


def test_generate_quiz_returns_quiz_text(monkeypatch):
    use_model(monkeypatch, FakeModel("Question 1\nAnswer: A"))

    response = request(
        "POST",
        "/generate_quiz",
        json={"topic": "Python basics", "num_questions": 2},
    )

    assert response.status_code == 200
    assert response.json() == {"quiz": "Question 1\nAnswer: A"}


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
    main.get_model.cache_clear()
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
