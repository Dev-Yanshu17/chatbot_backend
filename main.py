from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
import requests
from datetime import datetime
import uuid


from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import pagesizes
from reportlab.lib.units import inch
import os


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
# class ChatRequest(BaseModel):
#     message: str

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


# ------------------ DETECT CODE QUESTION ------------------
def is_code_question(text: str) -> bool:
    code_keywords = [
        "code", "program", "function", "bug", "error", "exception",
        "python", "java", "c++", "javascript", "react",
        "node", "api", "sql", "html", "css", "algorithm", "loop",
        "array", "string", "class", "object", "compile", "debug"
    ]

    text = text.lower()
    return any(keyword in text for keyword in code_keywords)

# ------------------ CHAT API ------------------
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        session_id = req.session_id or str(uuid.uuid4())

        if is_code_question(req.message):
            model_name = CODE_MODEL
            model_type = "code"
            final_prompt = f"Give short coding answer.\n{req.message}"
        else:
            model_name = CHAT_MODEL
            model_type = "chat"
            final_prompt = f"Give short answer.\n{req.message}"

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "prompt": final_prompt,
                "stream": False
            },
            timeout=180
        )

        bot_reply = response.json().get("response", "")

        # SAVE WITH SESSION ID
        collection.insert_one({
            "session_id": session_id,
            "model_type": model_type,
            "model_used": model_name,
            "user_message": req.message,
            "bot_reply": bot_reply,
            "created_at": datetime.utcnow()
        })

        return {
            "reply": bot_reply,
            "session_id": session_id
        }

    except Exception as e:
        return {"error": str(e)}
    try:
        # 🔥 AUTO MODEL SELECTION
        if is_code_question(req.message):
            model_name = CODE_MODEL
            model_type = "code"

            # 🔥 Short coding response prompt
            final_prompt = f"""
You are a professional coding assistant.

Rules:
- Give very short explanation (max 2 lines)
- Provide only necessary code
- No long paragraphs
- No extra examples
- Keep response concise

User Question:
{req.message}
"""
        else:
            model_name = CHAT_MODEL
            model_type = "chat"

            # 🔥 Short general response prompt
            final_prompt = f"""
Give a short and clear answer.
Keep response concise.
Do not give long explanation.

User Question:
{req.message}
"""

        response = requests.post(
    OLLAMA_URL,
    json={
        "model": model_name,
        "prompt": final_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.8
        }
    },
    timeout=180
)

        response.raise_for_status()
        bot_reply = response.json().get("response", "")

        # ---------------- SAVE TO MONGODB ----------------
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

    
#----------------load chat history by session id------------------
    
    
@app.get("/chats/{session_id}")
def get_chat_by_session(session_id: str):
    chats = []

    for doc in collection.find({"session_id": session_id}).sort("created_at", 1):
        chats.append({
            "role": "user",
            "text": doc["user_message"]
        })
        chats.append({
            "role": "bot",
            "text": doc["bot_reply"]
        })

    return chats


@app.get("/sessions")
def get_sessions():
    sessions = collection.distinct("session_id")
    return sessions


@app.get("/export/{session_id}")
def export_pdf(session_id: str):
    file_path = f"chat_{session_id}.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=pagesizes.A4
    )

    elements = []
    styles = getSampleStyleSheet()

    # Table Header
    data = [["User Prompt", "Bot Reply"]]

    # Fetch session chats
    chats = collection.find({"session_id": session_id}).sort("created_at", 1)

    for doc_chat in chats:
        data.append([
            Paragraph(doc_chat["user_message"], styles["Normal"]),
            Paragraph(doc_chat["bot_reply"], styles["Normal"])
        ])

    table = Table(data, colWidths=[3 * inch, 3 * inch])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)
    doc.build(elements)

    return FileResponse(file_path, media_type="application/pdf", filename="chat_export.pdf")