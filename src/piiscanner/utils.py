
from pathlib import Path
from docx import Document
from PyPDF2 import PdfReader
import os
import os, fnmatch, glob



# --- merge helpers ---
def _base_label(lbl: str) -> str:
    return lbl[2:] if lbl and (lbl.startswith("B-") or lbl.startswith("I-")) else lbl

def merge_findings(findings, max_gap=0):
    """
    Merge adjacent/overlapping findings with the same base label.
    - Strips BIO prefixes (B-/I-) to a plain label before merging.
    - Uses the max confidence of merged fragments.
    - max_gap: allow up to N chars gap between chunks to still merge (0 = only touching/overlap).
    """
    if not findings:
        return []

    # normalize & filter
    norm = []
    for f in findings:
        if not f or f.get("label") in (None, "O"):
            continue
        norm.append({
            "start": int(f["start"]),
            "end": int(f["end"]),
            "label": _base_label(f["label"]),
            "score": float(f.get("score", 0.0)),
        })

    if not norm:
        return []

    norm.sort(key=lambda x: (x["start"], x["end"]))
    merged = []
    cur = norm[0]
    for nxt in norm[1:]:
        same_label = (nxt["label"] == cur["label"])
        touching_or_gap = nxt["start"] <= cur["end"] + max_gap  # overlap or within gap
        if same_label and touching_or_gap:
            cur["end"] = max(cur["end"], nxt["end"])
            cur["score"] = max(cur["score"], nxt["score"])  # keep strongest score
        else:
            merged.append(cur)
            cur = nxt
    merged.append(cur)
    return merged

def iter_files(patterns, excludes):
    seen = set()
    for pat in patterns:
        for p in glob.iglob(pat, recursive=True):
            if any(fnmatch.fnmatch(p, ex) for ex in excludes):
                continue
            if os.path.isfile(p) and p not in seen:
                seen.add(p)
                yield p

def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        return read_txt(path)
    if ext == ".docx":
        return read_docx(path)
    if ext == ".pdf":
        return read_pdf(path)
    return ""  # unknown types ignored


def read_txt(path: str) -> str:
    try:
        if(os.path.getsize(path) == 0):
            return ""
        else:
            return Path(path).read_text(encoding="utf-8", errors="ignore")
    except:
        pass

def read_docx(path: str) -> str:
    try:
        if(os.path.getsize(path) == 0):
            return ""
        else:
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
    except:
        pass

def read_pdf(path: str) -> str:
    try:
        if(os.path.getsize(path) == 0):
            return ""
        else:
            pdf = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""  # unreadable PDFs just return empty