#!/usr/bin/env python3
"""Export a pack for the advisor: Excel workbook (needs the optional package openpyxl; otherwise CSV files) and a
DRAFT DATEV-style booking CSV. The DATEV file is NOT an official import file (no EXTF header, account table unverified);
the advisor's firm maps it with its own chart of accounts.
Usage: export.py PACK_DIR"""
import csv, json, os, sys

def _read_csv(p, delim=";"):
    return list(csv.reader(open(p, encoding="utf-8"), delimiter=delim)) if os.path.exists(p) else []

def sheets(d):
    s = {}
    pack = open(os.path.join(d, "review-pack.md"), encoding="utf-8").read() if os.path.exists(os.path.join(d, "review-pack.md")) else ""
    s["Zusammenfassung"] = [[ln] for ln in pack.splitlines()]
    s["EÜR-Zeilen"] = _read_csv(os.path.join(d, "eur-lines.csv"))
    s["Journal"] = _read_csv(os.path.join(d, "ledger-annotated.csv"))
    for name, fn in (("Anlagenverzeichnis", "register.json"), ("UStVA", "ustva.json")):
        p = os.path.join(d, fn)
        if os.path.exists(p):
            data = json.load(open(p, encoding="utf-8"))
            if name == "Anlagenverzeichnis":
                rows = data.get("rows", []); s[name] = [list(rows[0].keys())] + [list(r.values()) for r in rows] if rows else [["no assets"]]
            else:
                s[name] = [["Kennzahl / Zeile", "Betrag"]] + [[k, v] for k, v in data["form_usta_1a_2026"].items()] + [[], ["Flags"]] + [[x] for x in data["flags"]]
    p = os.path.join(d, "review.json")
    if os.path.exists(p):
        r = json.load(open(p, encoding="utf-8"))
        s["Prüfpunkte"] = [["ID", "Art", "Punkt", "Status", "Kommentar", "von", "am"]] + [[i["id"], i["kind"], i["text"], i["status"], i["comment"], i["by"], i["at"]] for i in r["items"]]
    s["Quellen & Annahmen"] = [["Statutes", "references/statutes (gesetze-im-internet.de)"], ["BMF", "references/bmf"], ["Calculator", "tools/taxcalc.py, tools/state.py, tools/ustva.py"],
                               ["Limits", "Draft for professional review; nothing filed; only Anlage EÜR and UStVA mapped."]]
    return s

def write_xlsx(d):
    try: import openpyxl
    except ImportError: return None
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    for name, rows in sheets(d).items():
        ws = wb.create_sheet(name[:31])
        for r in rows: ws.append(r)
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(max((len(str(c.value)) for c in col if c.value), default=8) + 2, 70)
    p = os.path.join(d, "advisor-workbook.xlsx"); wb.save(p); return p

def write_csv_fallback(d):
    out = os.path.join(d, "advisor-csv"); os.makedirs(out, exist_ok=True)
    for name, rows in sheets(d).items():
        with open(os.path.join(out, name.replace(" ", "_").replace("&", "und") + ".csv"), "w", newline="", encoding="utf-8") as f: csv.writer(f, delimiter=";").writerows(rows)
    return out

def write_datev_draft(d, skr=None):
    skr = skr or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "skr03_draft.csv")
    amap = {r[0]: r[1] for r in _read_csv(skr)[1:]}
    led = _read_csv(os.path.join(d, "ledger-annotated.csv"))
    if not led: return None
    h = led[0]; ix = {k: i for i, k in enumerate(h)}
    out = os.path.join(d, "datev-entwurf.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["DRAFT - not an official DATEV import file; accounts unverified"])
        w.writerow(["Umsatz", "S/H", "WKZ", "Kurs", "Basis-Umsatz", "WKZ Basis", "Konto", "Gegenkonto", "BU-Schlüssel", "Belegdatum", "Belegfeld 1", "Belegfeld 2", "Skonto", "Buchungstext"])
        for r in led[1:]:
            cat = r[ix["category"]]; net = float(r[ix["net"]] or 0); vat = float(r[ix["vat"]] or 0)
            income = cat.startswith("einnahme"); konto = amap.get(cat, "KONTO_PRÜFEN")
            rate = round(vat / net, 2) if net and vat else 0
            bu = ({0.19: "3", 0.07: "2"} if income else {0.19: "9", 0.07: "8"}).get(rate, "")
            ds = r[ix["date"]]; d4 = (ds[8:10] + ds[5:7]) if len(ds) >= 10 and ds[4] == "-" else ""
            w.writerow([f"{net + vat:.2f}".replace(".", ","), "H" if income else "S", "EUR", "", "", "", konto, "1200", bu, d4, "", "", "", r[ix["description"]][:60]])
    return out

def export_pack(d):
    return {"xlsx": write_xlsx(d), "csv_fallback": None if _has_openpyxl() else write_csv_fallback(d), "datev_draft": write_datev_draft(d)}

def _has_openpyxl():
    try: import openpyxl; return True
    except ImportError: return False

if __name__ == "__main__": print(json.dumps(export_pack(sys.argv[1]), indent=1))
