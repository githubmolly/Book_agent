"""BM25 keyword search over book chunks."""
import re
import json
import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi

from src.pdf_extract import extract_pdf, chunk_pages

# Compute the project root from THIS file's location.
# src/knowledge_base.py lives inside src/, which lives inside the project root.
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX_DIR = _PACKAGE_ROOT / "data" / "index"

def tokenize(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def build_index(pdf_path: str, out_dir: Path | str | None = None):
    """Extract, chunk, and build BM25 index. Save to disk."""
    out = Path(out_dir) if out_dir else DEFAULT_INDEX_DIR
    out.mkdir(parents=True, exist_ok=True)
    
    print("Extracting PDF...")
    pages = extract_pdf(pdf_path)
    
    print("Chunking...")
    chunks = chunk_pages(pages)
    print(f"  {len(chunks)} chunks from {len(pages)} pages")
    
    print("Building BM25 index...")
    tokenized = [tokenize(c["text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    
    # Save chunks as JSON (human-readable, easy to inspect)
    (out / "chunks.json").write_text(json.dumps(chunks, indent=2))
    
    # Save BM25 as pickle (binary, but fast to reload)
    with open(out / "bm25.pkl", "wb") as f:
        pickle.dump(bm25, f)
    
    print(f"✓ Saved to {out}/")
    return chunks, bm25


class KnowledgeBase:
    """Load an existing index and provide a search interface."""
    
    def __init__(self, index_dir: Path | str | None = None):
        idx = Path(index_dir) if index_dir else DEFAULT_INDEX_DIR
        self.chunks = json.loads((idx / "chunks.json").read_text())
        with open(idx / "bm25.pkl", "rb") as f:
            self.bm25 = pickle.load(f)
        
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return the top-k most relevant chunks."""
        scores = self.bm25.get_scores(tokenize(query))
        top_indices = scores.argsort()[::-1][:top_k]
        return [
            {**self.chunks[i], "score": float(scores[i])}
            for i in top_indices
        ]


if __name__ == "__main__":
    build_index("data/ai_engineering.pdf")