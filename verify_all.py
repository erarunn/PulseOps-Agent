"""
verify_all.py — Comprehensive reverification of hybrid RAG pipeline.
Run with: python verify_all.py
"""
import sys
import traceback

PASS = []
FAIL = []


def check(label, fn):
    try:
        fn()
        PASS.append(label)
        print(f"  [PASS] {label}")
    except Exception:
        FAIL.append(label)
        print(f"  [FAIL] {label}")
        traceback.print_exc()


# ── 1. Config fields ─────────────────────────────────────────────────────────
def test_config():
    from app.config import settings, DOCS_DIR, CHROMA_DIR

    assert CHROMA_DIR.name == "chroma_store", f"unexpected CHROMA_DIR: {CHROMA_DIR}"
    assert settings.chroma_persist_dir == CHROMA_DIR
    assert settings.openrouter_embed_model == "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    assert settings.hybrid_keyword_weight == 0.4
    assert settings.hybrid_vector_weight == 0.6
    assert settings.chunk_max_chars == 600
    assert settings.chunk_overlap_chars == 100
    print(f"       CHROMA_DIR = {CHROMA_DIR}")
    print(f"       embed_model = {settings.openrouter_embed_model}")


check("config: new fields present & correct defaults", test_config)


# ── 2. SQLite schema ──────────────────────────────────────────────────────────
def test_schema():
    from app.db.database import init_db, get_connection

    init_db()
    conn = get_connection()

    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    assert "doc_chunks" in tables, f"doc_chunks not found; tables={tables}"

    indexes = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    ]
    assert "idx_doc_chunks_filename" in indexes, (
        f"idx_doc_chunks_filename missing; indexes={indexes}"
    )

    # Verify column names
    cols = [
        r[1]
        for r in conn.execute("PRAGMA table_info(doc_chunks)").fetchall()
    ]
    expected = {"id", "filename", "title", "chunk_index", "text", "file_fingerprint", "indexed_at"}
    missing = expected - set(cols)
    assert not missing, f"Missing columns: {missing}"
    conn.close()
    print(f"       tables: {tables}")
    print(f"       doc_chunks cols: {cols}")


check("database: doc_chunks table + index + columns", test_schema)


# ── 3. DocChunkModel ──────────────────────────────────────────────────────────
def test_model():
    from app.db.models import DocChunkModel

    m = DocChunkModel(
        id="test-id",
        filename="foo.md",
        title="Foo Title",
        chunk_index=2,
        text="Some chunk text here",
        file_fingerprint="deadbeef",
        indexed_at="2026-01-01T00:00:00+00:00",
    )
    assert m.id == "test-id"
    assert m.chunk_index == 2
    assert m.file_fingerprint == "deadbeef"


check("models: DocChunkModel fields & types", test_model)


# ── 4. DocChunkRepository round-trip ─────────────────────────────────────────
def test_repo():
    from app.db.database import init_db
    from app.db.repository import DocChunkRepository

    init_db()

    fake_chunks = [
        {
            "id": "verify.md::chunk-0",
            "filename": "verify.md",
            "title": "Verify Test",
            "chunk_index": 0,
            "text": "First chunk for verification",
        },
        {
            "id": "verify.md::chunk-1",
            "filename": "verify.md",
            "title": "Verify Test",
            "chunk_index": 1,
            "text": "Second chunk for verification",
        },
    ]
    fingerprints = {"verify.md": "sha256-abc123"}

    # First upsert
    saved = DocChunkRepository.upsert_chunks(fake_chunks, fingerprints)
    assert len(saved) == 2, f"Expected 2 saved, got {len(saved)}"

    # Re-upsert should REPLACE not duplicate
    DocChunkRepository.upsert_chunks(fake_chunks, fingerprints)
    fetched = DocChunkRepository.get_chunks_by_filename("verify.md")
    assert len(fetched) == 2, f"Expected 2 chunks, got {len(fetched)} (duplicate bug?)"
    assert fetched[0].chunk_index == 0
    assert fetched[1].chunk_index == 1
    assert fetched[0].file_fingerprint == "sha256-abc123"

    # list_indexed_files summary
    listing = DocChunkRepository.list_indexed_files()
    entry = next((r for r in listing if r["filename"] == "verify.md"), None)
    assert entry is not None, "verify.md not in listing"
    assert entry["chunk_count"] == 2

    print(f"       upsert/get/list all consistent — 2 chunks for verify.md")

    # Cleanup test data
    from app.db.database import get_connection
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM doc_chunks WHERE filename = 'verify.md'")
    conn.close()


check("repository: DocChunkRepository upsert->dedup->get->list", test_repo)


# ── 5. Markdown chunker — all 8 docs ─────────────────────────────────────────
def test_chunker():
    from app.tools.embeddings import _chunk_markdown
    import pathlib

    docs = sorted(pathlib.Path("data/docs").glob("*.md"))
    assert len(docs) == 8, f"Expected 8 docs, found {len(docs)}"

    total = 0
    for md in docs:
        content = md.read_text(encoding="utf-8")
        chunks = _chunk_markdown(md.name, content)
        assert len(chunks) >= 1, f"{md.name} produced 0 chunks"
        for c in chunks:
            assert "id" in c and "text" in c and "filename" in c and "chunk_index" in c
            assert len(c["text"]) > 0
            assert c["id"].startswith(md.name)
        total += len(chunks)
        print(f"       {md.name}: {len(chunks)} chunk(s)")

    print(f"       TOTAL: {len(docs)} docs → {total} chunks")


check("embeddings: _chunk_markdown all 8 docs", test_chunker)


# ── 6. HybridDocsIndex — keyword-only fallback (no API key) ──────────────────
def test_keyword_only():
    from app.tools.embeddings import HybridDocsIndex
    from app.config import DOCS_DIR, CHROMA_DIR

    idx = HybridDocsIndex(
        docs_dir=DOCS_DIR,
        chroma_persist_dir=CHROMA_DIR / "test_keyword_only",
        api_key="",  # empty → triggers keyword-only fallback
    )
    idx.ensure_indexed()

    results = idx.search("P1 critical incident severity", k=3)
    assert isinstance(results, list)
    for r in results:
        assert "filename" in r
        assert "text" in r
        assert "hybrid_score" in r
        assert "keyword_score" in r

    if results:
        best = results[0]
        print(f"       top hit: {best['filename']}  hybrid={best['hybrid_score']}")
    else:
        print("       no results (keyword fallback active, no embeddings)")


check("embeddings: HybridDocsIndex keyword-only (no API key fallback)", test_keyword_only)


# ── 7. search_docs public API ─────────────────────────────────────────────────
def test_search_facade():
    from app.tools.search import search_docs

    # Non-empty query
    result = search_docs("P1 rollback checkout incident")
    assert isinstance(result, dict)
    assert "query" in result
    assert "count" in result
    assert "results" in result
    assert isinstance(result["results"], list)
    print(f"       returned {result['count']} result(s)")

    if result["results"]:
        r = result["results"][0]
        required_keys = {"filename", "title", "text", "keyword_score", "vector_score", "hybrid_score"}
        missing = required_keys - set(r.keys())
        assert not missing, f"Result missing keys: {missing}"

    # Empty query guard
    empty = search_docs("")
    assert empty["count"] == 0


check("search: search_docs facade (response shape + empty guard)", test_search_facade)


# ── 8. Tool registry wiring ───────────────────────────────────────────────────
def test_registry():
    from app.tools.registry import execute_tool

    out = execute_tool("search_docs", {"query": "oncall runbook P2 incident"})
    assert "error" not in out, f"Registry returned error: {out}"
    assert "results" in out
    assert "count" in out
    print(f"       registry search returned {out['count']} result(s)")


check("registry: execute_tool('search_docs') wired to hybrid", test_registry)


# ── 9. Ingest CLI importable + callable ──────────────────────────────────────
def test_ingest():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ingest", "app/ingest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert callable(getattr(mod, "cmd_status", None)), "cmd_status not found"
    assert callable(getattr(mod, "cmd_index", None)), "cmd_index not found"
    assert callable(getattr(mod, "main", None)), "main not found"

    # cmd_status should run without error
    mod.cmd_status()


check("ingest: CLI module importable + cmd_status runs", test_ingest)


# ── 10. requirements.txt ──────────────────────────────────────────────────────
def test_requirements():
    reqs = open("requirements.txt").read()
    assert "chromadb" in reqs, "chromadb missing from requirements.txt"
    assert "numpy" in reqs, "numpy missing from requirements.txt"

    import chromadb
    import numpy
    print(f"       chromadb={chromadb.__version__}  numpy={numpy.__version__}")


check("requirements: chromadb + numpy installed", test_requirements)


# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 55)
print(f"  PASSED : {len(PASS)} / {len(PASS) + len(FAIL)}")
if FAIL:
    print(f"  FAILED : {FAIL}")
    sys.exit(1)
else:
    print("  STATUS : ALL CHECKS PASSED ✓")
print("=" * 55)
