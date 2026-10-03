#!/usr/bin/env python3
"""Refresh the legal sources and report what changed.
  refresh.py            dry run: download, compare, report changed sections, BMF PDF hash changes
  refresh.py --apply    write updated statute files and BMF texts, update references/fetched.json
Afterwards run check_rules.py and the unit tests; review `git diff` before committing."""
import argparse, datetime, hashlib, io, json, os, re, subprocess, sys, tempfile, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); REF = os.path.join(HERE, "..", "references")
sys.path.insert(0, os.path.join(REF, "statutes"))
import convert
SRC = json.load(open(os.path.join(REF, "sources.json"))); STATE = os.path.join(REF, "fetched.json")

def get(url, tries=4):
    import time
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (de-tax-suite refresh)"})
            return urllib.request.urlopen(req, timeout=120).read()
        except Exception as e:          # truncated downloads (IncompleteRead) and transient errors: retry
            last = e; time.sleep(2 * (i + 1))
    raise last

def secs(text):
    parts = re.split(r"(?m)^### (§ \d+[a-z]?) .*$", text)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    changed = False; today = datetime.date.today().isoformat()
    for law in SRC["statutes"]:
        try: data = get(f"https://www.gesetze-im-internet.de/{law}/xml.zip")
        except Exception as e: print(f"FAIL {law}: {e}"); changed = True; continue
        with tempfile.TemporaryDirectory() as d:
            z = os.path.join(d, law + ".zip"); open(z, "wb").write(data)
            name, new = convert.convert_zip(z, "fetched " + today)
        path = os.path.join(REF, "statutes", name + ".md")
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        o, n = secs(old), secs(new)
        diff = sorted([s for s in n if o.get(s) != n[s]] + [s for s in o if s not in n])
        print(f"{law:12} {'unchanged' if not diff else 'CHANGED: ' + ', '.join(diff[:25])}")
        if diff: changed = True
        if a.apply: open(path, "w", encoding="utf-8").write(new)
        state[law] = {"checked": today, "sha256_sections": hashlib.sha256(json.dumps(n, sort_keys=True).encode()).hexdigest()}
    for fname, url in SRC["bmf_pdfs"].items():
        try: data = get(url)
        except Exception as e: print(f"FAIL {fname}: {e}"); changed = True; continue
        h = hashlib.sha256(data).hexdigest(); prev = state.get(fname, {}).get("sha256_pdf")
        print(f"{fname:42} {'unchanged' if prev == h else ('NEW/CHANGED' if prev else 'first fetch')}")
        if prev != h: changed = True
        if a.apply:
            with tempfile.NamedTemporaryFile(suffix=".pdf") as t:
                t.write(data); t.flush()
                subprocess.run(["pdftotext", "-layout", t.name, os.path.join(REF, "bmf", fname)], check=True)
        state[fname] = {"checked": today, "sha256_pdf": h}
    for page in SRC["bmf_watch_pages"]:
        try: html = get(page).decode("utf-8", "ignore")
        except Exception as e: print(f"FAIL watch {page}: {e}"); continue
        titles = re.findall(r'title="([^"]{20,200})"', html)[:15]
        h = hashlib.sha256("|".join(titles).encode()).hexdigest()
        prev = state.get(page, {}).get("sha256_titles")
        print(f"watch {page[-45:]:46} {'unchanged' if prev == h else 'LIST CHANGED - read the new letters'}")
        if prev != h: changed = True
        state[page] = {"checked": today, "sha256_titles": h}
    state["_last_run"] = today
    if a.apply: json.dump(state, open(STATE, "w"), indent=1)
    print("\nMANUAL EACH YEAR:\n - " + "\n - ".join(SRC["manual_each_year"]))
    print("\nRESULT:", "CHANGES FOUND - review required" if changed else "no changes")
    sys.exit(2 if changed and not a.apply else 0)
if __name__ == "__main__": main()
