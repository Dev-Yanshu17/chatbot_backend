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
    allow_origins=["*"],   # for development
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ MONGODB ------------------
# Make sure MongoDB service is running
client = MongoClient("mongodb://localhost:27017")

db = client["ollama_chatbot"]      # Database name
collection = db["chats"]           # Collection name

# ------------------ OLLAMA ------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "life4living/ChatGPT"

# ------------------ REQUEST MODEL ------------------
class ChatRequest(BaseModel):
    message: str

# ------------------ CHAT API ------------------
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        # Call Ollama
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": req.message,
                "stream": False
            },
            timeout=120
        )

        bot_reply = response.json().get("response", "")

        # Save chat to MongoDB
        chat_doc = {
            "user_message": req.message,
            "bot_reply": bot_reply,
            "created_at": datetime.utcnow()
        }

        collection.insert_one(chat_doc)

        return {"reply": bot_reply}

    except Exception as e:
        return {"error": str(e)}

# ------------------ GET CHAT HISTORY ------------------
@app.get("/chats")
def get_chats():
    chats = []

    for doc in collection.find().sort("created_at", -1):
        chats.append({
            "id": str(doc["_id"]),
            "user_message": doc["user_message"],
            "bot_reply": doc["bot_reply"],
            "created_at": doc["created_at"]
        })

    return chats
