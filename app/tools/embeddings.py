"""
Embedding & Vector-Store layer for PulseOps docs.

Architecture
------------
* OpenRouter is used as the embedding provider.
  Model: nvidia/llama-nemotron-embed-vl-1b-v2:free
  Endpoint: POST https://openrouter.ai/api/v1/embeddings  (OpenAI-compatible)

* ChromaDB runs fully embedded (no server) and persists its data to
  <project_root>/data/chroma_store/ so embeddings survive restarts.

* Lazy indexing: on first call (or when docs change) the engine computes
  embeddings for every chunk and upserts them into ChromaDB.
  Change detection is done via a SHA-256 fingerprint of each file's content.

* Chunking strategy: sliding window over markdown paragraphs.
  Each "chunk" is a heading + the paragraph(s) that follow it, capped at
  CHUNK_MAX_CHARS characters, with CHUNK_OVERLAP_CHARS of overlap.

* The public API is `HybridDocsIndex` which exposes:
    index_docs(docs_dir)  – build / refresh the index
    search(query, k)      – return top-k chunks via hybrid retrieval
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
from app.db.repository import DocChunkRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration knobs (all overridable via env vars)
# ---------------------------------------------------------------------------
CHUNK_MAX_CHARS: int = int(os.getenv("CHUNK_MAX_CHARS", "600"))
CHUNK_OVERLAP_CHARS: int = int(os.getenv("CHUNK_OVERLAP_CHARS", "100"))
EMBED_BATCH_SIZE: int = int(os.getenv("EMBED_BATCH_SIZE", "16"))
OPENROUTER_EMBED_MODEL: str = os.getenv(
    "OPENROUTER_EMBED_MODEL", "nvidia/llama-nemotron-embed-vl-1b-v2:free"
)

# Embedding endpoint — defaults to real OpenRouter so it works even when the
# LLM base URL points at Groq / another provider that lacks /embeddings.
# Override EMBED_BASE_URL in .env if you have a different embedding provider.
EMBED_BASE_URL: str = os.getenv(
    "EMBED_BASE_URL",
    os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
)
# EMBED_API_KEY falls back to OPENROUTER_API_KEY so existing configs keep working.
EMBED_API_KEY: str = os.getenv(
    "EMBED_API_KEY",
    os.getenv("OPENROUTER_API_KEY", ""),
)

# Hybrid fusion weights (must sum to 1.0)
HYBRID_KEYWORD_WEIGHT: float = float(os.getenv("HYBRID_KEYWORD_WEIGHT", "0.4"))
HYBRID_VECTOR_WEIGHT: float = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.6"))


# ---------------------------------------------------------------------------
# Markdown chunker
# ---------------------------------------------------------------------------

def _chunk_markdown(filename: str, content: str) -> List[Dict[str, Any]]:
    """
    Split a markdown document into overlapping chunks.

    Strategy:
    1. Split on double-newlines (paragraph boundaries).
    2. Accumulate paragraphs into a chunk until CHUNK_MAX_CHARS is reached.
    3. Store the last CHUNK_OVERLAP_CHARS of each chunk as the start of the next.
    4. Each chunk carries metadata: source filename, title, chunk index.
    """
    # Extract document title from first H1
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(filename).stem

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    chunks: List[Dict[str, Any]] = []
    current = ""
    chunk_idx = 0

    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= CHUNK_MAX_CHARS:
            current = candidate
        else:
            if current:
                chunks.append({
                    "id": f"{filename}::chunk-{chunk_idx}",
                    "filename": filename,
                    "title": title,
                    "chunk_index": chunk_idx,
                    "text": current,
                })
                chunk_idx += 1
                # Carry overlap from the tail of the previous chunk
                overlap = current[-CHUNK_OVERLAP_CHARS:] if CHUNK_OVERLAP_CHARS > 0 else ""
                current = (overlap + "\n\n" + para).strip() if overlap else para
            else:
                # Single paragraph larger than CHUNK_MAX_CHARS — hard-split
                for i in range(0, len(para), CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS):
                    sub = para[i : i + CHUNK_MAX_CHARS]
                    chunks.append({
                        "id": f"{filename}::chunk-{chunk_idx}",
                        "filename": filename,
                        "title": title,
                        "chunk_index": chunk_idx,
                        "text": sub,
                    })
                    chunk_idx += 1
                current = ""

    # Flush remaining
    if current:
        chunks.append({
            "id": f"{filename}::chunk-{chunk_idx}",
            "filename": filename,
            "title": title,
            "chunk_index": chunk_idx,
            "text": current,
        })

    return chunks


# ---------------------------------------------------------------------------
# OpenRouter embedding client
# ---------------------------------------------------------------------------

class OpenRouterEmbedder:
    """
    Thin wrapper around an OpenAI-compatible /embeddings endpoint.

    By default targets real OpenRouter (https://openrouter.ai/api/v1) so that
    embedding works even when the LLM is routed to a different provider (e.g.
    Groq) that may not expose an /embeddings endpoint.

    Override via env vars:
      EMBED_BASE_URL  — embedding API base URL  (default: OPENROUTER_BASE_URL or openrouter.ai)
      EMBED_API_KEY   — embedding API key        (default: OPENROUTER_API_KEY)
      OPENROUTER_EMBED_MODEL — model name        (default: nvidia/llama-nemotron-embed-vl-1b-v2:free)
    """

    def __init__(
        self,
        api_key: str,
        model: str = OPENROUTER_EMBED_MODEL,
        base_url: str = EMBED_BASE_URL,
    ):
        # Prefer the dedicated EMBED_API_KEY; fall back to passed-in api_key
        effective_key = EMBED_API_KEY or api_key
        if not effective_key:
            raise ValueError(
                "No embedding API key found. Set EMBED_API_KEY (or OPENROUTER_API_KEY) "
                "in your .env file."
            )
        self.model = model
        self._headers = {
            "Authorization": f"Bearer {effective_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/PulseOps",
            "X-Title": "PulseOps",
        }
        self._base_url = base_url.rstrip("/")
        logger.debug(
            "OpenRouterEmbedder: model=%s  base_url=%s", self.model, self._base_url
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts in batches. Returns a list of float vectors.
        Raises on HTTP error so callers can decide whether to fallback.
        """
        all_embeddings: List[List[float]] = []
        for batch_start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[batch_start : batch_start + EMBED_BATCH_SIZE]
            payload = {"model": self.model, "input": batch}
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/embeddings",
                    headers=self._headers,
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
            # OpenAI format: {"data": [{"embedding": [...], "index": N}, ...]}
            sorted_items = sorted(data["data"], key=lambda x: x["index"])
            all_embeddings.extend([item["embedding"] for item in sorted_items])
        return all_embeddings


# ---------------------------------------------------------------------------
# Hybrid index
# ---------------------------------------------------------------------------

class HybridDocsIndex:
    """
    Manages chunking, embedding, and hybrid retrieval for the docs corpus.

    Hybrid retrieval combines:
    - **Keyword score** (BM25-style TF term matching, same as the original engine)
    - **Vector score**  (cosine similarity via ChromaDB)
    Both scores are normalised to [0, 1] then combined as a weighted sum.
    """

    _COLLECTION_NAME = "pulseops_docs"
    _FINGERPRINT_FILE = "fingerprints.json"

    def __init__(
        self,
        docs_dir: Path,
        chroma_persist_dir: Path,
        api_key: str,
    ):
        self.docs_dir = docs_dir
        self.chroma_persist_dir = chroma_persist_dir
        self.api_key = api_key
        self._chunks: List[Dict[str, Any]] = []  # in-memory chunk metadata
        self._collection = None  # ChromaDB collection (lazy-initialised)
        self._embedder: Optional[OpenRouterEmbedder] = None
        self._ready = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_indexed(self) -> None:
        """Index docs if the index is empty or any doc file has changed."""
        if self._ready:
            return
        self._init_chroma()
        changed_files, current_fingerprints = self._detect_changes()
        if changed_files:
            logger.info(
                "DocIndex: %d doc(s) changed/new → re-indexing: %s",
                len(changed_files),
                changed_files,
            )
            self._index_files(changed_files, current_fingerprints)
        else:
            logger.info("DocIndex: all docs up-to-date, loading metadata from ChromaDB.")
            self._load_chunk_metadata_from_chroma()
        self._ready = True

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search: keyword + vector, fused via weighted sum.
        Returns up to *k* result dicts with keys:
          filename, title, chunk_index, text, keyword_score, vector_score, hybrid_score
        """
        if not self._ready:
            self.ensure_indexed()

        if not self._chunks:
            return []

        # --- Keyword scoring ---
        keyword_scores = self._keyword_score(query)

        # --- Vector scoring ---
        vector_scores = self._vector_score(query, len(self._chunks))

        # --- Fuse ---
        results = []
        for i, chunk in enumerate(self._chunks):
            ks = keyword_scores.get(i, 0.0)
            vs = vector_scores.get(i, 0.0)
            hybrid = HYBRID_KEYWORD_WEIGHT * ks + HYBRID_VECTOR_WEIGHT * vs
            if hybrid > 0:
                results.append({
                    "filename": chunk["filename"],
                    "title": chunk["title"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "keyword_score": round(ks, 4),
                    "vector_score": round(vs, 4),
                    "hybrid_score": round(hybrid, 4),
                })

        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return results[:k]

    # ------------------------------------------------------------------
    # Internal: ChromaDB setup
    # ------------------------------------------------------------------

    def _init_chroma(self) -> None:
        try:
            import chromadb  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "chromadb is required for vector search. "
                "Install it with: pip install chromadb"
            ) from exc

        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.chroma_persist_dir))
        self._collection = client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Internal: change detection
    # ------------------------------------------------------------------

    def _fingerprint_path(self) -> Path:
        return self.chroma_persist_dir / self._FINGERPRINT_FILE

    def _load_fingerprints(self) -> Dict[str, str]:
        fp = self._fingerprint_path()
        if fp.exists():
            try:
                return json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_fingerprints(self, fingerprints: Dict[str, str]) -> None:
        self._fingerprint_path().write_text(
            json.dumps(fingerprints, indent=2), encoding="utf-8"
        )

    def _detect_changes(self) -> Tuple[List[Path], Dict[str, str]]:
        """
        Return (list_of_changed_files, current_fingerprint_dict).
        A file is "changed" if it is new or its SHA-256 differs from the stored fingerprint.
        """
        stored = self._load_fingerprints()
        current: Dict[str, str] = {}
        changed: List[Path] = []

        if not self.docs_dir.exists():
            return [], current

        for file_path in sorted(self.docs_dir.glob("*.md")):
            content = file_path.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            current[file_path.name] = sha
            if stored.get(file_path.name) != sha:
                changed.append(file_path)

        # Also flag changes if ChromaDB collection is empty
        if self._collection is not None and self._collection.count() == 0:
            changed = list(self.docs_dir.glob("*.md"))
            current = {
                f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                for f in changed
            }

        return changed, current

    # ------------------------------------------------------------------
    # Internal: indexing
    # ------------------------------------------------------------------

    def _get_embedder(self) -> OpenRouterEmbedder:
        if self._embedder is None:
            self._embedder = OpenRouterEmbedder(api_key=self.api_key)
        return self._embedder

    def _index_files(
        self, file_paths: List[Path], current_fingerprints: Dict[str, str]
    ) -> None:
        """Chunk, embed, and upsert changed files into ChromaDB."""
        # Remove stale chunks for changed files
        changed_filenames = [p.name for p in file_paths]
        existing = self._collection.get(where={"filename": {"$in": changed_filenames}})
        if existing and existing.get("ids"):
            self._collection.delete(ids=existing["ids"])

        # Build new chunks
        new_chunks: List[Dict[str, Any]] = []
        for file_path in file_paths:
            content = file_path.read_text(encoding="utf-8")
            new_chunks.extend(_chunk_markdown(file_path.name, content))

        if not new_chunks:
            logger.warning("DocIndex: no chunks produced from changed files.")
            self._save_fingerprints(current_fingerprints)
            return

        # Embed
        texts = [c["text"] for c in new_chunks]
        logger.info("DocIndex: embedding %d chunks via OpenRouter…", len(texts))
        try:
            embedder = self._get_embedder()
            vectors = embedder.embed(texts)
        except Exception as exc:
            logger.error(
                "DocIndex: embedding failed (%s). Falling back to keyword-only search.", exc
            )
            # Still load metadata so keyword search works
            self._chunks = new_chunks + [
                c for c in self._chunks
                if c["filename"] not in changed_filenames
            ]
            return

        # Upsert into ChromaDB
        self._collection.upsert(
            ids=[c["id"] for c in new_chunks],
            embeddings=vectors,
            documents=texts,
            metadatas=[
                {
                    "filename": c["filename"],
                    "title": c["title"],
                    "chunk_index": c["chunk_index"],
                }
                for c in new_chunks
            ],
        )

        # Mirror chunk metadata into SQLite for audit / fast lookup
        try:
            DocChunkRepository.upsert_chunks(new_chunks, current_fingerprints)
        except Exception as db_exc:
            logger.warning(
                "DocIndex: failed to mirror chunks to SQLite (%s) — ChromaDB index is still valid.",
                db_exc,
            )

        # Merge in-memory chunk list
        self._chunks = new_chunks + [
            c for c in self._chunks
            if c["filename"] not in changed_filenames
        ]

        self._save_fingerprints(current_fingerprints)
        logger.info("DocIndex: indexed %d chunks into ChromaDB.", len(new_chunks))

    def _load_chunk_metadata_from_chroma(self) -> None:
        """Reload chunk metadata from ChromaDB (used when no docs changed)."""
        if self._collection is None:
            return
        result = self._collection.get(include=["metadatas", "documents"])
        self._chunks = []
        if not result or not result.get("ids"):
            return
        for cid, meta, doc in zip(
            result["ids"], result["metadatas"], result["documents"]
        ):
            self._chunks.append({
                "id": cid,
                "filename": meta["filename"],
                "title": meta["title"],
                "chunk_index": meta["chunk_index"],
                "text": doc,
            })

    # ------------------------------------------------------------------
    # Internal: keyword scoring (BM25-style TF)
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b\w{3,}\b", text)]

    def _keyword_score(self, query: str) -> Dict[int, float]:
        """
        Returns a dict {chunk_index_in_self._chunks: normalised_score}.
        Score is normalised to [0, 1] by dividing by the max raw score.
        """
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return {}

        raw: Dict[int, float] = {}
        for i, chunk in enumerate(self._chunks):
            doc_tokens = self._tokenize(chunk["text"])
            score = 0.0
            for qt in q_tokens:
                count = doc_tokens.count(qt)
                if count > 0:
                    score += 1.0 + count * 0.2
                    if qt in chunk["filename"].lower() or qt in chunk["title"].lower():
                        score += 3.0
            if score > 0:
                raw[i] = score

        if not raw:
            return {}
        max_score = max(raw.values())
        return {i: s / max_score for i, s in raw.items()}

    # ------------------------------------------------------------------
    # Internal: vector scoring
    # ------------------------------------------------------------------

    def _vector_score(self, query: str, n_chunks: int) -> Dict[int, float]:
        """
        Embeds the query and queries ChromaDB for cosine similarity scores.
        Returns a dict {chunk_index_in_self._chunks: normalised_score [0,1]}.

        ChromaDB with hnsw:space=cosine returns *distances* in [0, 2] where
        0 = identical. We convert to similarity = 1 - distance/2.
        """
        if self._collection is None or self._collection.count() == 0:
            return {}

        try:
            embedder = self._get_embedder()
            query_vec = embedder.embed([query])[0]
        except Exception as exc:
            logger.warning("DocIndex: query embedding failed (%s) → skipping vector score.", exc)
            return {}

        n_results = min(n_chunks, self._collection.count())
        try:
            result = self._collection.query(
                query_embeddings=[query_vec],
                n_results=n_results,
                include=["metadatas", "distances"],
            )
        except Exception as exc:
            logger.warning("DocIndex: ChromaDB query failed (%s) → skipping vector score.", exc)
            return {}

        # Build a lookup: chunk_id → position in self._chunks
        id_to_idx = {c["id"]: i for i, c in enumerate(self._chunks)}

        scores: Dict[int, float] = {}
        ids_list = result.get("ids", [[]])[0]
        distances_list = result.get("distances", [[]])[0]

        for cid, dist in zip(ids_list, distances_list):
            if cid in id_to_idx:
                similarity = 1.0 - (dist / 2.0)  # convert cosine distance → similarity
                similarity = max(0.0, min(1.0, similarity))
                scores[id_to_idx[cid]] = similarity

        return scores
