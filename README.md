# QuizBot

QuizBot is an AI quiz generator with a FastAPI backend and a static HTML frontend. The backend sends quiz-generation prompts to Google Gemini and returns a multiple-choice quiz for the requested topic and number of questions.

## Features

- Generate multiple-choice quizzes from a topic.
- Choose between 1 and 20 questions.
- Return four answer options per question.
- Include the correct answer in the generated response.
- Use a simple browser-based frontend in `index.html`.
- Expose a small FastAPI API for quiz generation.

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Pydantic
- Google Generative AI SDK
- HTML, CSS, and JavaScript

## File Structure

```text
.
├── index.html
├── main.py
├── README.md
├── requirements.txt
└── tests/
```

- `main.py` contains the FastAPI application and Gemini integration.
- `index.html` contains the static frontend for entering a topic and question count.
- `requirements.txt` lists the Python dependencies.
- `tests/` contains backend tests with mocked Gemini calls.

## Setup

Install the pinned Python dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

The backend reads the Google Gemini API key from the `GOOGLE_API_KEY` environment variable:

```bash
export GOOGLE_API_KEY="your-api-key"
```

On Windows PowerShell:

```powershell
$env:GOOGLE_API_KEY="your-api-key"
```

You can also create a local `.env` file:

```env
GOOGLE_API_KEY=your-api-key
```

The `.env` file is ignored by Git and should not be committed.

### CORS Configuration

By default, the backend allows common local development origins and the deployed Render origin. To override the list, set `CORS_ORIGINS` as a comma-separated list:

```bash
export CORS_ORIGINS="http://127.0.0.1:5500,https://your-frontend.example.com"
```

## Running the Backend Locally

Start the FastAPI development server:

```bash
uvicorn main:app --reload
```

By default, the API will be available at:

```text
http://127.0.0.1:8000
```

You can open the generated FastAPI documentation at:

```text
http://127.0.0.1:8000/docs
```

## Using the Frontend

Serve `index.html` from a local static server or deployed frontend host, enter a topic, enter the number of questions, and select **Generate Quiz**.

The frontend uses this deployed backend by default:

```text
https://quizbot-hi5v.onrender.com
```

To point the static frontend at a local backend without editing the fetch call, add an `apiBaseUrl` query parameter:

```text
http://127.0.0.1:5500/index.html?apiBaseUrl=http://127.0.0.1:8000
```

You can also define `window.QUIZBOT_API_BASE_URL` before the app script runs:

```html
<script>
    window.QUIZBOT_API_BASE_URL = "http://127.0.0.1:8000";
</script>
```

Because backend CORS is restricted, avoid opening `index.html` directly from `file://` when calling the API. Use a local static server such as VS Code Live Server, or:

```bash
python3 -m http.server 5500
```

## API Endpoints

### `GET /`

Returns a status message confirming that the API is running.

Example response:

```json
{
  "message": "AI Quiz Generator is running."
}
```

### `POST /generate_quiz`

Generates a multiple-choice quiz for the requested topic.

Request body:

```json
{
  "topic": "Python basics",
  "num_questions": 5
}
```

Response body:

```json
{
  "quiz": "Generated quiz text..."
}
```

Validation rules:

- `topic` must not be empty.
- `num_questions` must be an integer from 1 to 20.

The backend currently uses the Gemini model:

```text
gemini-2.5-pro
```

## Running Tests

Run the backend test suite with:

```bash
pytest
```

The tests use the FastAPI ASGI app directly and mock Gemini calls, so they do not require a real API key or network access.

## Security Notes

- Keep `GOOGLE_API_KEY` in an environment variable or local `.env` file.
- Rotate any API key that was previously committed or shared.
- Do not commit `.env`, virtual environments, Python cache files, or generated test caches.
