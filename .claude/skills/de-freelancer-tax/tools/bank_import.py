#!/usr/bin/env python3
"""Bank CSV -> ledger CSV with category suggestions.
Usage: bank_import.py bank.csv out_ledger.csv [--date-col Buchungstag --text-col Verwendungszweck --amount-col Betrag]
Rules: keyword -> category (first match). Unmatched lines get category 'UNSORTIERT' and are listed
for the human to decide; the tool never guesses. Income = positive amounts, expenses = negative.
VAT is not derived from bank data: the 'vat' column stays empty until invoices are matched."""
import csv, sys, argparse
RULES = [("aws", "edv"), ("amazon web", "edv"), ("hetzner", "edv"), ("google workspace", "edv"), ("telekom", "telekom"),
         ("vodafone", "telekom"), ("o2", "telekom"), ("steuerberat", "beratung"), ("coworking", "miete"),
         ("büromiete", "miete"), ("bürobedarf", "arbeitsmittel"), ("fachbuch", "arbeitsmittel"),
         ("seminar", "fortbildung"), ("kurs", "fortbildung"), ("werbung", "werbung"), ("google ads", "werbung"),
         ("restaurant", "bewirtung"), ("bewirtung", "bewirtung"), ("finanzamt", "STEUER-ZAHLUNG")]
def num(s): return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
def main():
    p = argparse.ArgumentParser(); p.add_argument("bank"); p.add_argument("out")
    p.add_argument("--date-col", default="Buchungstag"); p.add_argument("--text-col", default="Verwendungszweck")
    p.add_argument("--amount-col", default="Betrag"); p.add_argument("--delimiter", default=";")
    a = p.parse_args(); rows, unsorted, tax = [], [], []
    with open(a.bank, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=a.delimiter):
            amt, text = num(r[a.amount_col]), r[a.text_col]
            cat = next((c for k, c in RULES if k in text.lower()), None)
            if amt > 0: cat = cat if cat and cat not in ("STEUER-ZAHLUNG",) else "einnahme_steuerpflichtig?"
            if cat == "STEUER-ZAHLUNG": tax.append((r[a.date_col], text, amt)); continue
            if cat is None: cat = "UNSORTIERT"; unsorted.append((r[a.date_col], text, amt))
            rows.append({"date": r[a.date_col], "description": text[:80], "category": cat, "net": f"{abs(amt):.2f}", "vat": ""})
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "description", "category", "net", "vat"]); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} lines written, {len(unsorted)} need a decision, {len(tax)} tax-office payments set aside")
    for u in unsorted: print("  UNSORTIERT:", u)
    for t in tax: print("  FINANZAMT (Vorauszahlung/Erstattung, book to Z18/Z58 or ESt prepayment as appropriate):", t)
if __name__ == "__main__": main()
