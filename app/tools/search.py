"""
search.py — Public search façade for PulseOps docs.

Delegates all work to HybridDocsIndex (embeddings.py), which implements:
  1. Markdown chunking  (sliding window, CHUNK_MAX_CHARS / CHUNK_OVERLAP_CHARS)
  2. OpenRouter embeddings  (nvidia/llama-nemotron-embed-vl-1b-v2:free by default)
  3. ChromaDB vector store  (persisted to data/chroma_store/)
  4. Hybrid retrieval  (BM25-style keyword + cosine vector, weighted sum)
  5. SQLite mirror  (chunk metadata in doc_chunks table via DocChunkRepository)

The `search_docs` function is the only public entry-point consumed by the
tool registry.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.config import settings, DOCS_DIR
from app.tools.embeddings import HybridDocsIndex

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton HybridDocsIndex — initialised once per process
# ---------------------------------------------------------------------------

_hybrid_index: HybridDocsIndex | None = None


def _get_index() -> HybridDocsIndex:
    """Return the process-level singleton, creating it on first call."""
    global _hybrid_index
    if _hybrid_index is None:
        _hybrid_index = HybridDocsIndex(
            docs_dir=DOCS_DIR,
            chroma_persist_dir=settings.chroma_persist_dir,
            api_key=settings.openrouter_api_key,
        )
    return _hybrid_index


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_docs(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Hybrid (keyword + vector) search over the engineering markdown docs.

    On first invocation the docs are chunked, embedded, and stored in
    ChromaDB + SQLite.  Subsequent calls reuse the persisted index; changed
    files are automatically re-indexed via SHA-256 fingerprinting.

    Args:
        query:       Natural-language or keyword query string.
        max_results: Maximum number of chunk results to return (default 5).

    Returns:
        {
            "query": str,
            "count": int,
            "results": [
                {
                    "filename": str,
                    "title": str,
                    "chunk_index": int,
                    "text": str,          # the actual chunk text
                    "keyword_score": float,
                    "vector_score": float,
                    "hybrid_score": float,
                },
                ...
            ]
        }
    """
    if not query or not query.strip():
        return {"query": query, "count": 0, "results": []}

    try:
        index = _get_index()
        index.ensure_indexed()
        hits = index.search(query, k=max_results)
    except Exception as exc:
        logger.error("search_docs: HybridDocsIndex failed (%s)", exc)
        hits = []

    return {
        "query": query,
        "count": len(hits),
        "results": hits,
    }
