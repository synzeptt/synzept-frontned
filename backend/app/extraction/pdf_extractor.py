from typing import Optional
from .model import StructuredDocument

try:
    import PyPDF2
except Exception:
    PyPDF2 = None


def extract(pdf_bytes: bytes, url: Optional[str] = None) -> StructuredDocument:
    s = StructuredDocument()
    s.url = url
    if PyPDF2 is None:
        s.extraction_confidence = 0.0
        s.text = None
        s.word_count = 0
        return s

    try:
        reader = PyPDF2.PdfReader(pdf_bytes)
        pages_text = []
        for i, p in enumerate(reader.pages):
            try:
                t = p.extract_text() or ""
            except Exception:
                t = ""
            pages_text.append({"page": i + 1, "text": t})
            # naive headings: lines with uppercase
            for line in t.splitlines():
                if line.strip().isupper() and len(line.strip()) > 3:
                    s.headings.append(line.strip())

        full = "\n\n".join([p["text"] for p in pages_text])
        s.text = full
        s.word_count = len(full.split())
        s.estimated_reading_time = max(1, s.word_count // 200)
        s.extraction_confidence = 0.7
        return s
    except Exception:
        s.extraction_confidence = 0.0
        return s
