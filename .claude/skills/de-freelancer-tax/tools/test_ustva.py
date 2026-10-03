import unittest, tempfile, os, ustva as U, cite_check as C

def led(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
    f.write("date,description,category,net,vat,vat_treatment,partner_country,partner_vat_id\n" + "\n".join(rows)); f.close(); return f.name

class UStVA(unittest.TestCase):
    def run_rows(self, rows, **kw):
        p = led(rows); r = U.compute(p, **kw); os.unlink(p); return r
    def test_domestic(self):
        r = self.run_rows(["d,I,einnahme_steuerpflichtig,1000,190,,,", "d,B,edv,100,19,,,"])
        f = r["form_usta_1a_2026"]; self.assertEqual(f["Kz81"], 1000); self.assertEqual(f["Kz66"], 19.0); self.assertEqual(f["Kz83 verbleibend (Z50)"], 171.0)
    def test_reverse_charge_in(self):
        f = self.run_rows(["d,Hosting EU,edv,200,0,13B_EU_SERVICE,IE,IE123"])["form_usta_1a_2026"]
        self.assertEqual(f["Kz46"], 200); self.assertEqual(f["Kz47"], 38.0); self.assertEqual(f["Kz67"], 38.0); self.assertEqual(f["Kz83 verbleibend (Z50)"], 0.0)
    def test_eu_b2b_service_out_and_zm(self):
        r = self.run_rows(["d,Consulting,einnahme_steuerpflichtig,5000,0,EU_B2B_SERVICE,FR,FR12345678901"])
        self.assertEqual(r["form_usta_1a_2026"]["Kz21"], 5000); self.assertEqual(len(r["zusammenfassende_meldung"]), 1)
    def test_missing_vat_id_flagged(self):
        r = self.run_rows(["d,C,einnahme_steuerpflichtig,5000,0,EU_B2B_SERVICE,FR,"]); self.assertTrue(any("VAT ID" in x for x in r["flags"]))
    def test_third_country_and_export(self):
        f = self.run_rows(["d,US client,einnahme_steuerpflichtig,3000,0,THIRD_SERVICE,US,", "d,Goods,einnahme_steuerpflichtig,1000,0,EXPORT,CH,"])["form_usta_1a_2026"]
        self.assertEqual(f["Kz45"], 3000); self.assertEqual(f["Kz43"], 1000)
    def test_special_prepayment(self):
        f = self.run_rows(["d,I,einnahme_steuerpflichtig,1000,190,,,"], special_prepayment=50)["form_usta_1a_2026"]
        self.assertEqual(f["Kz83 verbleibend (Z50)"], 140.0)
    def test_gift_no_vorsteuer(self):
        r = self.run_rows(["d,Gift,geschenke,80,15.20,,,"]); self.assertEqual(r["form_usta_1a_2026"].get("Kz66", 0), 0)

class Helper(unittest.TestCase):
    def test_sales(self):
        self.assertEqual(U.sale("service", "B2B", "EU", True)["treatment"], "EU_B2B_SERVICE")
        self.assertEqual(U.sale("service", "B2B", "EU", False)["treatment"], "REVIEW")
        self.assertEqual(U.sale("service", "B2B", "THIRD")["kz"], "45")
        self.assertEqual(U.sale("goods", "B2B", "EU", True)["treatment"], "IG_LIEFERUNG")
        self.assertEqual(U.sale("goods", "B2C", "THIRD")["treatment"], "EXPORT")
    def test_purchases(self):
        self.assertEqual(U.purchase("service", "EU")["treatment"], "13B_EU_SERVICE")
        self.assertEqual(U.purchase("service", "THIRD")["treatment"], "13B_OTHER")
    def test_all_helper_citations_exist(self):
        laws = set()
        for fn in (U.sale("service", "B2B", "EU", True), U.sale("service", "B2B", "EU", False), U.sale("service", "B2B", "THIRD"), U.sale("service", "B2C", "THIRD", catalog_service=True),
                   U.sale("service", "B2C", "EU", digital=True), U.sale("goods", "B2B", "EU", True), U.sale("goods", "B2C", "THIRD"), U.sale("goods", "B2C", "EU"),
                   U.purchase("service", "EU"), U.purchase("service", "THIRD"), U.purchase("goods", "EU"), U.purchase("goods", "THIRD"), U.purchase("goods", "DE")):
            laws.update(fn["law"])
        import re
        self.assertTrue(len(laws) > 10)
        for l in laws:
            res = C.check(re.sub(r"\s*Buchst\.\s*\w", "", l))
            self.assertEqual([x[1] for x in res], ["OK"], l)

if __name__ == "__main__": unittest.main()
