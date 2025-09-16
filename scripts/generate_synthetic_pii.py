#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate synthetic documents containing PII with gold span labels.
Produces:
  - data/synthetic/text/*.txt
  - data/synthetic/docx/*.docx (optional)
  - data/synthetic/pdf/*.pdf  (optional)
  - datasets/labels.jsonl  (all)
  - datasets/train.jsonl, dev.jsonl, test.jsonl
Usage:
  python scripts/generate_synthetic_pii.py --out data --n 500 --formats txt docx pdf --seed 42
"""

import argparse, random, json, os
from pathlib import Path
from datetime import date
from faker import Faker

# Optional writers
try:
    from docx import Document
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    HAVE_PDF = True
except Exception:
    HAVE_PDF = False

ENT_LABELS = ["PERSON", "DOB", "ADDRESS", "SSN", "EMAIL", "PHONE", "CREDIT_CARD", "IP_ADDRESS"]

TEMPLATES = [
    "Customer {PERSON} (DOB {DOB}) lives at {ADDRESS}. SSN {SSN}. Email {EMAIL}. Phone {PHONE}. Card {CREDIT_CARD}. Last login IP {IP_ADDRESS}.",
    "Contact: {PERSON}, born {DOB}, residence: {ADDRESS}. Reach at {EMAIL} or {PHONE}. SSN={SSN}. Primary card {CREDIT_CARD}. Recent IP {IP_ADDRESS}.",
    "{PERSON} | {DOB} | {ADDRESS} | SSN {SSN} | {EMAIL} | {PHONE} | CC {CREDIT_CARD} | IP {IP_ADDRESS}",
    "Onboarding record: Name={PERSON}; Date of Birth={DOB}; Address={ADDRESS}; Email={EMAIL}; Phone={PHONE}; SSN={SSN}; Card={CREDIT_CARD}; IP={IP_ADDRESS}."
]

NEG_TEMPLATES = [
    "Meeting notes: finalize the deployment plan next Tuesday; no customer data attached.",
    "Changelog: refactor module, update dependencies, and improve logging verbosity.",
    "Reminder: rotate API keys monthly and validate error handling for timeouts.",
]

def build_example(fake: Faker, positive=True):
    if not positive:
        return random.choice(NEG_TEMPLATES), []

    # Generate realistic PII fields
    name = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y-%m-%d")
    addr = fake.address().replace("\n", ", ")
    ssn = fake.ssn()  # US style
    email = fake.email()
    phone = fake.phone_number()
    cc = fake.credit_card_number()
    ip = fake.ipv4_public()

    fields = {
        "PERSON": name,
        "DOB": dob,
        "ADDRESS": addr,
        "SSN": ssn,
        "EMAIL": email,
        "PHONE": phone,
        "CREDIT_CARD": cc,
        "IP_ADDRESS": ip,
    }

    template = random.choice(TEMPLATES)

    # Build text while tracking spans
    text = ""
    entities = []

    i = 0
    while i < len(template):
        if template[i] == "{":
            j = template.index("}", i+1)
            key = template[i+1:j]
            val = fields[key]
            start = len(text)
            text += val
            end = len(text)
            entities.append({"start": start, "end": end, "label": key})
            i = j + 1
        else:
            text += template[i]
            i += 1

    # Guarantee newline at end (nicer for some tools)
    if not text.endswith("\n"):
        text += "\n"

    return text, entities

def write_txt(path: Path, text: str):
    path.write_text(text, encoding="utf-8")

def write_docx(path: Path, text: str):
    if not HAVE_DOCX:
        return
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(str(path))

def write_pdf(path: Path, text: str):
    if not HAVE_PDF:
        return
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    x, y = 72, height - 72  # 1" margins
    for line in text.splitlines():
        c.drawString(x, y, line[:1200])  # simple single-line write
        y -= 14
        if y < 72:
            c.showPage()
            y = height - 72
    c.save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data", help="Root output folder (will create subfolders)")
    parser.add_argument("--n", type=int, default=200, help="Number of documents to generate")
    parser.add_argument("--positive_rate", type=float, default=0.75, help="Probability a doc contains PII")
    parser.add_argument("--formats", nargs="+", default=["txt", "docx", "pdf"],
                        help="Any of: txt docx pdf")
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    random.seed(args.seed)
    fake = Faker("en_US")
    Faker.seed(args.seed)

    out_root = Path(args.out)
    syn_root = out_root / "synthetic"
    txt_dir = syn_root / "text"
    docx_dir = syn_root / "docx"
    pdf_dir = syn_root / "pdf"
    for d in [txt_dir, docx_dir, pdf_dir]:
        d.mkdir(parents=True, exist_ok=True)

    ds_root = Path("datasets")
    ds_root.mkdir(parents=True, exist_ok=True)
    labels_path = ds_root / "labels.jsonl"
    all_items = []

    for idx in range(1, args.n + 1):
        doc_id = f"doc_{idx:05d}"
        positive = random.random() < args.positive_rate
        text, entities = build_example(fake, positive=positive)

        # Write files
        if "txt" in args.formats:
            write_txt(txt_dir / f"{doc_id}.txt", text)
        if "docx" in args.formats:
            write_docx(docx_dir / f"{doc_id}.docx", text)
        if "pdf" in args.formats:
            write_pdf(pdf_dir / f"{doc_id}.pdf", text)

        all_items.append({"id": doc_id, "text": text, "entities": entities})

    # Save global labels.jsonl
    with labels_path.open("w", encoding="utf-8") as f:
        for row in all_items:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Train/dev/test split (80/10/10)
    random.shuffle(all_items)
    n = len(all_items)
    n_train = int(0.8 * n)
    n_dev = int(0.1 * n)

    splits = {
        "train.jsonl": all_items[:n_train],
        "dev.jsonl": all_items[n_train:n_train + n_dev],
        "test.jsonl": all_items[n_train + n_dev:],
    }
    for name, items in splits.items():
        with (ds_root / name).open("w", encoding="utf-8") as f:
            for row in items:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Done. Wrote {args.n} docs.")
    print(f"Files under: {syn_root.resolve()}")
    print(f"Labels: {labels_path.resolve()} and dataset splits in {ds_root.resolve()}")

if __name__ == "__main__":
    main()
