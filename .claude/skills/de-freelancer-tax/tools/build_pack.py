#!/usr/bin/env python3
"""Build the Steuerberater review pack.
Usage: build_pack.py intake.json ledger.csv OUT_DIR [--regular-vat] [--hebesatz N]
Writes OUT_DIR/review-pack.md, eur-lines.csv, ledger-annotated.csv, citation-check.txt.
Every number comes from a deterministic function in taxcalc.py; narrative text is checked
with cite_check.py. Nothing is filed."""
import json, csv, os, sys, argparse, subprocess
import taxcalc as T, cite_check as C

def money(x): return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if x is not None else "n/a"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("intake"); ap.add_argument("ledger"); ap.add_argument("out")
    ap.add_argument("--regular-vat", action="store_true"); ap.add_argument("--hebesatz", type=float)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    it = json.load(open(a.intake)); year = it.get("tax_year", 2025); p = it.get("person", {})
    eur = T.eur_from_ledger(a.ledger, a.regular_vat); va = T.ustva(a.ledger) if a.regular_vat else None
    pd = it.get("private_deductions", {})
    sonder = sum(pd.get(k) or 0 for k in ("basisrente", "kv_pv_basis", "other_insurance", "donations"))
    joint = bool(p.get("spouse_joint_assessment"))
    zve = max(eur["gewinn"] - sonder, 0)
    est = T.tariff(zve, joint, year if year in T.TARIFF else 2026)
    sol = T.soli(est, joint, year if year in T.TARIFF else 2026)
    ch = {"yes": 0.09, "ja": 0.09}.get(str(p.get("church_tax")).lower(), 0.0)
    ksteuer = T.kirchensteuer(est, ch) if ch else 0.0
    paid = sum(it.get("payments_in_year", {}).get("est_advance_paid") or [])
    gew = T.gewerbesteuer(eur["gewinn"], a.hebesatz, est) if a.hebesatz else None
    missing = [k for k, v in it.get("documents_available", {}).items() if not v]
    unknown = [k for k, v in {**{f"person.{k}": v for k, v in p.items()}, **{f"private.{k}": v for k, v in pd.items()}}.items() if v is None]

    with open(os.path.join(a.out, "eur-lines.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["Zeile_Kz", "EUR"])
        for k, v in eur["zeilen"].items(): w.writerow([k, f"{v:.2f}"])
        w.writerow(["Z23 Summe Betriebseinnahmen", f"{eur['betriebseinnahmen_z23']:.2f}"]); w.writerow(["Z75 Summe Betriebsausgaben", f"{eur['betriebsausgaben_z75']:.2f}"]); w.writerow(["Gewinn", f"{eur['gewinn']:.2f}"])
    md = [f"# Steuerberater review pack - {p.get('name') or '[name]'}, tax year {year}",
          "", "Draft prepared with the DE-Tax-Suite. **Nothing has been filed.** All figures are estimates for professional review.", "",
          "## 1. Results at a glance", "| Item | EUR | Source |", "| :--- | ---: | :--- |",
          f"| Betriebseinnahmen (EÜR Z23) | {money(eur['betriebseinnahmen_z23'])} | ledger, taxcalc.eur_from_ledger |",
          f"| Betriebsausgaben (EÜR Z75) | {money(eur['betriebsausgaben_z75'])} | same |",
          f"| **Gewinn** | **{money(eur['gewinn'])}** | difference |",
          f"| Sonderausgaben used (as given) | {money(sonder)} | intake, unverified |",
          f"| Zu versteuerndes Einkommen (estimate) | {money(zve)} | profit - Sonderausgaben; other income not included |",
          f"| Einkommensteuer {year} ({'Splitting' if joint else 'Grundtabelle'}) | {money(est)} | § 32a EStG |",
          f"| Solidaritätszuschlag | {money(sol)} | §§ 3-4 SolzG |",
          f"| Kirchensteuer (9% assumed if church member) | {money(ksteuer)} | simplified |",
          f"| Advance payments recorded | {money(paid)} | intake |",
          f"| **Expected balance (payment +, refund -)** | **{money(est + sol + ksteuer - paid)}** | estimate |"]
    if gew: md.append(f"| Gewerbesteuer / § 35 credit / net | {money(gew['gewerbesteuer'])} / {money(gew['anrechnung_35_estg'])} / {money(gew['netto_belastung'])} | § 11 GewStG, § 35 EStG |")
    if va: md += ["", "## 1a. VAT (Regelbesteuerung) from the ledger", "| Item | EUR |", "| :--- | ---: |"] + [f"| {k} | {money(v)} |" for k, v in va.items()]
    md += ["", "## 2. Anlage EÜR 2025 line map", "| Zeile / Kz | EUR |", "| :--- | ---: |"] + [f"| {k} | {money(v)} |" for k, v in eur["zeilen"].items()]
    if eur["nicht_abziehbar"]: md += ["", "Non-deductible portions (reported in the 'nicht abziehbar' columns):"] + [f"- {k}: {money(v)}" for k, v in eur["nicht_abziehbar"].items()]
    md += ["", "## 3. Open issues and flags (advisor please decide)"]
    md += [f"{i}. {h}" for i, h in enumerate(eur["hinweise"], 1)] or ["None raised by the checks."]
    md += ["", "## 4. Missing documents"] + ([f"- {m}" for m in missing] or ["- none"])
    md += ["", "## 5. Unanswered profile items"] + ([f"- {u}" for u in unknown] or ["- none"])
    md += ["", "## 6. Assumptions and limits",
           "- Only Anlage EÜR is mapped; Mantelbogen and other Anlagen (S, G, N, V, KAP, Vorsorgeaufwand, AV) must be completed from source documents.",
           f"- Tariff {year}: {'statute text' if year == 2026 else 'reconstructed constants - verify against the official Programmablaufplan'}.",
           "- Child allowances, loss carry-forward, progression clause and best-of tests are not modelled.",
           "- Classification (Freiberufler vs. Gewerbe) and VAT regime taken from the intake, not independently verified.",
           "- Statutes: `references/statutes/` (fetched from gesetze-im-internet.de); BMF: `references/bmf/`. Cited rules: § 4 Abs. 3, § 6 Abs. 2, § 7g, § 32a EStG; § 19, § 15 Abs. 1a UStG; §§ 3-4 SolzG."]
    text = "\n".join(md)
    open(os.path.join(a.out, "review-pack.md"), "w", encoding="utf-8").write(text)
    res = C.check(text); bad = [r for r in res if r[1] == "INVALID"]
    with open(os.path.join(a.out, "citation-check.txt"), "w") as f:
        for c, st, why in res: f.write(f"{st:14} {c} {why}\n")
        f.write(f"\n{len(res)} citations, {len(bad)} invalid\n")
    with open(a.ledger, newline="", encoding="utf-8") as src, open(os.path.join(a.out, "ledger-annotated.csv"), "w", newline="", encoding="utf-8") as dst:
        r = csv.DictReader(src); w = csv.DictWriter(dst, fieldnames=r.fieldnames + ["eur_zeile", "kennzahl", "evidence"], delimiter=";"); w.writeheader()
        for row in r:
            z = T.EUR_LINES.get(row["category"]); row.update(eur_zeile=z[0] if z else "?", kennzahl=z[1] if z else "?", evidence=""); w.writerow(row)
    print(f"pack written to {a.out}; citations invalid: {len(bad)}")
    sys.exit(1 if bad else 0)
if __name__ == "__main__": main()
