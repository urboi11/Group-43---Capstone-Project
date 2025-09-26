# export_to_onnx.py
import os, json
from transformers import AutoTokenizer, AutoConfig
from optimum.onnxruntime import ORTModelForTokenClassification

src = r"C:\Users\Capstone2026User\pii-lab\experiments\baseline\model\final-model"
dst = r"C:\Users\Capstone2026User\pii-scanner\app\model"

os.makedirs(dst, exist_ok=True)

tok = AutoTokenizer.from_pretrained(src, use_fast=True)
cfg = AutoConfig.from_pretrained(src)

ort_model = ORTModelForTokenClassification.from_pretrained(
    src, export=True, from_transformers=True, opset=17
)
ort_model.save_pretrained(dst)
tok.save_pretrained(dst)

with open(os.path.join(dst, "id2label.json"), "w") as f:
    json.dump({int(k): v for k, v in cfg.id2label.items()}, f)

print("Exported ONNX model to", dst)
