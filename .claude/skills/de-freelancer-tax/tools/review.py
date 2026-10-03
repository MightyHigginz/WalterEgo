#!/usr/bin/env python3
"""Advisor workspace: a review checklist with status, comments and sign-off, stored as review.json next to the pack.
  review.py PACK_DIR init [--from-pack]        create items from the pack's flags and the standing decisions
  review.py PACK_DIR list
  review.py PACK_DIR set ID STATUS [--comment TEXT] [--by NAME]     STATUS: open|accepted|changed|rejected|question
  review.py PACK_DIR signoff --by NAME          only possible when no item is open/question; records name, time, pack hash
  review.py PACK_DIR report                     writes review-status.md (what the client sees)
Sign-off also stores a SHA-256 of review-pack.md and eur-lines.csv: changing the pack afterwards invalidates it."""
import argparse, datetime as dt, hashlib, json, os, re, sys
STATUS = {"open", "accepted", "changed", "rejected", "question"}
STANDING = ["Classification: Freiberufler vs. Gewerbe and basis", "VAT regime (Kleinunternehmer vs. Regelbesteuerung) and Ist-Versteuerung",
            "Treatment of each asset > EUR 800 (AfA, GWG, Sammelposten, IAB, degressive, e-vehicle)", "Home-office method and proof",
            "Private use shares (car, phone, rooms)", "Completeness: all income sources and forms beyond Anlage EÜR", "Prior-year figures and loss carry-forward"]

def _h(d):
    h = hashlib.sha256()
    for f in ("review-pack.md", "eur-lines.csv"):
        p = os.path.join(d, f)
        if os.path.exists(p): h.update(open(p, "rb").read())
    return h.hexdigest()
def _p(d): return os.path.join(d, "review.json")
def load(d): return json.load(open(_p(d), encoding="utf-8"))
def save(d, r): json.dump(r, open(_p(d), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def init(d):
    items = [{"id": f"D{i}", "kind": "decision", "text": t, "status": "open", "comment": "", "by": None, "at": None} for i, t in enumerate(STANDING, 1)]
    pack = os.path.join(d, "review-pack.md")
    if os.path.exists(pack):
        sec = re.search(r"## 3\. Open issues and flags.*?\n(.*?)\n## ", open(pack, encoding="utf-8").read() + "\n## ", re.S)
        for i, m in enumerate(re.findall(r"^\d+\. (.+)$", sec.group(1) if sec else "", re.M), 1):
            items.append({"id": f"F{i}", "kind": "flag", "text": m, "status": "open", "comment": "", "by": None, "at": None})
    r = {"pack_dir": os.path.abspath(d), "created": now(), "items": items, "signoff": None, "history": []}
    save(d, r); return r

def set_status(d, id_, status, comment="", by=None):
    if status not in STATUS: raise ValueError("status must be one of " + ", ".join(sorted(STATUS)))
    r = load(d); it = next((x for x in r["items"] if x["id"] == id_), None)
    if it is None: raise KeyError(id_)
    r["history"].append({"id": id_, "from": it["status"], "to": status, "by": by, "at": now(), "comment": comment})
    it.update(status=status, comment=comment or it["comment"], by=by, at=now()); r["signoff"] = None   # any change voids a sign-off
    save(d, r); return it

def signoff(d, by):
    r = load(d); blocking = [x["id"] for x in r["items"] if x["status"] in ("open", "question")]
    if blocking: raise RuntimeError("cannot sign off, unresolved items: " + ", ".join(blocking))
    r["signoff"] = {"by": by, "at": now(), "pack_sha256": _h(d)}; save(d, r); return r["signoff"]

def valid_signoff(d):
    r = load(d); s = r.get("signoff")
    return bool(s and s["pack_sha256"] == _h(d))

def report(d):
    r = load(d); lines = ["# Review status", "", f"Sign-off: {'VALID - ' + r['signoff']['by'] + ' ' + r['signoff']['at'] if valid_signoff(d) else 'none or voided'}", "",
                          "| ID | Item | Status | Comment |", "| :--- | :--- | :--- | :--- |"]
    lines += [f"| {x['id']} | {x['text']} | {x['status']} | {x['comment']} |" for x in r["items"]]
    open(os.path.join(d, "review-status.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n"); return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("dir"); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").add_argument("--from-pack", action="store_true"); sub.add_parser("list"); sub.add_parser("report")
    s = sub.add_parser("set"); s.add_argument("id"); s.add_argument("status"); s.add_argument("--comment", default=""); s.add_argument("--by")
    sub.add_parser("signoff").add_argument("--by", required=True)
    a = ap.parse_args()
    try:
        if a.cmd == "init": print(json.dumps(init(a.dir)["items"], indent=1, ensure_ascii=False))
        elif a.cmd == "list": print(json.dumps(load(a.dir)["items"], indent=1, ensure_ascii=False))
        elif a.cmd == "set": print(json.dumps(set_status(a.dir, a.id, a.status, a.comment, a.by), ensure_ascii=False))
        elif a.cmd == "signoff": print(json.dumps(signoff(a.dir, a.by)))
        else: print(report(a.dir))
    except Exception as e: print("ERROR:", e, file=sys.stderr); sys.exit(1)
if __name__ == "__main__": main()
