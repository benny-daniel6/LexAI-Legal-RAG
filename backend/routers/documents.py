from __future__ import annotations

import asyncio
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse, Response
from loguru import logger
from pydantic import BaseModel

from backend.config import get_settings
from backend.models.vector_store import VectorStore
from backend.utils.pdf_processor import extract_chunks, _make_doc_id, render_page_with_highlights

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_vs() -> VectorStore:
    from backend.main import app
    return app.state.vector_store


class DocumentMeta(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    chunks_indexed: int
    message: str


def _save_file(file_obj, save_path: Path):
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file_obj, f)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    vs: VectorStore = Depends(_get_vs),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    cfg = get_settings()

    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    save_path = cfg.uploads_dir / unique_filename

    await asyncio.to_thread(_save_file, file.file, save_path)
    logger.info(f"Saved upload: {save_path}")

    try:
        doc_info = await asyncio.to_thread(extract_chunks, str(save_path))
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"PDF processing failed: {e}")

    doc_info.filename = file.filename

    n = await asyncio.to_thread(vs.add_document, doc_info)

    return UploadResponse(
        doc_id=doc_info.doc_id,
        filename=doc_info.filename,
        page_count=doc_info.page_count,
        chunks_indexed=n,
        message=f"Indexed {n} chunks from {doc_info.page_count} pages.",
    )


@router.get("/", response_model=list[DocumentMeta])
async def list_documents(vs: VectorStore = Depends(_get_vs)):
    return await asyncio.to_thread(vs.list_documents)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, vs: VectorStore = Depends(_get_vs)):
    await asyncio.to_thread(vs.delete_document, doc_id)
    return {"message": f"Document {doc_id} removed from index."}


@router.get("/{doc_id}/pdf")
async def serve_pdf(doc_id: str):
    cfg = get_settings()
    for pdf in cfg.uploads_dir.glob("*.pdf"):
        computed_id = await asyncio.to_thread(_make_doc_id, str(pdf))
        if computed_id == doc_id:
            return FileResponse(str(pdf), media_type="application/pdf")
    raise HTTPException(status_code=404, detail="PDF file not found on server.")


def _get_page_count(pdf_path: str) -> int:
    import fitz
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


@router.get("/{doc_id}/info")
async def document_info(doc_id: str):
    cfg = get_settings()
    for pdf in cfg.uploads_dir.glob("*.pdf"):
        computed_id = await asyncio.to_thread(_make_doc_id, str(pdf))
        if computed_id == doc_id:
            count = await asyncio.to_thread(_get_page_count, str(pdf))
            name_parts = pdf.name.split("_", 1)
            display_name = name_parts[1] if len(name_parts) == 2 and len(name_parts[0]) == 8 else pdf.name
            return {"doc_id": doc_id, "filename": display_name, "page_count": count}
    raise HTTPException(status_code=404, detail="Document not found.")


@router.get("/{doc_id}/page/{page_num}")
async def render_page(
    doc_id: str,
    page_num: int,
    highlight: list[str] = Query(default=None),
    zoom: float = 2.0,
):
    cfg = get_settings()
    highlights = highlight or []
    for pdf in cfg.uploads_dir.glob("*.pdf"):
        computed_id = await asyncio.to_thread(_make_doc_id, str(pdf))
        if computed_id == doc_id:
            try:
                img = await asyncio.to_thread(render_page_with_highlights, str(pdf), page_num, highlights, zoom)
                return Response(content=img, media_type="image/png",
                                headers={"Cache-Control": "no-store"})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Document not found.")
