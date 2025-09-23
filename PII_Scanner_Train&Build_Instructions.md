**Step 1: Generate Synthetic Data**



Default:

python .\\pii-lab\\scripts\\generate\_synthetic\_pii\_v2.py --out .\\pii-lab\\data --n 3000 --seed 42

Harder:

python .\\pii-lab\\scripts\\generate\_synthetic\_pii\_v2.py --out .\\pii-lab\\data --n 3000 --seed 42 --disjoint\_formats



**Step 2: Prepare Dataset:**



python .\\pii-lab\\scripts\\prepare\_dataset.py --model distilbert-base-uncased



**Step 3: Train Model:**



Baseline:

python .\\pii-lab\\scripts\\train\_ner.py --epochs 5 --bsz 8 --lr 5e-5



Build off baseline:



python .\\pii-lab\\scripts\\train\_ner.py `

&nbsp; --base\_model "C:\\Users\\Capstone2026User\\pii-lab\\experiments\\baseline\\model\\checkpoint-1500" `

&nbsp; --data\_dir "C:\\Users\\Capstone2026User\\pii-lab\\experiments\\baseline\\data" `

&nbsp; --out\_dir  "C:\\Users\\Capstone2026User\\pii-lab\\experiments\\baseline\\model" `

&nbsp; --epochs 3 `

&nbsp; --bsz 8 `

&nbsp; --lr 5e-5





**Step 4: Evaluate Results:**



python .\\pii-lab\\scripts\\evaluate\_ner.py --per\_label



**Step 5: Export to ONNX:**



python .\\pii-lab\\scripts\\export\_to\_onnx.py







Build:
## Build prerequisites

\- Windows 10/11 x64

\- Python 3.11 (Conda or python.org)

\- PowerShell



\## Setup

```powershell

cd pii-scanner

python -m pip install -U pip

pip install pyinstaller pyyaml rich python-docx PyPDF2 onnxruntime transformers



\## Create EXE

pyinstaller app\\scan.py --onefile --name pii-scanner `

&nbsp; --paths app `

&nbsp; --hidden-import docx --hidden-import PyPDF2 `

&nbsp; --add-data "app\\model;model" `

&nbsp; --add-data "app\\config.yaml;."



