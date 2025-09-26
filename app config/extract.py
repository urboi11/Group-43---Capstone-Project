# extract.py
from pathlib import Path
from docx import Document
from PyPDF2 import PdfReader

def read_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")

def read_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def read_pdf(path: str) -> str:
    try:
        pdf = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""  # unreadable PDFs just return empty
