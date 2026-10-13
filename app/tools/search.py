import os
import re
from pathlib import Path
from typing import List, Dict, Any
from app.config import DOCS_DIR

def tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"\b\w{3,}\b", text)]

class DocsSearchEngine:
    def __init__(self, docs_dir: Path = DOCS_DIR):
        self.docs_dir = docs_dir
        self.documents: List[Dict[str, Any]] = []
        self._load_corpus()

    def _load_corpus(self):
        self.documents = []
        if not self.docs_dir.exists():
            return
        for file_path in self.docs_dir.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else file_path.stem
            tokens = tokenize(content)
            self.documents.append({
                "filename": file_path.name,
                "title": title,
                "content": content,
                "tokens": tokens,
            })

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        if not self.documents:
            self._load_corpus()
            
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        results = []
        for doc in self.documents:
            doc_tokens = doc["tokens"]
            score = 0.0
            # Term frequency / keyword matching
            for qt in q_tokens:
                count = doc_tokens.count(qt)
                if count > 0:
                    score += 1.0 + (count * 0.2)
                    if qt in doc["filename"].lower() or qt in doc["title"].lower():
                        score += 3.0

            if score > 0:
                # Find the most informative snippet — prefer paragraphs with actual content
                snippets = []
                paragraphs = [p.strip() for p in doc["content"].split("\n\n") if p.strip()]
                for para in paragraphs:
                    para_lower = para.lower()
                    # Skip very short lines or pure heading lines
                    if len(para) < 50 or para.startswith("#"):
                        continue
                    if any(qt in para_lower for qt in q_tokens):
                        snippets.append(para[:600])
                        if len(snippets) >= 3:
                            break

                # Fallback: use beginning of doc body (skip title line)
                if not snippets:
                    body_lines = [l for l in doc["content"].split("\n") if l.strip() and not l.startswith("#")]
                    snippets = ["\n".join(body_lines[:6])[:350]]

                snippet_text = "\n...\n".join(snippets)
                results.append({
                    "filename": doc["filename"],
                    "title": doc["title"],
                    "score": round(score, 2),
                    "snippet": snippet_text
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]

# Singleton instance
docs_engine = DocsSearchEngine()

def search_docs(query: str, max_results: int = 3) -> Dict[str, Any]:
    """Search internal engineering markdown docs by query keywords."""
    matches = docs_engine.search(query, max_results=max_results)
    return {
        "query": query,
        "count": len(matches),
        "results": matches
    }
