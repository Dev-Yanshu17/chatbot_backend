from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
import requests
from datetime import datetime

# ------------------ APP ------------------
app = FastAPI()

# ------------------ CORS ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ MONGODB ------------------
client = MongoClient("mongodb://localhost:27017")
db = client["ollama_chatbot"]
collection = db["chats"]

# ------------------ OLLAMA ------------------
OLLAMA_URL = "http://localhost:11434/api/generate"

CHAT_MODEL = "life4living/ChatGPT"
CODE_MODEL = "deepseek-coder"

# ------------------ REQUEST MODEL ------------------
class ChatRequest(BaseModel):
    message: str

# ------------------ HELPER: DETECT CODE QUESTION ------------------
def is_code_question(text: str) -> bool:
    code_keywords = [
        "code", "program", "function", "bug", "error", "exception",
        "python", "java", "c++", "c program", "javascript", "react",
        "node", "api", "sql", "html", "css", "algorithm", "loop",
        "array", "string", "class", "object", "compile", "debug"
    ]

    text = text.lower()
    return any(keyword in text for keyword in code_keywords)

# ------------------ CHAT API ------------------
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        # ✅ AUTO MODEL SELECTION
        if is_code_question(req.message):
            model_name = CODE_MODEL
            model_type = "code"
        else:
            model_name = CHAT_MODEL
            model_type = "chat"

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "prompt": req.message,
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()
        bot_reply = response.json().get("response", "")

        # Save chat
        collection.insert_one({
            "model_type": model_type,
            "model_used": model_name,
            "user_message": req.message,
            "bot_reply": bot_reply,
            "created_at": datetime.utcnow()
        })

        return {
            "reply": bot_reply,
            "model_used": model_name,
            "model_type": model_type
        }

    except Exception as e:
        return {"error": str(e)}

# ------------------ GET CHAT HISTORY ------------------
@app.get("/chats")
def get_chats():
    chats = []
    for doc in collection.find().sort("created_at", -1):
        chats.append({
            "id": str(doc["_id"]),
            "model_used": doc["model_used"],
            "model_type": doc["model_type"],
            "user_message": doc["user_message"],
            "bot_reply": doc["bot_reply"],
            "created_at": doc["created_at"]
        })
    return chats

# ------------------ HEALTH CHECK ------------------
@app.get("/")
def root():
    return {"status": "Backend is running 🚀"}
