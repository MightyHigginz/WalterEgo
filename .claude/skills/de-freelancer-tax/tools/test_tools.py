import unittest, subprocess, sys, os, tempfile, json, invoice_check as inv
HERE = os.path.dirname(os.path.abspath(__file__))

class Invoice(unittest.TestCase):
    def test_complete(self):
        i = dict(supplier_name="A", supplier_address="x", tax_number_or_vat_id="DE1", invoice_date="2025-01-01", invoice_number="1",
                 service_description="d", service_date="2025-01-01", net_amount=100, vat_rate=19, vat_amount=19, gross_amount=119, customer_name="B", customer_address="y")
        self.assertTrue(inv.check(i)["input_vat_deductible"])
    def test_missing_and_mismatch(self):
        r = inv.check(dict(supplier_name="A", gross_amount=500, net_amount=100, vat_rate=19, vat_amount=25))
        self.assertIn("invoice_number", r["missing"]); self.assertTrue(r["notes"]); self.assertFalse(r["input_vat_deductible"])
    def test_small_amount(self):
        r = inv.check(dict(supplier_name="A", supplier_address="x", invoice_date="d", service_description="d", gross_amount=100, vat_rate=19))
        self.assertTrue(r["kind"].startswith("Kleinbetrag")); self.assertEqual(r["missing"], [])

class Pipeline(unittest.TestCase):
    def test_bank_import_and_pack(self):
        d = tempfile.mkdtemp(); b = os.path.join(d, "bank.csv")
        open(b, "w", encoding="utf-8").write("Buchungstag;Verwendungszweck;Betrag\n2025-01-02;Kunde Rechnung 1;1.190,00\n2025-01-05;AWS Hosting;-45,50\n2025-01-09;Unbekannt GmbH;-12,00\n2025-03-10;Finanzamt ESt-VZ;-500,00\n")
        out = subprocess.run([sys.executable, os.path.join(HERE, "bank_import.py"), b, os.path.join(d, "l.csv")], capture_output=True, text=True).stdout
        self.assertIn("1 need a decision", out); self.assertIn("1 tax-office", out)
        rc = subprocess.run([sys.executable, os.path.join(HERE, "build_pack.py"), os.path.join(HERE, "..", "templates", "example-intake.json"), os.path.join(HERE, "..", "templates", "ledger.csv"), os.path.join(d, "o")]).returncode
        self.assertEqual(rc, 0); self.assertTrue(os.path.exists(os.path.join(d, "o", "review-pack.md")))

if __name__ == "__main__": unittest.main()
