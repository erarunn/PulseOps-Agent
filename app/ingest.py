"""
ingest.py — One-shot CLI to pre-index all docs in data/docs/*.md

Run once (or after any doc change) to warm the ChromaDB vector store and
populate the SQLite doc_chunks table before the API server starts.

Usage:
    python -m app.ingest            # index all docs
    python -m app.ingest --force    # force re-index even if fingerprints match
    python -m app.ingest --status   # show current index status from SQLite
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pulseops.ingest")


def cmd_index(force: bool = False) -> None:
    from app.config import settings, DOCS_DIR
    from app.tools.embeddings import HybridDocsIndex

    if not settings.openrouter_api_key:
        logger.error(
            "OPENROUTER_API_KEY is not set. Export it or add it to .env. "
            "Embedding is required for vector search."
        )
        sys.exit(1)

    if not DOCS_DIR.exists():
        logger.error("Docs directory not found: %s", DOCS_DIR)
        sys.exit(1)

    md_files = list(DOCS_DIR.glob("*.md"))
    if not md_files:
        logger.warning("No .md files found in %s", DOCS_DIR)
        return

    logger.info("Found %d markdown file(s) in %s", len(md_files), DOCS_DIR)

    index = HybridDocsIndex(
        docs_dir=DOCS_DIR,
        chroma_persist_dir=settings.chroma_persist_dir,
        api_key=settings.openrouter_api_key,
    )

    if force:
        # Wipe fingerprints so all files are treated as changed
        fp_file = settings.chroma_persist_dir / "fingerprints.json"
        if fp_file.exists():
            fp_file.unlink()
            logger.info("Force mode: cleared fingerprint cache.")

    index.ensure_indexed()

    # Report what was stored
    from app.db.repository import DocChunkRepository
    summary = DocChunkRepository.list_indexed_files()
    if summary:
        total_chunks = sum(r["chunk_count"] for r in summary)
        logger.info(
            "Index complete. %d file(s), %d chunk(s) total.", len(summary), total_chunks
        )
        for row in summary:
            logger.info(
                "  %-40s %3d chunk(s)   indexed_at=%s",
                row["filename"],
                row["chunk_count"],
                row["indexed_at"],
            )
    else:
        logger.info("Index complete (SQLite mirror empty — ChromaDB may still be populated).")


def cmd_status() -> None:
    from app.db.repository import DocChunkRepository

    summary = DocChunkRepository.list_indexed_files()
    if not summary:
        print("No chunks indexed yet. Run `python -m app.ingest` to build the index.")
        return

    total = sum(r["chunk_count"] for r in summary)
    print(f"\n{'Filename':<42} {'Chunks':>6}  {'Indexed At'}")
    print("-" * 72)
    for row in summary:
        print(f"  {row['filename']:<40} {row['chunk_count']:>6}  {row['indexed_at']}")
    print("-" * 72)
    print(f"  {'TOTAL':<40} {total:>6}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="PulseOps doc ingestion CLI")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-index all docs, ignoring cached fingerprints.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print index status from SQLite and exit (no re-indexing).",
    )
    args = parser.parse_args()

    # Ensure DB tables exist before any repository call
    from app.db.database import init_db
    init_db()

    if args.status:
        cmd_status()
    else:
        cmd_index(force=args.force)


if __name__ == "__main__":
    main()
