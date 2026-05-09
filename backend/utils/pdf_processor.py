from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import fitz  # PyMuPDF


@dataclass
class TextChunk:
    chunk_id: str
    doc_id: str
    text: str
    page_num: int
    bbox: list[float]
    char_start: int
    char_end: int


@dataclass
class DocumentInfo:
    doc_id: str
    filename: str
    page_count: int
    chunks: List[TextChunk] = field(default_factory=list)


def _make_doc_id(filepath: str) -> str:
    content = Path(filepath).read_bytes()
    return hashlib.md5(content).hexdigest()[:12]


def _split_into_chunks(
    page_text: str,
    max_chars: int = 1500,
    overlap_chars: int = 150,
) -> list[tuple[int, int]]:
    """Return (start, end) char-index pairs. Prefers splitting at paragraph/sentence boundaries."""
    separators = ["\n\n", "\n", ". ", "! ", "? "]
    chunks: list[tuple[int, int]] = []
    start = 0
    text_len = len(page_text)

    while start < text_len:
        end = min(start + max_chars, text_len)
        if end < text_len:
            for sep in separators:
                idx = page_text.rfind(sep, start, end)
                if idx != -1 and idx > start + max_chars // 2:
                    end = idx + len(sep)
                    break
        chunks.append((start, end))
        start = max(start + 1, end - overlap_chars)

    return chunks


def extract_chunks(pdf_path: str, max_chars: int = 1500) -> DocumentInfo:
    path = Path(pdf_path)
    doc_id = _make_doc_id(pdf_path)
    doc = fitz.open(pdf_path)

    all_chunks: list[TextChunk] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        words = page.get_text("words")
        if not words:
            continue

        page_text = page.get_text("text")
        span_pairs = _split_into_chunks(page_text, max_chars)

        for char_start, char_end in span_pairs:
            chunk_text = page_text[char_start:char_end].strip()
            if len(chunk_text) < 30:
                continue

            bbox = _estimate_bbox(words, page_text, char_start, char_end, page)

            chunk = TextChunk(
                chunk_id=f"{doc_id}_p{page_num}_{uuid.uuid4().hex[:6]}",
                doc_id=doc_id,
                text=chunk_text,
                page_num=page_num,
                bbox=bbox,
                char_start=char_start,
                char_end=char_end,
            )
            all_chunks.append(chunk)

    page_count = len(doc)
    doc.close()
    return DocumentInfo(
        doc_id=doc_id,
        filename=path.name,
        page_count=page_count,
        chunks=all_chunks,
    )


def _estimate_bbox(
    words: list,
    page_text: str,
    char_start: int,
    char_end: int,
    page: fitz.Page,
) -> list[float]:
    """Best-effort bounding box for a character range. Falls back to full page rect."""
    blocks = page.get_text("blocks")
    x0_all, y0_all, x1_all, y1_all = [], [], [], []

    consumed = 0
    for block in blocks:
        block_text = block[4]
        block_end = consumed + len(block_text)
        if block_end > char_start and consumed < char_end:
            x0_all.append(block[0])
            y0_all.append(block[1])
            x1_all.append(block[2])
            y1_all.append(block[3])
        consumed = block_end

    if x0_all:
        return [min(x0_all), min(y0_all), max(x1_all), max(y1_all)]

    r = page.rect
    return [r.x0, r.y0, r.x1, r.y1]


def render_page_with_highlights(
    pdf_path: str,
    page_num: int,
    highlight_texts: list[str],
    zoom: float = 2.0,
) -> bytes:
    """Renders a PDF page as PNG with yellow highlights on matched text."""
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]

    for text in highlight_texts:
        text = text.strip()
        if not text:
            continue
        search_str = text[:80]
        areas = page.search_for(search_str)
        for rect in areas:
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=[1.0, 0.85, 0.0])
            annot.update()

    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes
