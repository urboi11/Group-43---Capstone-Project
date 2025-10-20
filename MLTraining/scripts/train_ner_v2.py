# train_ner.py
# Fine-tune a token classification (NER) model and export a clean "final-model" folder.
#
# Usage (from project root):
#   python .\pii-lab\scripts\train_ner.py --epochs 5 --bsz 8 --lr 5e-5
# Optional args:
#   --base_model         HF model name or path (default: distilbert-base-uncased)
#   --data_dir           prepared dataset dir from prepare_dataset.py
#   --out_dir            training outputs/checkpoints
#   --final_out_dir      where to save the clean export (default: final-model under out_dir)
#   --epochs --bsz --lr  standard training knobs
#   --eval_steps         evaluation/save frequency (steps)
#   --seed               RNG seed
#
# After training:
#   - Trainer saves checkpoints and the best model to --out_dir
#   - We also save a clean export to --final_out_dir with:
#       config.json, pytorch_model.bin, tokenizer files, id2label.json

import os
import json
import argparse
import numpy as np

from datasets import load_from_disk
from transformers import (
    AutoConfig,
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)
import evaluate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_model", default="distilbert-base-uncased")
    ap.add_argument("--data_dir",   default="pii-lab/experiments/baseline/data")
    ap.add_argument("--out_dir",    default="pii-lab/experiments/baseline/model")
    ap.add_argument("--final_out_dir", default=None, help="Export folder for the final packaged model")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--bsz", type=int, default=8)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--warmup_ratio", type=float, default=0.1)
    ap.add_argument("--eval_steps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fp16", action="store_true", help="Use mixed precision (requires CUDA)")
    args = ap.parse_args()

    # Load tokenized dataset + label maps (from prepare_dataset.py)
    ds = load_from_disk(args.data_dir)
    with open(os.path.join(args.data_dir, "label2id.json"), "r", encoding="utf-8") as f:
        label2id = json.load(f)
    with open(os.path.join(args.data_dir, "id2label.json"), "r", encoding="utf-8") as f:
        id2label = {int(k): v for k, v in json.load(f).items()}

    num_labels = len(label2id)

    tok = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    cfg = AutoConfig.from_pretrained(
        args.base_model,
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id,
    )
    model = AutoModelForTokenClassification.from_pretrained(args.base_model, config=cfg)

    data_collator = DataCollatorForTokenClassification(tok)
    metric = evaluate.load("seqeval")

    def compute_metrics(p):
        preds, labels = p
        preds = np.argmax(preds, axis=-1)
        true_preds, true_labels = [], []
        for pred, lab in zip(preds, labels):
            cur_p, cur_l = [], []
            for p_i, l_i in zip(pred, lab):
                if l_i == -100:
                    continue
                cur_p.append(id2label[p_i])
                cur_l.append(id2label[l_i])
            true_preds.append(cur_p)
            true_labels.append(cur_l)
        results = metric.compute(predictions=true_preds, references=true_labels)
        return {
            "precision": results.get("overall_precision", 0.0),
            "recall":    results.get("overall_recall", 0.0),
            "f1":        results.get("overall_f1", 0.0),
            "accuracy":  results.get("overall_accuracy", 0.0),
        }

    os.makedirs(args.out_dir, exist_ok=True)

    targs = TrainingArguments(
    	output_dir=args.out_dir,
   	logging_dir=os.path.join(args.out_dir, "runs"),
    	learning_rate=args.lr,
    	per_device_train_batch_size=args.bsz,
    	per_device_eval_batch_size=args.bsz,
    	num_train_epochs=args.epochs,
    	weight_decay=0.01,

    	evaluation_strategy="epoch",  
    	save_strategy="no",         
    	load_best_model_at_end=False,  
    	save_total_limit=None,         

    	warmup_ratio=args.warmup_ratio,
    	seed=args.seed,
    	report_to=["tensorboard"],
    	fp16=args.fp16,
    	save_safetensors=True,         
    )


    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        tokenizer=tok,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    # Save best model to out_dir (Trainer handles this), and tokenizer as well.
    trainer.save_model(args.out_dir)
    tok.save_pretrained(args.out_dir)

    # -------- Clean export block (this is what you asked to include) --------
    final_out = args.final_out_dir or os.path.join(args.out_dir, "final-model")
    os.makedirs(final_out, exist_ok=True)

    # Save a clean copy (weights + config)
    trainer.model.save_pretrained(final_out)
    tok.save_pretrained(final_out)

    # Also save an explicit id2label map for inference scaffolds
    with open(os.path.join(final_out, "id2label.json"), "w", encoding="utf-8") as f:
        json.dump({int(k): v for k, v in id2label.items()}, f, indent=2)

    print("\n=== Training complete ===")
    print("Best/baseline model dir :", args.out_dir)
    print("Exported clean model to :", final_out)
    print("Files you should see there include:")
    print("  - config.json")
    print("  - pytorch_model.bin")
    print("  - tokenizer.json / tokenizer files")
    print("  - id2label.json")


if __name__ == "__main__":
    main()
