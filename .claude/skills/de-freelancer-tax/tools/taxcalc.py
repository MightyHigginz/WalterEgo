#!/usr/bin/env python3
"""DE tax helper (tax year 2026 tariff, EÜR 2025 form mapping).

Every function cites the statute it implements. Results are estimates for review
by a Steuerberater, not a filed return. Run `python3 taxcalc.py --help`.
"""
import argparse, csv, json, math, sys
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN

# ---- Income tax § 32a Abs. 1 EStG ----
# 2026: statute text checked 2026-10-03. 2025: reconstructed, validated only by zone continuity
# (see tests) - VERIFY against the BMF Programmablaufplan / statute history before filing.
TARIFF = {
    2026: dict(gfb=12348, z2=17799, z3=69878, z4=277825, a2=914.51, a3=173.10, c3=1034.87, k4=11135.63, k5=19470.38, soli=20350),
    2025: dict(gfb=12096, z2=17443, z3=68480, z4=277825, a2=932.30, a3=176.64, c3=1015.13, k4=10911.92, k5=19246.67, soli=19950),
}

def tariff(zve, joint=False, year=2026):
    """Tarifliche Einkommensteuer in whole EUR. joint -> Splitting, § 32a Abs. 5."""
    p = TARIFF[year]
    if joint:
        return 2 * tariff(math.floor(zve) // 2, False, year)
    x = math.floor(zve)
    if x <= p["gfb"]:
        t = 0.0
    elif x <= p["z2"]:
        y = (x - p["gfb"]) / 10000
        t = (p["a2"] * y + 1400) * y
    elif x <= p["z3"]:
        z = (x - p["z2"]) / 10000
        t = (p["a3"] * z + 2397) * z + p["c3"]
    elif x <= p["z4"]:
        t = 0.42 * x - p["k4"]
    else:
        t = 0.45 * x - p["k5"]
    return math.floor(t)

# ---- Solidaritätszuschlag §§ 3-4 SolzG ----
def soli(est, joint=False, year=2026):
    freigrenze = TARIFF[year]["soli"] * (2 if joint else 1)
    if est <= freigrenze:
        return 0.0
    full = 0.055 * est
    milder = 0.119 * (est - freigrenze)
    return float(Decimal(str(min(full, milder))).quantize(Decimal("0.01"), ROUND_DOWN))

def kirchensteuer(est, rate=0.09):
    """8% (BY, BW) or 9%. Simplified: base = assessed tax (child allowances ignored)."""
    return float(Decimal(str(est * rate)).quantize(Decimal("0.01"), ROUND_DOWN))

# ---- Trade tax § 11 GewStG, credit § 35 EStG ----
def gewerbesteuer(gewinn, hebesatz_pct, est_attributable=None):
    ertrag = math.floor(max(gewinn, 0) / 100) * 100
    base = max(ertrag - 24500, 0)
    messbetrag = base * 0.035
    gewst = messbetrag * hebesatz_pct / 100
    credit = 4.0 * messbetrag
    if est_attributable is not None:
        credit = min(credit, est_attributable)
    credit = min(credit, gewst)
    return {"gewerbeertrag": ertrag, "messbetrag": round(messbetrag, 2),
            "gewerbesteuer": round(gewst, 2), "anrechnung_35_estg": round(credit, 2),
            "netto_belastung": round(gewst - credit, 2)}

# ---- Assets § 6 Abs. 2/2a, § 7 EStG ----
def asset_treatment(net_cost, kind="other"):
    """Classify an acquisition by net cost (gross for Kleinunternehmer)."""
    if kind == "computer":
        return "sofort (Nutzungsdauer 1 Jahr, BMF 26.02.2021)"
    if net_cost <= 800:
        return "GWG sofort (§ 6 Abs. 2 EStG)" if net_cost > 250 else "Sofortaufwand"
    return "aktivieren, AfA (§ 7 EStG); degressiv 30% möglich bei Kauf 07/2025-2027"

def afa_linear(cost, life_years, purchase_month):
    """Year-1 pro-rata amount (months incl. purchase month) and yearly amount."""
    yearly = cost / life_years
    months = 13 - purchase_month
    return {"jahr_1": round(yearly * months / 12, 2), "jaehrlich": round(yearly, 2)}

def afa_degressiv(cost, life_years, purchase_month, years=3, cap=0.30):
    """§ 7 Abs. 2 EStG: max 3x linear and 30%."""
    rate = min(cap, 3.0 / life_years)
    book, out = cost, []
    for i in range(years):
        amt = book * rate * ((13 - purchase_month) / 12 if i == 0 else 1)
        out.append(round(amt, 2)); book -= amt
    return {"satz": round(rate, 4), "betraege": out, "restwert": round(book, 2)}

# ---- EÜR 2025 mapping (Anlage EÜR 2025, BMF 29.08.2025; Zeile -> Kennzahl) ----
EUR_LINES = {  # category: (Zeile, Kennzahl, kind)
    "einnahme_kleinunternehmer": (12, 111, "in"), "einnahme_steuerpflichtig": (15, 112, "in"),
    "einnahme_steuerfrei": (16, 103, "in"), "ust_vereinnahmt": (17, 140, "in"),
    "ust_erstattet": (18, 141, "in"), "anlagenverkauf": (19, 102, "in"),
    "kfz_privat": (20, 106, "in"), "sachentnahme": (21, 108, "in"),
    "waren": (27, 100, "out"), "fremdleistungen": (29, 110, "out"), "personal": (30, 120, "out"),
    "afa_beweglich": (33, 130, "out"), "gwg": (36, 132, "out"), "miete": (39, 150, "out"),
    "telekom": (43, 280, "out"), "reisenebenkosten": (44, 221, "out"), "fortbildung": (45, 281, "out"),
    "beratung": (46, 194, "out"), "miete_beweglich": (47, 222, "out"), "edv": (50, 228, "out"),
    "arbeitsmittel": (51, 229, "out"), "werbung": (54, 224, "out"), "schuldzinsen": (56, 234, "out"),
    "vorsteuer": (57, 185, "out"), "ust_gezahlt": (58, 186, "out"), "uebrige": (60, 183, "out"),
    "geschenke": (62, 164, "out"), "bewirtung": (63, 165, "out"), "verpflegung": (64, 171, "out"),
    "arbeitszimmer": (65, 162, "out"), "tagespauschale": (66, 163, "out"),
    "kfz_leasing": (68, 144, "out"), "kfz_steuern_vers": (69, 145, "out"), "kfz_sonst": (70, 146, "out"),
}
PREF = {"geschenke_limit": 50.0, "bewirtung_abziehbar": 0.70, "tagespauschale_max": 1260.0}

def eur_from_ledger(path, regular_vat):
    """Ledger CSV columns: date,description,category,net,vat  (amounts positive).
    Kleinunternehmer: put gross in net, vat=0. Regelbesteuerer: net + vat; VAT is booked
    to Z17 (collected) and Z57 (input) automatically (cash basis)."""
    lines, flags = defaultdict(float), []
    nicht_abziehbar = defaultdict(float)
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cat, net, vat = r["category"].strip(), float(r["net"]), float(r.get("vat") or 0)
            if cat not in EUR_LINES:
                flags.append(f"UNKNOWN category '{cat}': {r['description']}"); continue
            zeile, kz, kind = EUR_LINES[cat]
            amt = net
            if cat == "bewirtung":
                lines[(zeile, kz)] += net * PREF["bewirtung_abziehbar"]
                nicht_abziehbar[(zeile, kz)] += net * (1 - PREF["bewirtung_abziehbar"])
                amt = 0
            if cat == "geschenke" and net > PREF["geschenke_limit"]:
                flags.append(f"Geschenk über 50 EUR nicht abziehbar, auch keine Vorsteuer (§ 4 Abs. 5 Nr. 1 EStG, § 15 Abs. 1a UStG): {r['description']}")
                nicht_abziehbar[(zeile, kz)] += net + vat; amt = 0; vat = 0
            if cat in ("edv", "arbeitsmittel", "uebrige") and net > 800:
                flags.append(f"Anschaffung über 800 EUR netto: als Wirtschaftsgut behandeln (AfA/Sofortabschreibung, Anlage AVEÜR): {r['description']}")
            lines[(zeile, kz)] += amt
            if regular_vat and vat:
                if kind == "in":
                    lines[EUR_LINES["ust_vereinnahmt"][:2]] += vat
                else:
                    lines[EUR_LINES["vorsteuer"][:2]] += vat
    einnahmen = sum(v for (z, k), v in lines.items() if z <= 22)
    ausgaben = sum(v for (z, k), v in lines.items() if z >= 24)
    return {"zeilen": {f"Z{z} Kz{k}": round(v, 2) for (z, k), v in sorted(lines.items())},
            "nicht_abziehbar": {f"Z{z} Kz{k}": round(v, 2) for (z, k), v in nicht_abziehbar.items()},
            "betriebseinnahmen_z23": round(einnahmen, 2), "betriebsausgaben_z75": round(ausgaben, 2),
            "gewinn": round(einnahmen - ausgaben, 2), "hinweise": flags}

def ustva(path):
    """Sums VAT by rate from the ledger (categories with kind 'in'/'out')."""
    out = {"umsatz_19_netto": 0.0, "umsatz_19_ust": 0.0, "umsatz_7_netto": 0.0, "umsatz_7_ust": 0.0, "vorsteuer": 0.0}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cat = r["category"].strip()
            if cat not in EUR_LINES: continue
            net, vat = float(r["net"]), float(r.get("vat") or 0)
            if EUR_LINES[cat][2] == "in" and cat == "einnahme_steuerpflichtig" and vat:
                k = "19" if abs(vat / net - 0.19) < 0.005 else "7" if abs(vat / net - 0.07) < 0.005 else None
                if k is None:
                    sys.stderr.write(f"WARN VAT rate not 19/7: {r['description']}\n"); continue
                out[f"umsatz_{k}_netto"] += net; out[f"umsatz_{k}_ust"] += vat
            elif EUR_LINES[cat][2] == "out" and vat:
                if cat == "geschenke" and net > PREF["geschenke_limit"]:
                    continue  # § 15 Abs. 1a UStG
                out["vorsteuer"] += vat
    out["zahllast"] = round(out["umsatz_19_ust"] + out["umsatz_7_ust"] - out["vorsteuer"], 2)
    return {k: round(v, 2) for k, v in out.items()}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("est"); a.add_argument("zve", type=float); a.add_argument("--year", type=int, default=2026, choices=sorted(TARIFF)); a.add_argument("--joint", action="store_true"); a.add_argument("--church", type=float, default=0.0)
    b = sub.add_parser("eur"); b.add_argument("ledger"); b.add_argument("--regular-vat", action="store_true")
    c = sub.add_parser("ustva"); c.add_argument("ledger")
    d = sub.add_parser("gewst"); d.add_argument("gewinn", type=float); d.add_argument("hebesatz", type=float)
    e = sub.add_parser("asset"); e.add_argument("cost", type=float); e.add_argument("--kind", default="other")
    args = p.parse_args()
    if args.cmd == "est":
        t = tariff(args.zve, args.joint, args.year)
        print(json.dumps({"year": args.year, "est": t, "soli": soli(t, args.joint, args.year), "kirchensteuer": kirchensteuer(t, args.church) if args.church else 0.0}, indent=2))
    elif args.cmd == "eur": print(json.dumps(eur_from_ledger(args.ledger, args.regular_vat), indent=2, ensure_ascii=False))
    elif args.cmd == "ustva": print(json.dumps(ustva(args.ledger), indent=2))
    elif args.cmd == "gewst": print(json.dumps(gewerbesteuer(args.gewinn, args.hebesatz), indent=2))
    elif args.cmd == "asset": print(asset_treatment(args.cost, args.kind))

if __name__ == "__main__":
    main()
