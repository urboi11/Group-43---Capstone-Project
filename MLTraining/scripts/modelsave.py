from transformers import AutoModelForTokenClassification, AutoTokenizer

ckpt = "pii-lab/experiments/baseline/model/checkpoint-1500"  # replace with your last checkpoint folder
model = AutoModelForTokenClassification.from_pretrained(ckpt)
tokenizer = AutoTokenizer.from_pretrained(ckpt)

model.save_pretrained("pii-lab/experiments/baseline/final-model")
tokenizer.save_pretrained("pii-lab/experiments/baseline/final-model")
