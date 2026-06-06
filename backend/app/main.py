from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, quiz, profile, ocr, roadmap, analytics
from app.core.config import settings
from contextlib import asynccontextmanager
from app.services.llm_service import load_models
import traceback
from fastapi import Request
from starlette.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to TutorAI Internal Profile & Vector MCP Server...")
    from app.services.mcp_service import mcp_service
    # Spawn and connect to internal FastMCP server
    success = await mcp_service.connect_to_server(
        "tutor_mcp",
        "python",
        ["-m", "app.mcp_servers.tutor_mcp_server"]
    )
    if success:
        print("[Lifespan] MCP connection established successfully.")
    else:
        print("[Lifespan] Failed to connect to internal MCP server.")

    # Initialize ExpertRegistry (maps subjects to LoRA experts / GeminiTutor)
    # This is zero-cost — adapters are already loaded by llm_service.load_models()
    from app.services.expert_service import ExpertRegistry
    ExpertRegistry.initialize()
    print("[Lifespan] ExpertRegistry initialized.")
        
    yield
    
    print("[Lifespan] Disconnecting all active MCP connections...")
    await mcp_service.disconnect_all()

app = FastAPI(
    title="TutorAI API",
    lifespan=lifespan
)

@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"GLOBAL ERROR CAUGHT: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(profile.router)
app.include_router(ocr.router)
app.include_router(roadmap.router)
app.include_router(analytics.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=False)
