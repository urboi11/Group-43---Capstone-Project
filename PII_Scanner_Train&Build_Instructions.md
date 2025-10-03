Step 1: Generate Synthetic Data

Default:
python .\pii-lab\scripts\generate_synthetic_pii_v2.py --out .\pii-lab\data --n 3000 --seed 42

V.3 Default:
python .\pii-lab\scripts\generate_synthetic_pii_v3.py --out .\pii-lab\data --n 3000 --seed 42

V.3 Harder:
python .\pii-lab\scripts\generate_synthetic_pii_v3.py --out .\pii-lab\data --n 3000 --seed 42 --disjoint_formats

V.3 Ultra-hard:
python .\pii-lab\scripts\generate_synthetic_pii_v3.py --out .\pii-lab\data --n 3000 --seed 42 --confusables 0.2 --extra_noise 0.6 --disjoint_formats


Step 2: Prepare Dataset:

python .\pii-lab\scripts\prepare_dataset.py --model distilbert-base-uncased

Step 3: Train Model:

Baseline:
cd pii-lab
python .\pii-lab\scripts\train_ner.py --epochs 5 --bsz 8 --lr 5e-5

Build off baseline:
cd pii-lab
python .\scripts\train_ner.py --base_model experiments\baseline\model\checkpoint-1000 --data_dir experiments\baseline\data --out_dir experiments\baseline\model --epochs 5 --bsz 8 --lr 5e-5


python .\pii-lab\scripts\train_ner.py `
  --base_model "C:\Users\Capstone2026User\pii-lab\experiments\baseline\model\checkpoint-1500" `
  --data_dir "C:\Users\Capstone2026User\pii-lab\experiments\baseline\data" `
  --out_dir  "C:\Users\Capstone2026User\pii-lab\experiments\baseline\model" `
  --epochs 3 `
  --bsz 8 `
  --lr 5e-5


Step 4: Evaluate Results:

python .\pii-lab\scripts\evaluate_ner.py --per_label

Step 5: Export to ONNX:

optimum-cli export onnx --model "C:\Users\Capstone2026User\pii-lab\experiments\baseline\model\final-model" --task token-classification --opset 17 "C:\Users\Capstone2026User\pii-scanner\app\model"

Copy-Item -Path "C:\Users\Capstone2026User\pii-lab\experiments\baseline\model\final-model\id2label.json" -Destination "C:\Users\Capstone2026User\pii-scanner\app\model"

Build:
## Build prerequisites
- Windows 10/11 x64
- Python 3.11 (Conda or python.org)
- PowerShell

## Setup
```powershell
cd pii-scanner
python -m pip install -U pip
pip install pyinstaller pyyaml rich python-docx PyPDF2 onnxruntime transformers

## Create EXE
pyinstaller app\scan.py --onefile --name pii-scanner `
  --paths app `
  --hidden-import docx --hidden-import PyPDF2 `
  --add-data "app\model;model" `
  --add-data "app\config.yaml;."

