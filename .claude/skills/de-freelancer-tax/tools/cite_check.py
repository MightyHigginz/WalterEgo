#!/usr/bin/env python3
"""Citation validator: every '§ N [Abs. n] [Satz n] [Nr. n] LAW' in a text must exist in the
statute files under references/statutes. Exit code 1 if any citation is invalid.
Usage: cite_check.py FILE [FILE...]   |   cite_check.py -   (stdin)
       cite_check.py --quote "text" "§ 19 UStG"   (verbatim quote must appear in that section)"""
import re, sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "statutes")
LAWS = {"EStG": "estg", "UStG": "ustg_1980", "GewStG": "gewstg", "AO": "ao_1977", "StBerG": "stberg",
        "UStDV": "ustdv_1980", "SolzG": "solzg_1995", "KStG": "kstg_1977", "GmbHG": "gmbhg",
        "EStDV": "estdv_1955", "KSVG": "ksvg", "SGB IV": "sgb_4", "SGB VI": "sgb_6"}
_cache = {}

def sections(law):
    if law not in _cache:
        with open(os.path.join(ROOT, LAWS[law] + ".md"), encoding="utf-8") as fh:
            txt = fh.read()
        parts = re.split(r"(?m)^### (§ \d+[a-z]?) .*$", txt)
        _cache[law] = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    return _cache[law]

CITE = re.compile(
    r"(§§?)\s*(\d+[a-z]?)(?:\s*(?:,|und|bis|–|-)\s*(\d+[a-z]?))?"
    r"((?:\s*(?:Abs\.|Absatz)\s*\d+[a-z]?)?(?:\s*(?:Satz|S\.)\s*\d+)?(?:\s*(?:Nr\.|Nummer)\s*\d+[a-z]?)?)"
    r"\s+(" + "|".join(sorted((re.escape(k) for k in LAWS), key=len, reverse=True)) + r"|BGB|HGB|SGB V|SGB X|BewG|InvStG|ErbStG|GrEStG|KraftStG)\b")

def check(text):
    results = []
    for m in CITE.finditer(text):
        law, nums, detail = m.group(5), [m.group(2)] + ([m.group(3)] if m.group(3) else []), m.group(4)
        cite = m.group(0)
        if law not in LAWS:
            results.append((cite, "NOT-IN-CORPUS", f"{law} is not loaded; verify manually")); continue
        secs = sections(law)
        for n in nums:
            sec = secs.get(f"§ {n}")
            if sec is None:
                results.append((cite, "INVALID", f"§ {n} does not exist in {law}")); continue
            a = re.search(r"(?:Abs\.|Absatz)\s*(\d+[a-z]?)", detail)
            if a and not re.search(rf"(?m)^\({re.escape(a.group(1))}\)", sec) and not (a.group(1) == "1" and not re.search(r"(?m)^\(\d", sec)):
                results.append((cite, "INVALID", f"§ {n} {law} has no Absatz {a.group(1)}")); continue
            nr = re.search(r"(?:Nr\.|Nummer)\s*(\d+[a-z]?)", detail)
            if nr and not re.search(rf"(?:^|\s){re.escape(nr.group(1))}\.(?:\s|$)", sec, re.M):
                results.append((cite, "INVALID", f"§ {n} {law} has no Nummer {nr.group(1)}")); continue
            results.append((cite, "OK", ""))
    return results

def quote_ok(quote, cite):
    m = CITE.search(cite)
    if not m or m.group(5) not in LAWS: return False
    sec = sections(m.group(5)).get(f"§ {m.group(2)}", "")
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"(?m)\b\d(?=[A-ZÄÖÜ])", "", s)).strip()
    return norm(quote) in norm(sec)

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--quote":
        ok = quote_ok(args[1], args[2]); print("QUOTE OK" if ok else "QUOTE NOT FOUND"); sys.exit(0 if ok else 1)
    text = "".join(sys.stdin.read() if a == "-" else open(a, encoding="utf-8").read() for a in args)
    res = check(text); bad = [r for r in res if r[1] == "INVALID"]
    for c, st, why in res:
        print(f"{st:14} {c}  {why}")
    print(f"\n{len(res)} citations, {len(bad)} invalid, {sum(1 for r in res if r[1]=='NOT-IN-CORPUS')} not in corpus")
    sys.exit(1 if bad else 0)
