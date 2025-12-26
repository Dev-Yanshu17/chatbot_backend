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
    allow_origins=["*"],  # React frontend
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

SUPPORTED_MODELS = {
    "chat": "life4living/ChatGPT",
    "code": "deepseek-coder"
}

# ------------------ REQUEST MODEL ------------------
class ChatRequest(BaseModel):
    message: str
    model_type: str = "chat"  # default model

# ------------------ CHAT API ------------------
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        model_name = SUPPORTED_MODELS.get(req.model_type, "life4living/ChatGPT")

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "prompt": req.message,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        bot_reply = response.json().get("response", "")

        # Save chat
        collection.insert_one({
            "model": model_name,
            "user_message": req.message,
            "bot_reply": bot_reply,
            "created_at": datetime.utcnow()
        })

        return {
            "reply": bot_reply,
            "model_used": model_name
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
            "model": doc.get("model"),
            "user_message": doc["user_message"],
            "bot_reply": doc["bot_reply"],
            "created_at": doc["created_at"]
        })
    return chats

# ------------------ HEALTH CHECK ------------------
@app.get("/")
def root():
    return {"status": "Backend is running 🚀"}
