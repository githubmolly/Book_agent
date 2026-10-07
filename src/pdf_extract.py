"""Extract clean text from a PDF, one chapter or section at a time."""
import fitz  # PyMuPDF
from pathlib import Path


def extract_pdf(pdf_path: str) -> list[dict]:
    """Return a list of {page, text} dicts, one per page."""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():  # skip blank pages
            pages.append({"page": i, "text": text})
    doc.close()
    return pages


if __name__ == "__main__":
    pages = extract_pdf("data/ai_engineering.pdf")
    print(f"Extracted {len(pages)} non-blank pages")
    print(f"\nFirst page preview:\n{pages[0]['text'][:400]}...")


def chunk_pages(pages: list[dict], chunk_size: int = 1000, overlap: int = 150) -> list[dict]:
    """Split pages into overlapping chunks. Keep page number metadata."""
    chunks = []
    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page"]
        
        # Slide a window across the text
        start = 0
        chunk_idx = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            
            if len(chunk_text.strip()) > 100:  # skip tiny fragments
                chunks.append({
                    "chunk_id": f"p{page_num}_c{chunk_idx}",
                    "page": page_num,
                    "text": chunk_text.strip(),
                })
                chunk_idx += 1
            
            start += chunk_size - overlap
    
    return chunks