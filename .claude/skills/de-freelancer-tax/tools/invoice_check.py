#!/usr/bin/env python3
"""§ 14 Abs. 4 UStG / § 34 UStDV completeness check for an invoice given as JSON
(extracted by OCR/vision). Usage: invoice_check.py invoice.json
Keys: supplier_name, supplier_address, tax_number_or_vat_id, invoice_date, invoice_number,
service_description, service_date, net_amount, vat_rate, vat_amount, gross_amount, customer_name, customer_address.
Small-amount invoices (gross <= 250 EUR, § 33 UStDV) need fewer fields."""
import json, sys
FULL = ["supplier_name", "supplier_address", "tax_number_or_vat_id", "invoice_date", "invoice_number",
        "service_description", "service_date", "net_amount", "vat_rate", "vat_amount", "customer_name", "customer_address"]
SMALL = ["supplier_name", "supplier_address", "invoice_date", "service_description", "gross_amount", "vat_rate"]
def check(inv, kleinunternehmer=False):
    small = (inv.get("gross_amount") or 10**9) <= 250
    need = list(SMALL if small else FULL)
    if kleinunternehmer:  # incoming invoice from a Kleinunternehmer: no VAT fields
        need = [k for k in need if k not in ("vat_rate", "vat_amount", "net_amount")]
    miss = [k for k in need if not inv.get(k)]
    notes = []
    if inv.get("vat_rate") and inv.get("net_amount") and inv.get("vat_amount"):
        calc = round(inv["net_amount"] * inv["vat_rate"] / 100, 2)
        if abs(calc - inv["vat_amount"]) > 0.02: notes.append(f"VAT mismatch: {inv['net_amount']} x {inv['vat_rate']}% = {calc}, invoice says {inv['vat_amount']}")
    return {"kind": "Kleinbetragsrechnung (§ 33 UStDV)" if small else "Rechnung (§ 14 Abs. 4 UStG)",
            "missing": miss, "notes": notes, "input_vat_deductible": not miss and not notes}
if __name__ == "__main__":
    print(json.dumps(check(json.load(open(sys.argv[1]))), indent=2, ensure_ascii=False))
