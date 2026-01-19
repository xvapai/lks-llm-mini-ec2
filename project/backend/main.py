import os
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx

print("=" * 70)
print("🚀 BACKEND STARTING...")
print("=" * 70)

load_dotenv()

# Import db with error handling
try:
    import db
    print("✓ db module imported successfully")
except Exception as e:
    print(f"✗ FATAL: Cannot import db module")
    print(f"Error: {e}")
    traceback.print_exc()
    raise

app = FastAPI(title="AI Chat Debug")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")

print(f"⚙️  Configuration:")
print(f"   - Database: {db.DB_TYPE}")
print(f"   - Ollama: {OLLAMA_HOST}")
print(f"   - Model: {OLLAMA_MODEL}")

@app.on_event("startup")
def startup():
    print("\n🔧 Running startup tasks...")
    try:
        db.init_db()
        print(f"✓ Database initialized ({db.DB_TYPE})")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        traceback.print_exc()

class ChatRequest(BaseModel):
    message: str
    use_history: bool = True

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    try:
        # Try multiple paths
        paths = [
            "../frontend/index.html",
        ]

        for path in paths:
            if os.path.exists(path):
                print(f"✓ Serving frontend from: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())

        # If no frontend found, show error
        return HTMLResponse(content="""
        <html>
        <body style="font-family: monospace; padding: 2rem; background: #0f172a; color: #e2e8f0;">
            <h1>❌ Frontend Not Found</h1>
            <p>Please create the frontend file at one of these locations:</p>
            <ul>
                <li>~/chatapp/frontend/index.html</li>
            </ul>
            <p>Backend is running at <a href="/health" style="color: #3b82f6;">/health</a></p>
        </body>
        </html>
        """, status_code=404)
    except Exception as e:
        print(f"✗ Error serving frontend: {e}")
        traceback.print_exc()
        return HTMLResponse(content=f"<h1>Error loading frontend: {e}</h1>", status_code=500)

@app.get("/health")
async def health():
    print("\n📊 Health check requested")
    result = {
        "status": "ok",
        "database": db.DB_TYPE,
        "ollama_host": OLLAMA_HOST,
        "model": OLLAMA_MODEL,
    }

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            if resp.status_code == 200:
                result["ollama"] = "connected"
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                result["available_models"] = model_names
                result["model_available"] = any(OLLAMA_MODEL in name for name in model_names)
                print(f"✓ Ollama connected, models: {model_names}")
            else:
                result["ollama"] = f"error (status {resp.status_code})"
                print(f"✗ Ollama returned status {resp.status_code}")
    except httpx.ConnectError as e:
        result["ollama"] = "not running"
        result["error"] = str(e)
        print(f"✗ Ollama connection failed: {e}")
    except Exception as e:
        result["ollama"] = f"error: {str(e)}"
        print(f"✗ Ollama check failed: {e}")

    print(f"Health result: {result}")
    return result

@app.post("/chat")
async def chat(request: ChatRequest):
    print("\n" + "=" * 70)
    print(f"💬 CHAT REQUEST")
    print(f"   Message: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
    print(f"   Use history: {request.use_history}")
    print("=" * 70)

    try:
        # STEP 1: Save user message
        print("\n[STEP 1] Saving user message to database...")
        try:
            db.save_message("user", request.message)
            print("✓ User message saved")
        except Exception as e:
            print(f"✗ Database save failed: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # STEP 2: Build context
        print("\n[STEP 2] Building conversation context...")
        messages = []

        if request.use_history:
            try:
                history = db.get_history(limit=10)
                for h in history[-6:]:  # Last 3 exchanges
                    messages.append({"role": h["role"], "content": h["content"]})
                print(f"✓ Loaded {len(messages)} messages from history")
            except Exception as e:
                print(f"⚠️  Could not load history (continuing anyway): {e}")

        messages.append({"role": "user", "content": request.message})
        print(f"✓ Context prepared ({len(messages)} messages total)")

        # STEP 3: Call Ollama
        print(f"\n[STEP 3] Calling Ollama at {OLLAMA_HOST}...")
        print(f"   Model: {OLLAMA_MODEL}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Health check first
                print("   Checking Ollama connection...")
                try:
                    health_resp = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
                    if health_resp.status_code != 200:
                        raise HTTPException(
                            status_code=503,
                            detail=f"Ollama health check failed (status {health_resp.status_code})"
                        )
                    print("   ✓ Ollama is reachable")
                except httpx.ConnectError:
                    print("   ✗ Cannot connect to Ollama")
                    raise HTTPException(
                        status_code=503,
                        detail="Ollama is not running. Start with: sudo systemctl start ollama"
                    )

                # Make actual request
                print(f"   Sending request to model '{OLLAMA_MODEL}'...")
                response = await client.post(
                    f"{OLLAMA_HOST}/api/chat",
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "num_ctx": 512,
                            "temperature": 0.7,
                        }
                    }
                )

                print(f"   Response status: {response.status_code}")

                if response.status_code != 200:
                    error_text = response.text
                    print(f"   ✗ Ollama error response: {error_text[:200]}")

                    if "not found" in error_text.lower():
                        raise HTTPException(
                            status_code=503,
                            detail=f"Model '{OLLAMA_MODEL}' not found. Run: ollama pull {OLLAMA_MODEL}"
                        )

                    raise HTTPException(
                        status_code=500,
                        detail=f"Ollama returned error: {error_text[:200]}"
                    )

                result = response.json()

                if "message" not in result or "content" not in result["message"]:
                    print(f"   ✗ Invalid response structure: {result}")
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid response format from Ollama"
                    )

                assistant_msg = result["message"]["content"]
                print(f"✓ Received response ({len(assistant_msg)} characters)")
                print(f"   Preview: {assistant_msg[:100]}{'...' if len(assistant_msg) > 100 else ''}")

        except httpx.TimeoutException:
            print("   ✗ Request timed out")
            raise HTTPException(
                status_code=504,
                detail="Request timed out. Try a shorter message or smaller model."
            )
        except httpx.ConnectError as e:
            print(f"   ✗ Connection error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to Ollama. Is it running?"
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"   ✗ Unexpected error: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

        # STEP 4: Save assistant response
        print("\n[STEP 4] Saving assistant response...")
        try:
            db.save_message("assistant", assistant_msg)
            print("✓ Assistant response saved")
        except Exception as e:
            print(f"⚠️  Could not save response (continuing anyway): {e}")

        print("\n" + "=" * 70)
        print("✅ CHAT REQUEST COMPLETED SUCCESSFULLY")
        print("=" * 70 + "\n")

        return {"response": assistant_msg, "model": OLLAMA_MODEL}

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}")
        print(f"   Details: {e}")
        traceback.print_exc()
        print("=" * 70 + "\n")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {type(e).__name__}: {str(e)}"
        )

@app.get("/history")
async def get_history(limit: int = 50):
    print(f"\n📜 History requested (limit={limit})")
    try:
        history = db.get_history(limit)
        print(f"✓ Returning {len(history)} messages")
        return {"history": history}
    except Exception as e:
        print(f"✗ History retrieval failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history")
async def clear_history():
    print("\n🗑️  Clear history requested")
    try:
        db.clear_history()
        print("✓ History cleared")
        return {"status": "cleared"}
    except Exception as e:
        print(f"✗ Clear failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

print("=" * 70)
print("✅ BACKEND INITIALIZATION COMPLETE")
print("=" * 70 + "\n")
