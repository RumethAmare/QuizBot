from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

genai.configure(api_key="AIzaSyDn6WJLko--BWHcRbipzGv5ea5EGiLS-1U")

model = genai.GenerativeModel('gemini-2.5-pro')

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "AI Quiz Generator is running."}

class QuizRequest(BaseModel):
    topic: str
    num_questions: int

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate_quiz")
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