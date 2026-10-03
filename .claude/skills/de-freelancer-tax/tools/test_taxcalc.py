import unittest, tempfile, os, taxcalc as t

class Tariff(unittest.TestCase):
    def test_zone_boundaries_continuous(self):
        # statute zones must join without jumps (±1 EUR rounding)
        for lo, hi in ((17799, 17800), (69878, 69879), (277825, 277826)):
            self.assertLessEqual(abs(t.tariff(hi) - t.tariff(lo)), 1 + 1)
    def test_grundfreibetrag(self):
        self.assertEqual(t.tariff(12348), 0); self.assertEqual(t.tariff(0), 0)
        self.assertGreater(t.tariff(12349) + 1, 0)
    def test_constants_match_statute_at_zone2_end(self):
        self.assertEqual(t.tariff(17799), 1034)
    def test_top_zone_value(self):
        self.assertEqual(t.tariff(100000), int(0.42 * 100000 - 11135.63))
    def test_splitting_is_double_half(self):
        self.assertEqual(t.tariff(80000, True), 2 * t.tariff(40000))
    def test_monotonic(self):
        prev = -1
        for x in range(0, 300000, 997):
            v = t.tariff(x); self.assertGreaterEqual(v, prev); prev = v

class Tariff2025(unittest.TestCase):
    def test_zone_boundaries_continuous(self):
        for lo, hi in ((17443, 17444), (68480, 68481), (277825, 277826)):
            self.assertLessEqual(abs(t.tariff(hi, year=2025) - t.tariff(lo, year=2025)), 2)
    def test_grundfreibetrag(self):
        self.assertEqual(t.tariff(12096, year=2025), 0)
    def test_2025_lower_than_2026_tax_free_gap(self):
        self.assertGreaterEqual(t.tariff(40000, year=2025), t.tariff(40000, year=2026))

class Soli(unittest.TestCase):
    def test_below_freigrenze(self): self.assertEqual(t.soli(20350), 0.0)
    def test_milderungszone(self): self.assertEqual(t.soli(25000), 553.35)
    def test_full(self): self.assertEqual(t.soli(100000), 5500.0)

class Assets(unittest.TestCase):
    def test_classes(self):
        self.assertIn("GWG", t.asset_treatment(500)); self.assertIn("aktivieren", t.asset_treatment(801))
        self.assertIn("sofort", t.asset_treatment(2000, "computer"))
    def test_afa(self):
        self.assertEqual(t.afa_linear(1200, 4, 10)["jahr_1"], 75.0)
        d = t.afa_degressiv(10000, 8, 1)
        self.assertEqual(d["satz"], 0.30)

class Gewst(unittest.TestCase):
    def test_example(self):
        r = t.gewerbesteuer(74500, 400)
        self.assertEqual(r["messbetrag"], 1750.0); self.assertEqual(r["gewerbesteuer"], 7000.0)
        self.assertEqual(r["netto_belastung"], 0.0)

class Ledger(unittest.TestCase):
    def write(self, rows):
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
        f.write("date,description,category,net,vat\n" + "\n".join(rows)); f.close(); return f.name
    def test_eur_regular(self):
        p = self.write(["2026-01-05,Invoice,einnahme_steuerpflichtig,1000,190",
                        "2026-01-06,Laptop,edv,200,38", "2026-01-07,Dinner,bewirtung,100,19"])
        r = t.eur_from_ledger(p, True); os.unlink(p)
        self.assertEqual(r["betriebseinnahmen_z23"], 1190.0)   # 1000 + collected VAT
        self.assertEqual(r["betriebsausgaben_z75"], 200 + 70 + 57)  # + input VAT 38+19
        self.assertEqual(r["nicht_abziehbar"]["Z63 Kz165"], 30.0)
    def test_gift_over_limit_no_input_vat(self):
        p = self.write(["d,Gift,geschenke,80,15.20"]); r = t.eur_from_ledger(p, True); u = t.ustva(p); os.unlink(p)
        self.assertEqual(r["betriebsausgaben_z75"], 0.0); self.assertEqual(u["vorsteuer"], 0.0)
        self.assertEqual(r["nicht_abziehbar"]["Z62 Kz164"], 95.2)
    def test_big_purchase_flagged(self):
        p = self.write(["d,Laptop,edv,1200,228"]); r = t.eur_from_ledger(p, True); os.unlink(p)
        self.assertTrue(any("800" in h for h in r["hinweise"]))
    def test_unknown_category_flagged(self):
        p = self.write(["2026-01-05,x,foo,10,0"]); r = t.eur_from_ledger(p, False); os.unlink(p)
        self.assertTrue(r["hinweise"])
    def test_ustva(self):
        p = self.write(["d,Inv,einnahme_steuerpflichtig,1000,190", "d,Buy,edv,100,19"])
        r = t.ustva(p); os.unlink(p); self.assertEqual(r["zahllast"], 171.0)

if __name__ == "__main__": unittest.main()
