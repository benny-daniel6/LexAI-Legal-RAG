from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from backend.models.agent import AgenticRAG
from backend.models.synthesizer import Synthesizer
from backend.models.vector_store import VectorStore
from backend.routers import documents, query

# ── Persistent logging (survives container restarts via volume mount) ─────────
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.add(
    str(_LOG_DIR / "lexai.log"),
    rotation="50 MB",
    retention="7 days",
    compression="gz",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="INFO",
    enqueue=True,  # thread-safe async logging
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LexAI backend starting")

    app.state.vector_store = VectorStore()
    app.state.synthesizer = Synthesizer()
    app.state.rag_engine = AgenticRAG(app.state.vector_store, app.state.synthesizer)

    llm_status = "ready" if app.state.synthesizer.is_ready else "model not loaded"
    logger.info(f"LLM backend ({app.state.synthesizer._backend}): {llm_status}")
    logger.info("LexAI backend ready -- http://localhost:8000/docs")

    yield

    logger.info("LexAI backend shutting down")


app = FastAPI(
    title="LexAI",
    description="RAG pipeline for legal contract analysis with cited answers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(query.router)


@app.get("/health", tags=["meta"])
def root_health():
    return {"status": "ok", "app": "LexAI"}


_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse(str(_FRONTEND / "index.html"))

if _FRONTEND.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND)), name="assets")
