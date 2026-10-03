#!/usr/bin/env python3
"""VAT advance return (UStVA) mapped to the official 2026 form USt 1 A (BMF 29.12.2025) and a
cross-border decision helper. Kennzahlen (Kz) and form lines (Z) come from the form text in
references/bmf/bmf-2025-12-29-ustva-vordruck-2026.txt.

Ledger CSV columns: date,description,category,net,vat,vat_treatment,partner_country,partner_vat_id
vat_treatment (outgoing):  DE19 DE7 DE0 EU_B2B_SERVICE THIRD_SERVICE IG_LIEFERUNG EXPORT STEUERFREI_OHNE_VSt
vat_treatment (incoming):  VORSTEUER 13B_EU_SERVICE 13B_OTHER IG_ERWERB19 IG_ERWERB7 EUST
Rows without vat_treatment: income with vat ~19%/7% -> DE19/DE7; expense with vat -> VORSTEUER.
Bases are truncated to whole EUR (the form has no cents for bases; verify against the form instructions)."""
import csv, math, sys, json

# Kz -> (form line, meaning)
KZ = {81: (13, "Steuerpflichtige Umsätze 19% (Bemessungsgrundlage)"), 86: (14, "Steuerpflichtige Umsätze 7%"), 87: (15, "Umsätze 0%"),
      41: (19, "Innergemeinschaftliche Lieferungen an Abnehmer mit USt-IdNr."), 43: (22, "Weitere steuerfreie Umsätze mit Vorsteuerabzug (u.a. Ausfuhr)"),
      48: (23, "Steuerfreie Umsätze ohne Vorsteuerabzug"), 89: (25, "Steuerpflichtige ig. Erwerbe 19%"), 93: (26, "Steuerpflichtige ig. Erwerbe 7%"),
      46: (30, "§ 13b Abs. 1: sonstige Leistungen EU-Unternehmer (Bemessungsgrundlage); 47 = Steuer"), 84: (32, "§ 13b Abs. 2 Nr. 1, 2, 4-12: andere Leistungen (Bemessungsgrundlage); 85 = Steuer"),
      21: (35, "Nicht steuerbare sonstige Leistungen § 18b S. 1 Nr. 2 (EU B2B)"), 45: (36, "Übrige nicht steuerbare Umsätze (Leistungsort nicht im Inland)"),
      66: (38, "Vorsteuer aus Rechnungen anderer Unternehmer"), 61: (39, "Vorsteuer aus ig. Erwerb"), 62: (40, "Einfuhrumsatzsteuer"),
      67: (41, "Vorsteuer aus Leistungen nach § 13b"), 83: (50, "Verbleibende Umsatzsteuer-Vorauszahlung / Überschuss")}
OUT = {"DE19", "DE7", "DE0", "EU_B2B_SERVICE", "THIRD_SERVICE", "IG_LIEFERUNG", "EXPORT", "STEUERFREI_OHNE_VSt"}
RATE = {"19": 0.19, "7": 0.07}
def fl(x): return math.floor(x + 1e-9)

def compute(path, special_prepayment=0.0):
    k = {n: 0.0 for n in (81, 86, 87, 41, 43, 48, 89, 93, 46, 84, 21, 45, 66, 61, 62, 67)}
    tax = {"81": 0.0, "86": 0.0, "47": 0.0, "85": 0.0, "89": 0.0, "93": 0.0}
    zm, flags = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cat, net, vat = r["category"].strip(), float(r["net"]), float(r.get("vat") or 0)
            tr = (r.get("vat_treatment") or "").strip().upper()
            desc = r["description"]
            is_income = cat.startswith("einnahme") or cat in ("anlagenverkauf",)
            if not tr:
                if is_income and vat and abs(vat / net - 0.19) < 0.005: tr = "DE19"
                elif is_income and vat and abs(vat / net - 0.07) < 0.005: tr = "DE7"
                elif not is_income and vat: tr = "VORSTEUER"
                elif is_income: flags.append(f"income without VAT treatment, not reported: {desc}"); continue
                else: continue
            if cat == "geschenke" and net > 50 and tr == "VORSTEUER":
                flags.append(f"no input VAT on gift over EUR 50 (§ 15 Abs. 1a UStG): {desc}"); continue
            if tr == "DE19": k[81] += net; tax["81"] += vat if vat else net * .19
            elif tr == "DE7": k[86] += net; tax["86"] += vat if vat else net * .07
            elif tr == "DE0": k[87] += net
            elif tr == "EU_B2B_SERVICE":
                k[21] += net
                if not r.get("partner_vat_id"): flags.append(f"EU B2B service without customer VAT ID (needed for invoice, ZM, § 14a UStG): {desc}")
                else: zm.append({"country": r.get("partner_country", ""), "vat_id": r["partner_vat_id"], "amount": net, "type": "sonstige Leistung (§ 18a Abs. 2)"})
            elif tr == "THIRD_SERVICE": k[45] += net
            elif tr == "IG_LIEFERUNG":
                k[41] += net
                if not r.get("partner_vat_id"): flags.append(f"intra-EU supply without customer VAT ID - not tax-free (§ 6a UStG): {desc}")
                else: zm.append({"country": r.get("partner_country", ""), "vat_id": r["partner_vat_id"], "amount": net, "type": "Warenlieferung (§ 18a Abs. 1)"})
            elif tr == "EXPORT": k[43] += net
            elif tr == "STEUERFREI_OHNE_VSt": k[48] += net
            elif tr == "VORSTEUER": k[66] += vat
            elif tr == "13B_EU_SERVICE": k[46] += net; t = vat or net * .19; tax["47"] += t; k[67] += t
            elif tr == "13B_OTHER": k[84] += net; t = vat or net * .19; tax["85"] += t; k[67] += t
            elif tr == "IG_ERWERB19": k[89] += net; t = net * .19; tax["89"] += t; k[61] += t
            elif tr == "IG_ERWERB7": k[93] += net; t = net * .07; tax["93"] += t; k[61] += t
            elif tr == "EUST": k[62] += vat
            else: flags.append(f"unknown vat_treatment '{tr}': {desc}")
    z37 = round(sum(tax.values()), 2)
    vorsteuer = round(k[66] + k[61] + k[62] + k[67], 2)
    z45 = round(z37 - vorsteuer, 2); z48 = z45; z50 = round(z48 - special_prepayment, 2)
    form = {f"Kz{n}": fl(v) for n, v in k.items() if n in (81, 86, 87, 41, 43, 48, 89, 93, 46, 84, 21, 45) and v}
    form.update({"Kz81 Steuer": round(tax["81"], 2), "Kz86 Steuer": round(tax["86"], 2), "Kz47": round(tax["47"], 2), "Kz85": round(tax["85"], 2),
                 "Kz66": round(k[66], 2), "Kz61": round(k[61], 2), "Kz62": round(k[62], 2), "Kz67": round(k[67], 2),
                 "Z37 Umsatzsteuer gesamt": z37, "Z45 Verbleibender Betrag": z45, "Z48 Vorauszahlung/Überschuss": z48, "Kz83 verbleibend (Z50)": z50})
    if special_prepayment: form["Kz39 Sondervorauszahlung (Z49)"] = special_prepayment
    form = {a: b for a, b in form.items() if b not in (0, 0.0) or a.startswith(("Z", "Kz83"))}
    if zm: flags.append("Zusammenfassende Meldung required (BZSt, by the 25th after the period; § 18a UStG)")
    return {"form_usta_1a_2026": form, "zusammenfassende_meldung": zm, "flags": flags}

# ---------------- cross-border decision helper ----------------
def sale(kind, customer_type, region, vat_id_valid=False, digital=False, catalog_service=False):
    """kind: service|goods; customer_type: B2B|B2C; region: DE|EU|THIRD."""
    r = {"treatment": None, "kz": None, "invoice": None, "zm": False, "law": [], "flags": []}
    if region == "DE":
        r.update(treatment="DE19" if True else "", kz="81/86", invoice="normal invoice with German VAT (§ 14 UStG)", law=["§ 1 UStG", "§ 14 UStG"]); return r
    if kind == "service":
        if customer_type == "B2B":
            r["law"] = ["§ 3a Abs. 2 UStG"]
            if region == "EU":
                if vat_id_valid:
                    r.update(treatment="EU_B2B_SERVICE", kz="21", zm=True, invoice='no VAT; text "Steuerschuldnerschaft des Leistungsempfängers"; both VAT IDs; issue by the 15th of the following month',
                             law=["§ 3a Abs. 2 UStG", "§ 14a Abs. 1 UStG", "§ 18a Abs. 2 UStG", "§ 18b UStG"])
                else:
                    r.update(treatment="REVIEW", flags=["customer VAT ID missing or not validated: obtain it and confirm via the BZSt qualified check; without proof treat as B2C (German VAT)"], law=["§ 3a Abs. 1 UStG", "§ 3a Abs. 2 UStG"])
            else:
                r.update(treatment="THIRD_SERVICE", kz="45", invoice="no German VAT; note that the service is not taxable in Germany (§ 3a Abs. 2 UStG)", law=["§ 3a Abs. 2 UStG"],
                         flags=["local VAT or withholding tax may apply in the customer's country - check there"])
        else:  # B2C
            if region == "THIRD" and catalog_service:
                r.update(treatment="THIRD_SERVICE", kz="45", law=["§ 3a Abs. 4 Satz 2 Nr. 3 UStG"], invoice="no German VAT (catalogue service to a non-EU private customer)",
                         flags=["verify the service is within the § 3a Abs. 4 catalogue (e.g. engineers, lawyers, translators)"])
            elif region == "EU" and digital:
                r.update(treatment="REVIEW", law=["§ 3a Abs. 5 UStG", "§ 18j UStG"], flags=["digital/telecom/broadcast services to EU consumers: place of supply at the customer's location above the EU-wide threshold; OSS registration (§ 18j) - ask the advisor"])
            else:
                r.update(treatment="DE19", kz="81/86", law=["§ 3a Abs. 1 UStG"], invoice="German VAT; place of supply is where you run the business", flags=["check special rules (§ 3a Abs. 3-8) for the specific service"])
    else:  # goods
        if region == "EU" and customer_type == "B2B" and vat_id_valid:
            r.update(treatment="IG_LIEFERUNG", kz="41", zm=True, law=["§ 4 Nr. 1 Buchst. b UStG", "§ 6a UStG", "§ 18a Abs. 1 UStG"], invoice="no VAT; both VAT IDs; mention intra-community supply",
                     flags=["keep proof the goods reached the other EU state (Gelangensbestätigung or equivalent)"])
        elif region == "THIRD":
            r.update(treatment="EXPORT", kz="43", law=["§ 4 Nr. 1 Buchst. a UStG", "§ 6 UStG"], invoice="no VAT with export proof", flags=["keep customs export proof"])
        else:
            r.update(treatment="REVIEW", law=["§ 3c UStG", "§ 18j UStG"], flags=["distance sales to EU consumers or missing VAT ID: threshold and OSS rules - ask the advisor"])
    return r

def purchase(kind, supplier_region, supplier_has_german_vat=False):
    r = {"treatment": None, "kz": None, "input_vat": None, "law": [], "flags": []}
    if supplier_region == "DE" or supplier_has_german_vat:
        r.update(treatment="VORSTEUER", kz="66", input_vat="deductible with a valid invoice (§ 15 UStG)", law=["§ 15 Abs. 1 Nr. 1 UStG"]); return r
    if kind == "service" and supplier_region == "EU":
        r.update(treatment="13B_EU_SERVICE", kz="46/47, Vorsteuer 67", input_vat="deductible if you may deduct input VAT", law=["§ 13b Abs. 1 UStG", "§ 15 Abs. 1 Nr. 4 UStG"],
                 flags=["you owe the German VAT: book base and tax in the UStVA; a Kleinunternehmer has no input-VAT deduction - check UStAE for filing duties"])
    elif kind == "service":
        r.update(treatment="13B_OTHER", kz="84/85, Vorsteuer 67", law=["§ 13b Abs. 2 Nr. 1 UStG", "§ 15 Abs. 1 Nr. 4 UStG"], flags=["foreign supplier of services: reverse charge applies"])
    elif supplier_region == "EU":
        r.update(treatment="IG_ERWERB19", kz="89/93, Vorsteuer 61", law=["§ 1a UStG", "§ 15 Abs. 1 Nr. 3 UStG"])
    else:
        r.update(treatment="EUST", kz="62", law=["§ 15 Abs. 1 Nr. 2 UStG"], flags=["import VAT: keep the customs document"])
    return r

if __name__ == "__main__":
    print(json.dumps(compute(sys.argv[1]), indent=1, ensure_ascii=False))
