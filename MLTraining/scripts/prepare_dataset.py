# prepare_dataset.py
import json, argparse, os
from pathlib import Path
from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer

LABELS = ["O","B-PERSON","I-PERSON","B-DOB","I-DOB","B-ADDRESS","I-ADDRESS",
          "B-SSN","I-SSN","B-EMAIL","I-EMAIL","B-PHONE","I-PHONE",
          "B-CREDIT_CARD","I-CREDIT_CARD","B-IP_ADDRESS","I-IP_ADDRESS"]

def char_spans_to_bio(text, spans, tok, max_len=512):
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=max_len)
    tags = ["O"] * len(enc["offset_mapping"])

    # Make span list (start,end,label) safe
    norm = [(int(s["start"]), int(s["end"]), s["label"]) for s in spans]
    for i, (s, e) in enumerate(enc["offset_mapping"]):
        if e <= s:  # special tokens like CLS/SEP will be (0,0)
            continue
        covering = [lab for (a,b,lab) in norm if not (e <= a or b <= s)]
        if covering:
            # choose the one with max overlap
            a,b,lab = max(((a,b,lab) for (a,b,lab) in norm),
                          key=lambda x: max(0, min(e, x[1]) - max(s, x[0])) if not (e <= x[0] or x[1] <= s) else -1)
            # B/I decision: starts at the token that overlaps the span start
            if s >= a and s < b:
                tags[i] = f"B-{lab}"
            else:
                tags[i] = f"I-{lab}"

    # map to ids
    label2id = {l:i for i,l in enumerate(LABELS)}
    ids = [label2id.get(t, 0) for t in tags]
    enc.pop("offset_mapping", None)
    enc["labels"] = ids
    return enc

def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            yield {"id": o["id"], "text": o["text"], "entities": o["entities"]}

def build_split(jsonl_path, tok):
    rows = list(load_jsonl(jsonl_path))
    def gen():
        for r in rows:
            ex = char_spans_to_bio(r["text"], r["entities"], tok)
            ex["id"] = r["id"]
            yield ex
    return Dataset.from_generator(gen)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="datasets/train.jsonl")
    ap.add_argument("--dev",   default="datasets/dev.jsonl")
    ap.add_argument("--test",  default="datasets/test.jsonl")
    ap.add_argument("--model", default="distilbert-base-uncased")
    ap.add_argument("--out",   default="pii-lab/experiments/baseline/data")
    ap.add_argument("--max_len", type=int, default=512)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model, use_fast=True, model_max_length=args.max_len)

    ds = DatasetDict({
        "train": build_split(args.train, tok),
        "validation": build_split(args.dev, tok),
        "test": build_split(args.test, tok),
    })
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    ds.save_to_disk(str(out))

    # Save label maps
    label2id = {l:i for i,l in enumerate(LABELS)}
    id2label = {i:l for l,i in label2id.items()}
    (out / "label2id.json").write_text(json.dumps(label2id, indent=2))
    (out / "id2label.json").write_text(json.dumps(id2label, indent=2))
    print("Saved tokenized dataset to", out)

if __name__ == "__main__":
    main()
