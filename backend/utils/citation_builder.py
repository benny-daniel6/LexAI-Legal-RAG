from __future__ import annotations
from dataclasses import dataclass
import math
from typing import List


CONFIDENCE_HIGH = 0.75
CONFIDENCE_MED  = 0.55


@dataclass
class Citation:
    chunk_id: str
    source_file: str
    page_num: int
    bbox: list[float]
    text_snippet: str
    raw_score: float
    confidence: float
    confidence_label: str
    confidence_color: str


def logit_to_probability(logit: float) -> float:
    """Sigmoid: converts cross-encoder logit to [0, 1] probability."""
    try:
        return 1.0 / (1.0 + math.exp(-logit))
    except OverflowError:
        return 0.0 if logit < 0 else 1.0


def label_confidence(score: float) -> tuple[str, str]:
    if score >= CONFIDENCE_HIGH:
        return "HIGH", "#10b981"
    elif score >= CONFIDENCE_MED:
        return "MEDIUM", "#f59e0b"
    else:
        return "LOW", "#ef4444"


def build_citations(
    retrieved_docs: list[str],
    retrieved_metadatas: list[dict],
    retrieved_scores: list[float],
    confidence_threshold: float = 0.45,
) -> list[Citation]:
    """Converts cross-encoder scored chunks into Citation objects.
    Filters below threshold, deduplicates by page+source."""
    citations: list[Citation] = []
    seen: set[str] = set()

    for text, meta, score in zip(retrieved_docs, retrieved_metadatas, retrieved_scores):
        conf = logit_to_probability(score)
        if conf < confidence_threshold:
            continue

        key = f"{meta.get('source_file', '')}::p{meta.get('page_num', 0)}"
        if key in seen:
            continue
        seen.add(key)

        label, color = label_confidence(conf)
        citations.append(
            Citation(
                chunk_id=meta.get("chunk_id", ""),
                source_file=meta.get("source_file", "unknown"),
                page_num=int(meta.get("page_num", 0)),
                bbox=meta.get("bbox", []),
                text_snippet=text[:400],
                raw_score=score,
                confidence=round(conf, 3),
                confidence_label=label,
                confidence_color=color,
            )
        )

    citations.sort(key=lambda c: c.confidence, reverse=True)
    return citations


def format_context_for_llm(citations: list[Citation]) -> str:
    """Builds the context block injected into the LLM prompt."""
    parts = []
    for i, c in enumerate(citations, 1):
        parts.append(
            f"[SOURCE {i} | {c.source_file} | Page {c.page_num} | "
            f"Confidence {c.confidence:.0%}]\n{c.text_snippet}"
        )
    return "\n\n---\n\n".join(parts)
