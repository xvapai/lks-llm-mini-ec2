import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import db
import asyncio

load_dotenv()

app = FastAPI(title="Low-Resource AI Chat")

# CORS for same-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi")

# Initialize DB on startup
@app.on_event("startup")
def startup():
    db.init_db()
    print(f"✅ Database initialized ({db.DB_TYPE})")
    print(f"✅ Using Ollama model: {OLLAMA_MODEL}")

# Models
class ChatRequest(BaseModel):
    message: str
    use_history: bool = True

class ChatResponse(BaseModel):
    response: str
    model: str

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("../frontend/index.html", "r") as f:
        return f.read()

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Save user message
        db.save_message("user", request.message)
        
        # Build context
        messages = []
        if request.use_history:
            history = db.get_history(limit=10)  # Last 10 messages for context
            for h in history[-6:]:  # Only last 3 exchanges to save RAM
                messages.append({"role": h["role"], "content": h["content"]})
        
        messages.append({"role": "user", "content": request.message})
        
        # Call Ollama
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_ctx": 1024,  # Low context window to save RAM
                        "temperature": 0.7,
                    }
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama error")
            
            result = response.json()
            assistant_message = result["message"]["content"]
            
            # Save assistant response
            db.save_message("assistant", assistant_message)
            
            return ChatResponse(response=assistant_message, model=OLLAMA_MODEL)
    
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ollama not running. Start with: ollama serve")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get history
@app.get("/history")
async def get_history(limit: int = 50):
    return {"history": db.get_history(limit)}

# Clear history
@app.delete("/history")
async def clear_history():
    db.clear_history()
    return {"status": "cleared"}

# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "database": db.DB_TYPE,
        "ollama_host": OLLAMA_HOST,
        "model": OLLAMA_MODEL
    }
