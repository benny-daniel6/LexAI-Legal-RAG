from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.models.agent import AgenticRAG, RAGResponse
from backend.models.vector_store import VectorStore
from backend.utils.citation_builder import Citation

router = APIRouter(prefix="/api/query", tags=["query"])


def _get_engine() -> AgenticRAG:
    from backend.main import app
    return app.state.rag_engine

def _get_vs() -> VectorStore:
    from backend.main import app
    return app.state.vector_store


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    doc_id: str | None = None
    top_k: int = Field(default=6, ge=1, le=20)
    confidence_threshold: float = Field(default=0.45, ge=0.0, le=1.0)


class CitationOut(BaseModel):
    chunk_id: str
    source_file: str
    page_num: int
    bbox: list[float]
    text_snippet: str
    confidence: float
    confidence_label: str
    confidence_color: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationOut]
    model_backend: str
    total_chunks_searched: int
    warning: str


class SearchRequest(BaseModel):
    query: str
    doc_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    text: str
    source_file: str
    page_num: int
    confidence: float


@router.post("/", response_model=QueryResponse)
async def run_query(
    req: QueryRequest,
    engine: AgenticRAG = Depends(_get_engine),
):
    result: RAGResponse = await engine.query(
        question=req.question,
        doc_id=req.doc_id,
        top_k=req.top_k,
        confidence_threshold=req.confidence_threshold,
    )
    return QueryResponse(
        question=result.question,
        answer=result.answer,
        citations=[
            CitationOut(
                chunk_id=c.chunk_id,
                source_file=c.source_file,
                page_num=c.page_num,
                bbox=c.bbox,
                text_snippet=c.text_snippet,
                confidence=c.confidence,
                confidence_label=c.confidence_label,
                confidence_color=c.confidence_color,
            )
            for c in result.citations
        ],
        model_backend=result.model_backend,
        total_chunks_searched=result.total_chunks_searched,
        warning=result.warning,
    )


@router.post("/search", response_model=list[SearchResult])
async def semantic_search(
    req: SearchRequest,
    vs: VectorStore = Depends(_get_vs),
):
    """Vector search without LLM synthesis."""
    docs, metas, dists = await asyncio.to_thread(vs.query, req.query, doc_id=req.doc_id, top_k=req.top_k)
    return [
        SearchResult(
            text=doc[:300],
            source_file=meta.get("source_file", ""),
            page_num=int(meta.get("page_num", 0)),
            confidence=round(max(0.0, min(1.0, 1.0 - dist / 2.0)), 3),
        )
        for doc, meta, dist in zip(docs, metas, dists)
    ]


@router.get("/health")
def health():
    from backend.main import app
    syn = app.state.synthesizer
    return {
        "status": "ok",
        "llm_ready": syn.is_ready,
        "llm_backend": syn._backend,
    }
