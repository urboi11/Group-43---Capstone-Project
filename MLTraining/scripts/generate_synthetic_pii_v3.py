#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hard synthetic data generator for PII detection (v3, disjoint-capable).

Features:
- Luhn-valid CREDIT_CARD for positives; near-valid decoys for negatives.
- Diverse formats: plain text, HTML, CSV, JSON, code-ish, logs, signatures/tables.
- Obfuscations embedded in labeled values (keeps spans correct).
- International variants (phones/dates/addresses).
- Confusable (homoglyph) noise inside labeled values (optional).
- Optional disjoint style pools for dev/test (held-out formats).

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
# Utilities
# -----------------------------
def luhn_checksum(num_str: str) -> int:
    total = 0
    rev = list(map(int, reversed(num_str)))
    for i, d in enumerate(rev):
        if i % 2 == 1:
            d = d * 2
            if d > 9:
                d -= 9
        total += d
    return total % 10

def luhn_make_valid(prefix: str, total_len=16) -> str:
    s = prefix + "".join(str(random.randint(0,9)) for _ in range(total_len - len(prefix) - 1))
    chk = (10 - luhn_checksum(s + "0")) % 10
    return s + str(chk)

def cc_formats(valid=True):
    """Return a list of callables generating CC in different layouts."""
    def core():
        if valid:
            # Visa-like start 4 + random, Luhn-valid
            return luhn_make_valid("4" + "".join(str(random.randint(0,9)) for _ in range(5)))
        else:
            base = luhn_make_valid("4" + "".join(str(random.randint(0,9)) for _ in range(5)))
            bad = base[:-1] + str((int(base[-1])+random.randint(1,9))%10)
            return bad

    def grouped(sep=" "):
        s = core()
        return sep.join([s[i:i+4] for i in range(0,16,4)])

    return [
        lambda f: core(),
        lambda f: grouped(" "),
        lambda f: grouped("-"),
        lambda f: grouped("·"),
    ]

def confusable_map():
    return {
        "a":"а", "e":"е", "i":"і", "o":"о", "c":"с", "p":"р", "x":"х", "y":"у",
        "A":"А", "E":"Е", "O":"О",
        "0":"𝟶", "1":"𝟣", "2":"𝟤", "3":"𝟥", "4":"𝟦", "5":"𝟧", "6":"𝟨", "7":"𝟩", "8":"𝟪", "9":"𝟫",
        "@":"＠", ".":"․", "-":"‐", "_":"¯"
    }

def inject_confusables(s: str, rate=0.15):
    cmap = confusable_map()
    out = []
    for ch in s:
        if ch in cmap and random.random() < rate:
            out.append(cmap[ch])
        else:
            out.append(ch)
    return "".join(out)

def email_obfuscations(local, domain):
    variants = [
        f"{local}@{domain}",
        f"{local} at {domain}",
        f"{local}(at){domain}",
        f"{local} [at] {domain}",
        f"{local} at {domain.replace('.', ' dot ')}",
        f"{local.replace('.', '(dot)')}@( {domain} )",
        f"{local}@@{domain}",  # odd double @
    ]
    return variants

def phone_variants():
    a = random.randint(200,999); b = random.randint(200,999); c = random.randint(1000,9999)
    us_forms = [
        f"({a}) {b}-{c}",
        f"{a}-{b}-{c}",
        f"{a}.{b}.{c}",
        f"+1 {a} {b} {c}",
        f"+1-{a}-{b}-{c}",
        f"+1 ({a}) {b}-{c}",
    ]
    intl_cc = random.choice(["+44","+61","+49","+33","+34","+91"])
    intl = [
        f"{intl_cc} {random.randint(20,999)} {random.randint(200,999)} {random.randint(1000,9999)}",
        f"{intl_cc}-{random.randint(20,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
    ]
    funky = [
        f"{a} {b}  .  {c}",
        f"{a}–{b}–{c}",
        f"{a} {b}-{c}",
    ]
    return us_forms + intl + funky

def date_variants(fake):
    d = fake.date_of_birth(minimum_age=18, maximum_age=90)
    return [
        d.strftime("%Y-%m-%d"),
        d.strftime("%m/%d/%Y"),
        d.strftime("%d/%m/%Y"),
        d.strftime("%b %d, %Y"),
        d.strftime("%d-%m-%Y"),
    ]

def address_variants(fake):
    return [
        fake.address().replace("\n", ", "),
        f"{fake.building_number()} {fake.street_name()}, {fake.city()}, {fake.state_abbr()} {fake.postcode()}",
        f"{fake.street_address()}, {fake.city()} {fake.state_abbr()}",
        f"{fake.street_address()}, {fake.city()} {fake.state()} {fake.postcode()}",
    ]

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
    ]
    random.shuffle(styles); return styles[:max(1, min(n, len(styles)))]

def phone_styles(n):
    styles = [lambda f, pv=phone_variants: random.choice(pv())]
    styles = styles * 6
    return styles[:max(1, min(n, len(styles)))]

def email_styles(n):
    def make(f):
        local = f.user_name()
        domain = random.choice([f.free_email_domain(), "mail."+f.domain_name(), f.domain_name()])
        return random.choice(email_obfuscations(local, domain))
    styles = [lambda f, mk=make: mk(f) for _ in range(6)]
    return styles[:max(1, min(n, len(styles)))]

def dob_styles(n):
    styles = [lambda f: random.choice(date_variants(f))]
    styles = styles * 5
    return styles[:max(1, min(n, len(styles)))]

def address_styles(n):
    styles = [lambda f: random.choice(address_variants(f))]
    styles = styles * 4
    return styles[:max(1, min(n, len(styles)))]

def cc_styles(n):
    pool = cc_formats(valid=True)
    random.shuffle(pool)
    return pool[:max(1, min(n, len(pool)))]

def ip_styles(n):
    def ipv4_pub(_): return Faker().ipv4_public()
    def ipv6(_):     return str(ipaddress.IPv6Address(random.getrandbits(128)))
    def ipv4_pad(_): return ".".join(f"{random.randint(1,255):03d}" for _ in range(4))  # 010.200.007.099
    styles = [ipv4_pub, ipv6, ipv4_pad]
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
def decoy_like_email(f): return f"{f.user_name()}(dot){f.last_name()}(at){f.domain_name()}"
def decoy_like_cc(f):    return random.choice(cc_formats(valid=False))(f)
def decoy_like_ip(f):    return f"{random.randint(200,999)}.{random.randint(0,999)}.{random.randint(0,999)}.{random.randint(0,999)}"
def decoy_uuid(f):       return f"{f.uuid4()}"
def decoy_sha(f):        return "".join(random.choice("0123456789abcdef") for _ in range(40))
def decoy_b64(f):        return "YWJj" * random.randint(3,8)

DECOYS = [decoy_like_ssn, decoy_like_phone, decoy_like_email, decoy_like_cc, decoy_like_ip, decoy_uuid, decoy_sha, decoy_b64]

NOISE_SNIPPETS = [
    "2025-03-14T10:05:22Z INFO login ok src=10.0.0.12 req=GET /health",
    "WARN scheduler: job=27 retry=1 corr=7f3ad0",
    "name,role,last_seen\nalice,analyst,2025-02-10\nbob,admin,2025-02-11",
    "From: buildbot@ci.example.com\nSubject: Nightly pass\n\nAll checks green.",
    "const cfg = { retries:3, url:'https://api.example.com/v1/ping' };",
]

# -----------------------------
# Templates (diverse)
# -----------------------------
TEMPLATES_TEXT = [
    "Customer {PERSON} (DOB {DOB}) at {ADDRESS}. SSN {SSN}. Email {EMAIL}. Phone {PHONE}. Card {CREDIT_CARD}. IP {IP_ADDRESS}.",
    "Regards,\n{PERSON}\n{ADDRESS}\n{EMAIL} | {PHONE}\nClient ID: {CREDIT_CARD}\n",
    "{PERSON} | {DOB} | {ADDRESS} | SSN:{SSN} | {EMAIL} | {PHONE} | CC:{CREDIT_CARD} | IP:{IP_ADDRESS}",
    "Onboarding: Email={EMAIL}; Phone={PHONE}; Name={PERSON}; Addr={ADDRESS}; Birth={DOB}; CC={CREDIT_CARD}; IP={IP_ADDRESS}; SSN={SSN}",
]

TEMPLATES_HTML = [
    "<div class='sig'><strong>{PERSON}</strong><br/>{ADDRESS}<br/><a>{EMAIL}</a> | {PHONE}<br/>CC: {CREDIT_CARD}<br/>SSN: {SSN}<br/>IP: {IP_ADDRESS}</div>\n",
    "<table><tr><th>Name</th><th>Email</th><th>Phone</th><th>DOB</th><th>CC</th></tr>\n"
    f"<tr><td>{{PERSON}}</td><td>{{EMAIL}}</td><td>{{PHONE}}</td><td>{{DOB}}</td><td>{{CREDIT_CARD}}</td></tr></table>\n"
]

TEMPLATES_CSV = [
    "name,email,phone,dob,address,ssn,cc,ip\n{PERSON},{EMAIL},{PHONE},{DOB},{ADDRESS},{SSN},{CREDIT_CARD},{IP_ADDRESS}\n",
]

TEMPLATES_JSON = [
    '{{"name":"{PERSON}","email":"{EMAIL}","phone":"{PHONE}","dob":"{DOB}","address":"{ADDRESS}","ssn":"{SSN}","cc":"{CREDIT_CARD}","ip":"{IP_ADDRESS}"}}\n',
]

TEMPLATES_CODE = [
    '// user record\nconst user = {{ name: "{PERSON}", email: "{EMAIL}", phone: "{PHONE}", dob: "{DOB}", addr: "{ADDRESS}", ssn: "{SSN}", cc: "{CREDIT_CARD}", ip: "{IP_ADDRESS}" }};\n',
]

ALL_TEMPLATES = TEMPLATES_TEXT + TEMPLATES_HTML + TEMPLATES_CSV + TEMPLATES_JSON + TEMPLATES_CODE

# -----------------------------
# Fill with spans (robust to {{ }} and unknown placeholders)
# -----------------------------
def fill_template(template, fields):
    out_parts = []
    spans = []
    i = 0
    cur_len = 0
    L = len(template)
    labels_set = set(fields.keys())

    while i < L:
        ch = template[i]

        # Escaped open brace '{{' -> literal '{'
        if ch == "{" and i + 1 < L and template[i+1] == "{":
            out_parts.append("{"); cur_len += 1; i += 2; continue

        # Escaped close brace '}}' -> literal '}'
        if ch == "}" and i + 1 < L and template[i+1] == "}":
            out_parts.append("}"); cur_len += 1; i += 2; continue

        # Placeholder {KEY}
        if ch == "{":
            j = i + 1
            while j < L and template[j] != "}":
                j += 1
            if j >= L:
                # unmatched '{' -> treat as literal
                out_parts.append("{"); cur_len += 1; i += 1; continue
            key = template[i+1:j]
            if key in labels_set:
                val = fields[key]
                start = cur_len
                out_parts.append(val)
                cur_len += len(val)
                spans.append({"start": start, "end": cur_len, "label": key})
                i = j + 1
            else:
                # Not one of our placeholders -> keep literal text "{...}"
                lit = "{" + key + "}"
                out_parts.append(lit)
                cur_len += len(lit)
                i = j + 1
            continue

        # Normal char
        out_parts.append(ch); cur_len += 1; i += 1

    out = "".join(out_parts)
    if not out.endswith("\n"): out += "\n"
    return out, spans

# -----------------------------
# Builders
# -----------------------------
def build_positive(fake, style_map, confusable_rate=0.0):
    def maybe_confuse(s):
        return inject_confusables(s, rate=confusable_rate) if confusable_rate > 0.0 else s

    person = fake.name()
    dob   = maybe_confuse(random.choice(style_map["DOB"])(fake))
    addr  = maybe_confuse(random.choice(style_map["ADDRESS"])(fake))
    ssn   = maybe_confuse(random.choice(style_map["SSN"])(fake))
    email = maybe_confuse(random.choice(style_map["EMAIL"])(fake))
    phone = maybe_confuse(random.choice(style_map["PHONE"])(fake))
    cc    = maybe_confuse(random.choice(style_map["CREDIT_CARD"])(fake))
    ip    = maybe_confuse(random.choice(style_map["IP_ADDRESS"])(fake))

    fields = {"PERSON":person,"DOB":dob,"ADDRESS":addr,"SSN":ssn,"EMAIL":email,"PHONE":phone,"CREDIT_CARD":cc,"IP_ADDRESS":ip}
    return fill_template(random.choice(ALL_TEMPLATES), fields)

def build_negative(fake, hard_neg_rate=0.5, noise_rate=0.6):
    lines = [random.choice([
        "Meeting notes: finalize the deployment plan next Tuesday; no customer data attached.",
        "Changelog: refactor module, update dependencies, and improve logging verbosity.",
        "Reminder: rotate API keys monthly and validate error handling for timeouts.",
        "<p>Release: add audit headers, improve error resilience.</p>",
        "name,role,last_seen\nalice,analyst,2025-02-10\nbob,admin,2025-02-11",
    ])]
    if random.random() < hard_neg_rate:
        k = random.randint(2, 4)
        lines.append("Decoys: " + " ".join(d(fake) for d in random.sample(DECOYS, k=k)))
    if random.random() < noise_rate:
        lines.append(random.choice(NOISE_SNIPPETS))
    return "\n".join(lines) + "\n", []

# -----------------------------
# Style splitting (for disjoint formats)
# -----------------------------
def split_styles(label, k, seed=13):
    rng = random.Random(seed + hash(label) % 1000)
    styles = STYLE_BANK[label](k)
    rng.shuffle(styles)
    mid = max(1, len(styles) // 2)
    return styles[:mid], styles[mid:]  # (train, heldout)

# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--positive_rate", type=float, default=0.55)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--confusables", type=float, default=0.0, help="0.0-1.0 rate of confusable chars INSIDE labeled values")
    ap.add_argument("--extra_noise", type=float, default=0.4, help="chance to append an extra negative block")
    ap.add_argument("--disjoint_formats", action="store_true", help="use held-out style pools for dev/test positives")
    args = ap.parse_args()

    random.seed(args.seed); fake = Faker("en_US"); Faker.seed(args.seed)

    out_root = Path(args.out)
    txt_dir = out_root/"synthetic"/"text"; txt_dir.mkdir(parents=True, exist_ok=True)
    ds_root = Path("datasets"); ds_root.mkdir(parents=True, exist_ok=True)
    labels_path = ds_root/"labels.jsonl"

    # Build style maps
    if args.disjoint_formats:
        style_map_train, style_map_held = {}, {}
        cfg_k = {"SSN":5,"PHONE":6,"EMAIL":6,"DOB":5,"ADDRESS":4,"CREDIT_CARD":4,"IP_ADDRESS":3}
        for lbl, k in cfg_k.items():
            tr, ho = split_styles(lbl, k=k, seed=args.seed)
            if not tr: tr = STYLE_BANK[lbl](max(1,k//2) or 1)
            if not ho: ho = STYLE_BANK
            style_map_train[lbl] = tr
            style_map_held[lbl]  = ho
    else:
        style_map = {
            "SSN": ssn_styles(5),
            "PHONE": phone_styles(6),
            "EMAIL": email_styles(6),
            "DOB": dob_styles(5),
            "ADDRESS": address_styles(4),
            "CREDIT_CARD": cc_styles(4),   # Luhn-valid
            "IP_ADDRESS": ip_styles(3),
        }

    items = []
    for idx in range(1, args.n+1):
        doc_id = f"doc_{idx:06d}"
        is_pos = random.random() < args.positive_rate

        if args.disjoint_formats:
            if is_pos:
                text, spans = build_positive(fake, style_map_train, confusable_rate=args.confusables)
            else:
                text, spans = build_negative(fake)
        else:
            if is_pos:
                text, spans = build_positive(fake, style_map, confusable_rate=args.confusables)
            else:
                text, spans = build_negative(fake)

        if random.random() < args.extra_noise:
            extra, _ = build_negative(fake)
            text = text + ("\n" if not text.endswith("\n") else "") + extra

        (txt_dir/f"{doc_id}.txt").write_text(text, encoding="utf-8")
        items.append({"id":doc_id,"text":text,"entities":spans})

    # Split
    random.shuffle(items)
    n = len(items)
    n_train = int(0.8 * n)
    n_dev = int(0.1 * n)
    train_items = items[:n_train]
    dev_items   = items[n_train:n_train + n_dev]
    test_items  = items[n_train + n_dev:]

    # Rebuild positives in dev/test with HELD-OUT styles (disjoint)
    if args.disjoint_formats:
        def rebuild(rows, style_map):
            out = []
            for r in rows:
                if r["entities"]:  # positive
                    text, spans = build_positive(fake, style_map, confusable_rate=args.confusables)
                    (txt_dir / f"{r['id']}.txt").write_text(text, encoding="utf-8")
                    out.append({"id": r["id"], "text": text, "entities": spans})
                else:
                    out.append(r)
            return out

        dev_items  = rebuild(dev_items,  style_map_held)
        test_items = rebuild(test_items, style_map_held)

    # Write labels.jsonl (all)
    with labels_path.open("w", encoding="utf-8") as f:
        for row in (train_items + dev_items + test_items):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Split files
    for name, rows in [("train.jsonl", train_items), ("dev.jsonl", dev_items), ("test.jsonl", test_items)]:
        with (ds_root / name).open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("Done.")
    print("Text:", txt_dir.resolve())
    print("Splits:", ds_root.resolve())
    if args.confusables > 0.0:
        print(f"Confusables rate inside labeled values: {args.confusables}")
    if args.disjoint_formats:
        print("Disjoint formats ENABLED: dev/test use held-out style pools.")

if __name__=="__main__":
    main()
