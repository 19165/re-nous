from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from api.routes import router as research_router
from utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler to initialize database schemas on startup.
    """
    logger.info("🚀 [FastAPI] Starting Multi-Agent Research Assistant API Server...")
    await init_db()
    yield
    logger.info("🛑 [FastAPI] Shutting down API Server...")

app = FastAPI(
    title="🌸 Multi-Agent Research Assistant API",
    description="Enterprise-grade autonomous research assistant powered by LangGraph, Ollama, Tavily, Redis, and PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(research_router)

@app.get("/health", tags=["System Health"])
async def health_check():
    """Returns the operational status of the service."""
    return {"status": "ok", "service": "Multi-Agent Research Assistant API", "version": "1.0.0"}

@app.get("/", tags=["Root"])
async def root():
    """Root welcome endpoint with link to interactive Swagger docs."""
    return {
        "message": "Welcome to the Multi-Agent Research Assistant API! 🌸✨",
        "docs_url": "/docs",
        "endpoints": {
            "submit_research": "POST /research",
            "get_status_and_report": "GET /research/{id}",
            "stream_progress": "GET /research/{id}?stream=true",
            "get_trace": "GET /research/{id}/trace"
        }
    }
