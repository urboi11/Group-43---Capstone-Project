#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hard synthetic data generator for PII detection.

- Multiple formats per label (SSN/PHONE/EMAIL/DOB/ADDRESS/CC/IP)
- Near-miss decoys (not labeled)
- Noise snippets from logs/csv/email/code/markdown

Outputs:
  <out>/synthetic/text/*.txt
  datasets/train.jsonl, dev.jsonl, test.jsonl, labels.jsonl
"""

import argparse
import json
import random
import ipaddress
from pathlib import Path
from faker import Faker

ENT_LABELS = ["PERSON","DOB","ADDRESS","SSN","EMAIL","PHONE","CREDIT_CARD","IP_ADDRESS"]

# -----------------------------
# Style banks (return lists of callables)
# -----------------------------
def ssn_styles(n):
    styles = [
        lambda f: f.ssn(),                                        # 123-45-6789
        lambda f: f.ssn().replace("-", ""),                       # 123456789
        lambda f: f"SSN:{f.ssn()}",
        lambda f: f"Social Security {f.ssn()}",
        lambda f: f"SSN {f.ssn().replace('-', ' ')}",             # 123 45 6789
        lambda f: f"{f.ssn()[0:3]} {f.ssn()[4:6]} {f.ssn()[7:]}", # 123 45 6789
    ]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

def phone_styles(n):
    styles = [
        lambda f: f.phone_number(),
        lambda f: f"+1{f.msisdn()[:10]}",
        lambda f: f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
        lambda f: f"{random.randint(200,999)}.{random.randint(200,999)}.{random.randint(1000,9999)}",
        lambda f: f"{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
    ]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

def email_styles(n):
    styles = [
        lambda f: f.email(),
        lambda f: f"{f.user_name()}@{f.free_email_domain()}",
        lambda f: f"{f.user_name()}@mail.{f.domain_name()}",
        lambda f: f"{f.user_name()}+alerts@{f.domain_name()}",
    ]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

def dob_styles(n):
    def dob_iso(f):  return f.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y-%m-%d")
    def dob_us(f):   return f.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
    def dob_text(f): return f.date_of_birth(minimum_age=18, maximum_age=90).strftime("%b %d, %Y")
    def dob_rev(f):  return f.date_of_birth(minimum_age=18, maximum_age=90).strftime("%d-%m-%Y")
    styles = [dob_iso, dob_us, dob_text, dob_rev]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

def address_styles(n):
    styles = [
        lambda f: f.address().replace("\n", ", "),
        lambda f: f"{f.building_number()} {f.street_name()}, {f.city()}, {f.state_abbr()} {f.postcode()}",
        lambda f: f"{f.street_address()}, {f.city()} {f.state_abbr()}",
    ]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

def cc_styles(n):
    def cc_plain(_):  return f"{random.randint(4000000000000000,4999999999999999)}"
    def cc_spaced(_): s = cc_plain(_); return " ".join([s[i:i+4] for i in range(0,16,4)])
    def cc_dashed(_): s = cc_plain(_); return "-".join([s[i:i+4] for i in range(0,16,4)])
    styles = [cc_plain, cc_spaced, cc_dashed]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

def ip_styles(n):
    def ipv4(_):       return Faker().ipv4_public()
    def ipv6(_):       return str(ipaddress.IPv6Address(random.getrandbits(128)))
    def ipv4nodots(_): return "".join([str(random.randint(1,255)) for _ in range(4)])
    styles = [ipv4, ipv6, ipv4nodots]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

STYLE_BANK = {
    "SSN": ssn_styles, "PHONE": phone_styles, "EMAIL": email_styles,
    "DOB": dob_styles, "ADDRESS": address_styles, "CREDIT_CARD": cc_styles,
    "IP_ADDRESS": ip_styles,
}

# -----------------------------
# Decoys & noise
# -----------------------------
def decoy_like_ssn(f):   return f"{random.randint(10,99)}-{random.randint(10,99)}-{random.randint(1000,9999)}"
def decoy_like_phone(f): return f"+{random.randint(2,9)}{random.randint(10**8,10**10-1)}"
def decoy_like_email(f): return f"{f.user_name()}(at){f.domain_name()}"
def decoy_like_cc(f):    return f"{random.randint(1000,9999)}-{random.randint(100,999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}"
def decoy_like_ip(f):    return f"{random.randint(300,999)}.{random.randint(300,999)}.{random.randint(300,999)}.{random.randint(300,999)}"

DECOYS = [decoy_like_ssn, decoy_like_phone, decoy_like_email, decoy_like_cc, decoy_like_ip]

NOISE_SNIPPETS = [
    "2025-03-14T10:05:22Z INFO user login ok src=10.0.0.12 req=GET /health",
    "WARN scheduler: job 27 retried after timeout",
    "name,role,last_seen\nalice,analyst,2025-02-10\nbob,admin,2025-02-11",
    "From: buildbot@ci.example.com\nSubject: Nightly pass\n\nAll checks green.",
    "const cfg = { retries:3, url:'https://api.example.com/v1/ping' };",
]

TEMPLATES = [
    "Customer {PERSON} (DOB {DOB}) at {ADDRESS}. SSN {SSN}. Email {EMAIL}. Phone {PHONE}. Card {CREDIT_CARD}. IP {IP_ADDRESS}.",
    "Regards,\n{PERSON}\n{ADDRESS}\n{EMAIL} | {PHONE}\nClient ID: {CREDIT_CARD}\n",
    "{PERSON} | {DOB} | {ADDRESS} | SSN:{SSN} | {EMAIL} | {PHONE} | CC:{CREDIT_CARD} | IP:{IP_ADDRESS}",
    "Onboarding: Email={EMAIL}; Phone={PHONE}; Name={PERSON}; Addr={ADDRESS}; Birth={DOB}; CC={CREDIT_CARD}; IP={IP_ADDRESS}; SSN={SSN}",
]

NEG_TEMPLATES = [
    "Meeting notes: finalize the deployment plan next Tuesday; no customer data attached.",
    "Changelog: refactor module, update dependencies, and improve logging verbosity.",
    "Reminder: rotate API keys monthly and validate error handling for timeouts.",
]

# -----------------------------
# Helpers
# -----------------------------
def fill_template(template, fields):
    out, spans, i = "", [], 0
    while i < len(template):
        if template[i] == "{":
            j = template.index("}", i+1)
            key = template[i+1:j]
            val = fields[key]
            start = len(out); out += val; end = len(out)
            spans.append({"start": start,"end": end,"label": key})
            i = j+1
        else:
            out += template[i]; i += 1
    if not out.endswith("\n"): out += "\n"
    return out, spans

def build_positive(fake, style_map):
    person = fake.name()
    dob   = random.choice(style_map["DOB"])(fake)
    addr  = random.choice(style_map["ADDRESS"])(fake)
    ssn   = random.choice(style_map["SSN"])(fake)
    email = random.choice(style_map["EMAIL"])(fake)
    phone = random.choice(style_map["PHONE"])(fake)
    cc    = random.choice(style_map["CREDIT_CARD"])(fake)
    ip    = random.choice(style_map["IP_ADDRESS"])(fake)
    fields = {"PERSON":person,"DOB":dob,"ADDRESS":addr,"SSN":ssn,"EMAIL":email,"PHONE":phone,"CREDIT_CARD":cc,"IP_ADDRESS":ip}
    return fill_template(random.choice(TEMPLATES), fields)

def build_negative(fake, hard_neg_rate=0.35, noise_rate=0.5):
    lines = [random.choice(NEG_TEMPLATES)]
    if random.random() < hard_neg_rate:
        lines.append("Decoys: " + " ".join(d(fake) for d in random.sample(DECOYS, k=random.randint(1,2))))
    if random.random() < noise_rate:
        lines.append(random.choice(NOISE_SNIPPETS))
    return "\n".join(lines) + "\n", []

# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--positive_rate", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    random.seed(args.seed); fake = Faker("en_US"); Faker.seed(args.seed)

    out_root = Path(args.out)
    txt_dir = out_root/"synthetic"/"text"; txt_dir.mkdir(parents=True, exist_ok=True)
    ds_root = Path("datasets"); ds_root.mkdir(parents=True, exist_ok=True)
    labels_path = ds_root/"labels.jsonl"

    # ✅ CORRECT: build style_map with lists of callables
    style_map = {
        "SSN": ssn_styles(6),
        "PHONE": phone_styles(6),
        "EMAIL": email_styles(6),
        "DOB": dob_styles(4),
        "ADDRESS": address_styles(3),
        "CREDIT_CARD": cc_styles(3),
        "IP_ADDRESS": ip_styles(3),
    }

    items = []
    for idx in range(1, args.n+1):
        doc_id = f"doc_{idx:06d}"
        if random.random() < args.positive_rate:
            text, spans = build_positive(fake, style_map)
        else:
            text, spans = build_negative(fake)
        # maybe add extra noise block
        if random.random() < 0.4:
            extra, _ = build_negative(fake)
            text = text + ("\n" if not text.endswith("\n") else "") + extra

        (txt_dir/f"{doc_id}.txt").write_text(text, encoding="utf-8")
        items.append({"id":doc_id,"text":text,"entities":spans})

    random.shuffle(items)
    n_train = int(0.8*len(items)); n_dev = int(0.1*len(items))
    train, dev, test = items[:n_train], items[n_train:n_train+n_dev], items[n_train+n_dev:]

    with labels_path.open("w",encoding="utf-8") as f:
        for r in items: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    for name,rows in [("train.jsonl",train),("dev.jsonl",dev),("test.jsonl",test)]:
        with (ds_root/name).open("w",encoding="utf-8") as f:
            for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")

    print("Done.")
    print("Text:", txt_dir.resolve())
    print("Splits:", ds_root.resolve())

if __name__=="__main__":
    main()
