# infer.py (ONNX, robust local loading)
from transformers import AutoTokenizer
import onnxruntime as ort
import numpy as np, json, os, sys
from pathlib import Path

def _resource_path(rel_path: str | os.PathLike) -> Path:
    # Works in both source and PyInstaller EXE
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return (base / rel_path).resolve()
 
class PiiModel:
    def __init__(self, model_dir="model", thresholds=None, batch_size=8):
        # If model_dir is absolute, use it as-is; else resolve relative to app/EXE
        mdir = Path(model_dir)
        self.model_dir = mdir if mdir.is_absolute() else _resource_path(mdir)
        # Force local files only (no internet)
        self.tok = AutoTokenizer.from_pretrained(str(self.model_dir), use_fast=True, local_files_only=True)
        model_path = self.model_dir / "model.onnx"
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        with open(self.model_dir / "id2label.json", "r", encoding="utf-8") as f:
            self.id2label = {int(k): v for k, v in json.load(f).items()}
        self.thresholds = thresholds or {}
        self.batch_size = batch_size

    def predict(self, text: str):
        enc = self.tok(text, return_offsets_mapping=True, truncation=True, max_length=4096)
        inputs = {
            "input_ids": np.array([enc["input_ids"]], dtype=np.int64),
            "attention_mask": np.array([enc["attention_mask"]], dtype=np.int64),
        }
        (logits,) = self.session.run(None, inputs)
        probs = (np.exp(logits) / np.exp(logits).sum(-1, keepdims=True))[0]
        findings = []
        for i, (start, end) in enumerate(enc["offset_mapping"]):
            if end <= start:
                continue
            lab_id = int(np.argmax(probs[i])); score = float(probs[i, lab_id])
            lab = self.id2label.get(lab_id, "O")
            if lab != "O" and score >= self.thresholds.get(lab, 0.5):
                findings.append({"start": int(start), "end": int(end), "label": lab, "score": round(score, 4)})
        return findings
