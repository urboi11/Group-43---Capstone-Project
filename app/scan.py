# scan.py
import sys
import argparse, json, os, fnmatch, glob, pathlib, time, yaml
from PySide6.QtWidgets import QApplication
from PiiScannerApp import MainWindow
from rich.progress import track
from extract import read_txt, read_docx, read_pdf
from infer import PiiModel

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

def main():
    app = QApplication([])
    
    window = MainWindow()
    
    window.show()
    
    sys.exit(app.exec())
    # ap = argparse.ArgumentParser()
    # ap.add_argument("--config", default="config.yaml")
    # ap.add_argument("--input", nargs="*", help="Optional explicit files/dirs to scan (overrides targets in config)")
    # ap.add_argument("--merge_gap", type=int, default=0, help="Max char gap to merge adjacent fragments")
    # args = ap.parse_args()


    #Test this config location to make sure that it works. 
    cfg = yaml.safe_load(open(os.getcwd() + "\config.yaml", "r", encoding="utf-8"))
    out_dir = pathlib.Path(cfg["output"]["path"])
    out_dir.mkdir(parents=True, exist_ok=True)

    model = PiiModel(
        model_dir=cfg.get("model_dir", "model"),
        thresholds=cfg.get("thresholds", {}),
        batch_size=cfg.get("batch_size", 8),
    )

    # Build file list
    # if args.input:
    # Verify that this logic works correctly
    if len(window.FileLineEdit.text()) > 0 or len(window.DirectoryLineEdit.text()) > 0:
        paths = []
        # for p in args.input:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                if any(fnmatch.fnmatch(root, ex) for ex in cfg.get("exclude_globs", [])):
                    continue
                for f in files:
                    paths.append(os.path.join(root, f))
        elif os.path.isfile(p):
            paths.append(p)
    else:
        #TODO: Work on this one, targets config property will not exist. 
        paths = list(iter_files(cfg.get("targets", []), cfg.get("exclude_globs", [])))

    for p in track(paths, description="Scanning"):
        try:
            text = read_any(p)
            if not text:
                continue
            findings = model.predict(text)
            merged = merge_findings(findings, max_gap=cfg.get("merge_gap", 0))
            if merged:
                record = {
                    "ts": time.time(),
                    "file": p,
                    "findings": merged,
                }
                (out_dir / (pathlib.Path(p).name + ".json")).write_text(
                    json.dumps(record, indent=2), encoding="utf-8"
                )
        except Exception:
            # In production: log errors to a file; for now, continue scanning next file.
            continue


if __name__ == "__main__":
    main()
