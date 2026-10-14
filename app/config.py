import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
CHROMA_DIR = DATA_DIR / "chroma_store"

def _load_dotenv():
    """Minimal .env loader — reads KEY=VALUE lines from .env in project root."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

_load_dotenv()

class Settings(BaseModel):
    # LLM Settings
    llm_mode: str = os.getenv("LLM_MODE", "mock").lower()
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Database
    db_path: Path = BASE_DIR / "pulseops.db"

    # Vector store (ChromaDB) — persists embeddings across restarts
    chroma_persist_dir: Path = CHROMA_DIR

    # Embedding model (via OpenRouter)
    openrouter_embed_model: str = os.getenv(
        "OPENROUTER_EMBED_MODEL", "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    )

    # Hybrid retrieval weights (keyword + vector; must sum to 1.0)
    hybrid_keyword_weight: float = float(os.getenv("HYBRID_KEYWORD_WEIGHT", "0.4"))
    hybrid_vector_weight: float = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.6"))

    # Chunking knobs
    chunk_max_chars: int = int(os.getenv("CHUNK_MAX_CHARS", "600"))
    chunk_overlap_chars: int = int(os.getenv("CHUNK_OVERLAP_CHARS", "100"))

    # App
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Agent execution limits
    max_agent_steps: int = 5

settings = Settings()
