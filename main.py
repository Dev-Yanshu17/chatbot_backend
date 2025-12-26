from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

OLLAMA_URL = "http://localhost:11434/api/generate"

# ---------- MODEL DECISION ----------
def decide_model(message: str):
    keywords = [
        "code", "program", "python", "java", "react", "html",
        "css", "javascript", "algorithm", "function", "error"
    ]
    for word in keywords:
        if word in message.lower():
            return "deepseek-coder:latest"
    return "life4living/ChatGPT"

# ---------- PROMPTS ----------
CODE_PROMPT = (
    "You are a professional programming assistant.\n"
    "Rules:\n"
    "- Give the shortest correct code.\n"
    "- No explanation.\n"
    "- Clean and readable code only.\n"
)

CHAT_PROMPT = (
    "You are a helpful assistant.\n"
    "Rules:\n"
    "- Answer briefly.\n"
    "- Be simple and direct.\n"
)

# ---------- API ----------
@app.post("/chat")
def chat(req: dict):
    user_msg = req["message"]
    model = decide_model(user_msg)

    prompt = CODE_PROMPT if model.startswith("deepseek") else CHAT_PROMPT

    payload = {
        "model": model,
        "prompt": f"{prompt}\nUser: {user_msg}",
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    return {"reply": response.json()["response"]}
