# evaluate_ner.py
# Evaluate a token classification (NER) model on the saved test split.
# Usage:
#   python pii-lab/scripts/evaluate_ner.py
# Optional args:
#   --model_dir  path to trained HF model dir (default: experiments/baseline/model)
#   --data_dir   path to prepared dataset dir (default: experiments/baseline/data)
#   --bsz        batch size for inference (default: 16)
#   --per_label  include per-label scores in output JSON

import os
import json
import argparse
from typing import Dict, List

import numpy as np
import torch
from datasets import load_from_disk
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
)
import evaluate


def to_py(o):
    """Convert NumPy types/arrays (and nested structures) into plain Python for json.dumps."""
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    if isinstance(o, dict):
        return {k: to_py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    return o


def chunk_indices(n_items: int, bsz: int):
    for i in range(0, n_items, bsz):
        yield range(i, min(i + bsz, n_items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", default="pii-lab/experiments/baseline/model")
    ap.add_argument("--data_dir",  default="pii-lab/experiments/baseline/data")
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--per_label", action="store_true")
    args = ap.parse_args()

    # Load dataset + label maps
    ds = load_from_disk(args.data_dir)
    test = ds["test"]

    with open(os.path.join(args.data_dir, "id2label.json"), "r", encoding="utf-8") as f:
        id2label: Dict[int, str] = {int(k): v for k, v in json.load(f).items()}

    # Model & tokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model_dir, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(args.model_dir).to(device)
    model.eval()

    # Collator pads inputs AND labels (labels -> -100 for padded positions)
    collator = DataCollatorForTokenClassification(tok)
    seqeval_metric = evaluate.load("seqeval")

    all_pred_tags: List[List[str]] = []
    all_true_tags: List[List[str]] = []

    for idx_range in chunk_indices(len(test), args.bsz):
        features = []
        for i in idx_range:
            ex = test[i]
            features.append({
                "input_ids": ex["input_ids"],
                "attention_mask": ex["attention_mask"],
                "labels": ex["labels"],
            })

        batch = collator(features)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].cpu().numpy()  # [B, T] with -100 on padding

        with torch.no_grad():
            logits = model(input_ids=input_ids, attention_mask=attention_mask).logits  # [B, T, C]
        preds = torch.argmax(logits, dim=-1).cpu().numpy()

        # Convert ids -> tag strings, skipping padded (-100) label positions
        for p_row, l_row in zip(preds, labels):
            pred_tags, true_tags = [], []
            for pid, lid in zip(p_row, l_row):
                if lid == -100:
                    continue  # ignore padding
                pred_tags.append(id2label[int(pid)])
                true_tags.append(id2label[int(lid)])
            all_pred_tags.append(pred_tags)
            all_true_tags.append(true_tags)

    results = seqeval_metric.compute(predictions=all_pred_tags, references=all_true_tags)
    if not args.per_label:
        results = {
            "overall_precision": results.get("overall_precision"),
            "overall_recall": results.get("overall_recall"),
            "overall_f1": results.get("overall_f1"),
            "overall_accuracy": results.get("overall_accuracy"),
        }

    print(json.dumps(to_py(results), indent=2))


if __name__ == "__main__":
    main()
