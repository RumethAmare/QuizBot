# QuizBot Improvement Roadmap

## Overview

QuizBot is currently a small FastAPI backend in `main.py` with a static HTML frontend in `index.html`. The backend sends a topic and requested question count to Google Gemini, then returns generated multiple-choice quiz text.

This roadmap reframes the improvement work as an execution sequence. The order matters: contain the exposed credential first, then stabilize backend behavior, repair the frontend flow, and finally add tests and documentation so future changes are safer.

The current public API should remain stable during this pass:

Request body for `POST /generate_quiz`:

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

Structured quiz JSON is a valuable future improvement, but it should not be mixed into the first stabilization pass unless a deliberate API migration is planned.

## Phase 1: Contain the Security Risk

The hardcoded Google API key in `main.py` should be treated as exposed. No deployment or feature work should happen before this is addressed.

### Implementation

- Rotate the exposed Google API key in Google Cloud or Google AI Studio.
- Remove the hardcoded API key from `main.py`.
- Configure Gemini only from the `GOOGLE_API_KEY` environment variable.
- Add `.env` support for local development.
- Add a `.gitignore` file that excludes `.env`, Python cache files, and virtual environment folders.
- Restrict CORS instead of using `allow_origins=["*"]`.
- Allow only the deployed frontend origin and localhost development origins.

Suggested `.gitignore` entries:

```gitignore
__pycache__/
*.py[cod]
.env
.venv/
venv/
.idea/
.vscode/
```

### Acceptance Criteria

- No API key or secret value remains in committed source files.
- The app can use Gemini when `GOOGLE_API_KEY` is set.
- The app returns a clear controlled error when `GOOGLE_API_KEY` is missing.
- `.env`, `__pycache__/`, and virtual environment folders are ignored by Git.
- CORS no longer allows every origin in production configuration.

## Phase 2: Stabilize the Backend Contract

Keep the existing endpoint names and response shape, but make request validation and failure behavior predictable.

### Implementation

- Keep `GET /` as the health/status endpoint.
- Keep `POST /generate_quiz` as the quiz generation endpoint.
- Validate `topic` as a non-empty string.
- Validate `num_questions` as an integer.
- Restrict `num_questions` to a safe range, such as `1` to `20`.
- Return clear `4xx` responses for invalid user input.
- Return a controlled error response when Gemini fails.
- Avoid exposing raw provider errors directly to users.
- Move prompt construction into a helper function.
- Move Gemini model creation or access into a small helper so the route stays readable.

### Acceptance Criteria

- Valid requests still return `{ "quiz": "..." }`.
- Empty or whitespace-only topics are rejected.
- Non-integer, zero, negative, and excessive question counts are rejected.
- Gemini failures return a user-safe error response.
- The route function remains short enough to show request validation, model access, generation, and response handling clearly.

## Phase 3: Repair the Frontend Flow

The frontend should submit cleanly, validate obvious mistakes before calling the API, and give clear feedback while a request is running.

### Implementation

- Change the question-count input from `type="text"` to `type="number"`.
- Add minimum and maximum values that match the backend limits.
- Remove the duplicate `id="generateBtn"` from the reset button.
- Give the reset button its own unique ID.
- Prevent the form from reloading the page on submit.
- Use a submit event listener instead of inline `onclick`.
- Make the API base URL easy to configure for local and deployed environments.
- Show a clear loading state while the quiz is being generated.
- Keep the generate button disabled during the request.
- Show user-friendly validation errors before sending the request.
- Show user-friendly API error messages when the backend fails.
- Clear the result area when the user resets the form.
- Improve the mobile layout so the form remains readable on small screens.

### Acceptance Criteria

- Pressing the generate button submits without reloading the page.
- Pressing Enter in the form submits exactly once.
- The reset button clears the form and result area.
- The question count input prevents obvious invalid values in the browser.
- The frontend can be pointed at either the local backend or deployed backend with a small configuration change.
- Users see loading and error states instead of silent failures or raw stack/provider details.

## Phase 4: Add Confidence Checks

After the security, backend, and frontend fixes are in place, add tests and documentation updates that make the improved behavior repeatable.

### Implementation

- Add backend tests using FastAPI `TestClient`.
- Mock Gemini calls so tests do not require a network request or real API key.
- Test `GET /` returns the expected status message.
- Test `POST /generate_quiz` succeeds with valid input.
- Test empty `topic` returns a validation error.
- Test invalid `num_questions` returns a validation error.
- Test missing `GOOGLE_API_KEY` returns a controlled error.
- Test Gemini/provider failure returns a controlled error.
- Update `README.md` with setup, environment, run commands, and API usage.
- Consider pinning dependency versions in `requirements.txt`.
- Add a GitHub Actions workflow for pushes and pull requests after local tests exist.

Suggested CI flow:

```yaml
name: Tests

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pip install pytest
      - run: pytest
```

### Acceptance Criteria

- Tests pass locally with `pytest`.
- Tests do not require a real Gemini API key.
- CI runs the same test command used locally.
- `README.md` accurately explains how to run the backend and configure `GOOGLE_API_KEY`.
- No documentation tells users to edit source code just to switch between local and deployed API usage.

## Future Enhancement: Structured Quiz JSON

Returning structured quiz data would make the frontend easier to render and validate, but it changes the API contract. Treat this as a separate migration after the current app is secure and stable.

Recommended future response shape:

```json
{
  "questions": [
    {
      "question": "What does HTML stand for?",
      "options": {
        "A": "HyperText Markup Language",
        "B": "HighText Machine Language",
        "C": "HyperTool Multi Language",
        "D": "Home Tool Markup Language"
      },
      "answer": "A"
    }
  ]
}
```

If backwards compatibility is needed during that migration, temporarily return both fields:

```json
{
  "quiz": "Generated quiz text...",
  "questions": []
}
```

## Implementation Checklist

- [ ] Rotate the exposed Google API key.
- [ ] Remove the hardcoded API key from `main.py`.
- [ ] Read Gemini credentials only from `GOOGLE_API_KEY`.
- [ ] Add local `.env` support.
- [ ] Add `.gitignore`.
- [ ] Restrict CORS origins.
- [ ] Validate `topic`.
- [ ] Validate `num_questions`.
- [ ] Add safe `num_questions` limits.
- [ ] Add controlled backend error handling.
- [ ] Refactor prompt construction into a helper.
- [ ] Update frontend question count to a number input.
- [ ] Fix duplicate button IDs.
- [ ] Prevent form reloads.
- [ ] Make API base URL configurable.
- [ ] Improve frontend loading, reset, and error states.
- [ ] Add backend tests with mocked Gemini calls.
- [ ] Update `README.md` after implementation.
- [ ] Add GitHub Actions workflow after local tests are in place.

## Test Plan

- Verify the backend starts locally with `uvicorn main:app --reload` when `GOOGLE_API_KEY` is set.
- Verify missing `GOOGLE_API_KEY` returns a controlled error.
- Verify `GET /` returns the health/status message.
- Verify `POST /generate_quiz` works with valid input and returns `{ "quiz": "..." }`.
- Verify invalid topic input is rejected.
- Verify invalid question count input is rejected.
- Verify Gemini failures return a controlled error.
- Verify the frontend can call the local backend.
- Verify the frontend can call the deployed backend when configured to do so.
- Verify reset clears the form and result area.
- Verify tests pass locally with `pytest`.
- Verify GitHub Actions passes on push or pull request once CI is added.
- Verify no API keys or `.env` files are committed.

## Assumptions

- The project should remain a small FastAPI backend plus static HTML frontend.
- Security cleanup is the first required implementation phase.
- The existing endpoint names and response shape should remain stable during this pass.
- Gemini should be mocked in tests, not called live.
- Structured quiz JSON is valuable, but should be treated as a later product/API migration.
- The improvement work should keep the app beginner-friendly and easy to run locally.
