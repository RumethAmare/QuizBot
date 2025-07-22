from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os

# Configure Google API key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables")

genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel('gemini-2.5-pro')

app = FastAPI()

# Health check route
@app.get("/")
def read_root():
    return {"message": "AI Quiz Generator is running."}

# Request model
class QuizRequest(BaseModel):
    topic: str
    num_questions: int

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific domains in production for security
    allow_methods=["*"],
    allow_headers=["*"],
)

# Quiz generation route
@app.post("/generate_quiz/")
def generate_quiz(req: QuizRequest):
    prompt = f"""
    Create a {req.num_questions}-question multiple choice quiz on the topic '{req.topic}'.
    For each question, provide:
    - The question
    - 4 options labeled A, B, C, D
    - The correct answer at the end in this format: 'Answer: X'
    Format the output cleanly and clearly.
    """
    response = model.generate_content(prompt)
    return {"quiz": response.text}
