#!/usr/bin/env python3
"""Canary test: every rule in references/rules.json must still match the current statute text.
Exit 1 and list the broken rules if the law (or our reading of it) has changed."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cite_check as C
RULES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "rules.json")
def run():
    bad = []
    for r in json.load(open(RULES, encoding="utf-8"))["rules"]:
        sec = C.sections(r["law"]).get(r["sec"])
        flat = re.sub(r"\s+", " ", re.sub(r"(?<![\d])\d(?=[A-ZÄÖÜ])", "", sec or ""))
        if sec is None or not re.search(r["re"], flat):
            bad.append(r)
    return bad
if __name__ == "__main__":
    bad = run(); n = len(json.load(open(RULES))["rules"])
    for r in bad: print(f"BROKEN {r['id']}: {r['law']} {r['sec']} no longer matches /{r['re']}/  (used in {r['used_in']})")
    print(f"{n - len(bad)}/{n} rules still match the statute text")
    sys.exit(1 if bad else 0)
