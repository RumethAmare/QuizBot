# QuizBot

QuizBot is an AI quiz generator with a FastAPI backend and a static HTML frontend. The backend sends quiz-generation prompts to Google Gemini and returns a multiple-choice quiz for the requested topic and number of questions.

## Features

- Generate multiple-choice quizzes from a topic.
- Choose the number of questions to generate.
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
└── requirements.txt
```

- `main.py` contains the FastAPI application and Gemini integration.
- `index.html` contains the static frontend for entering a topic and question count.
- `requirements.txt` lists the Python dependencies.

## Setup

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

The backend should read the Google Gemini API key from the `GOOGLE_API_KEY` environment variable:

```bash
export GOOGLE_API_KEY="your-api-key"
```

On Windows PowerShell:

```powershell
$env:GOOGLE_API_KEY="your-api-key"
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

Open `index.html` in a browser, enter a topic, enter the number of questions, and select **Generate Quiz**.

The current frontend sends requests to the deployed Render API endpoint:

```text
https://quizbot-hi5v.onrender.com/generate_quiz/
```

If you want the frontend to use a local backend instead, update the `fetch` URL in `index.html` to:

```text
http://127.0.0.1:8000/generate_quiz
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

The backend currently uses the Gemini model:

```text
gemini-2.5-pro
```

## Known Issues and Security Notes

- `main.py` currently contains a hardcoded Google API key. Remove the hardcoded key, rotate it in Google Cloud or Google AI Studio, and use only the `GOOGLE_API_KEY` environment variable.
- CORS is currently configured with `allow_origins=["*"]`, which allows requests from any origin. For production, restrict this to trusted frontend domains.
- The API does not currently validate that `num_questions` is positive or within a safe limit.
- The frontend uses a text input for the question count instead of a numeric input.
- The app does not currently include automated tests.
