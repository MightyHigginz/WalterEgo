import unittest, state as S

def A(**k):
    d = dict(id="a", description="x", acquired="2025-03-15", cost=12000, method="linear", life_years=5, business_use_pct=100); d.update(k); return d

class AfA(unittest.TestCase):
    def test_linear_pro_rata(self):
        r = S.schedule(A(), 2027)
        self.assertEqual(r[2025]["afa"], 2000.0)          # 2400 * 10/12 (March counts)
        self.assertEqual(r[2026]["afa"], 2400.0); self.assertEqual(r[2027]["book_end"], 12000 - 2000 - 4800)
    def test_linear_ends_at_zero(self):
        r = S.schedule(A(), 2031); self.assertEqual(r[2031]["book_end"], 0.0); self.assertEqual(sum(v["afa"] for v in r.values()), 12000)
    def test_degressive_cap_and_dates(self):
        d = A(acquired="2025-07-10", method="degressive", life_years=8)
        r = S.schedule(d, 2027); self.assertEqual(r[2025]["afa"], round(12000 * 0.30 * 6 / 12, 2))
        with self.assertRaises(ValueError): S.schedule(A(acquired="2025-06-30", method="degressive", life_years=8), 2026)
    def test_degressive_switches_to_linear_eventually(self):
        r = S.schedule(A(acquired="2026-01-05", method="degressive", life_years=5), 2031)
        self.assertEqual(r[2031]["book_end"], 0.0)
    def test_ecar(self):
        r = S.schedule(A(acquired="2026-02-01", method="ecar75", cost=40000), 2031)
        self.assertEqual(r[2026]["afa"], 30000.0); self.assertEqual(sum(v["afa"] for v in r.values()), 40000.0)
        with self.assertRaises(ValueError): S.schedule(A(acquired="2028-01-01", method="ecar75"), 2029)
    def test_gwg_sofort_and_computer(self):
        self.assertEqual(S.schedule(A(method="gwg", cost=500), 2025)[2025]["afa"], 500)
        self.assertEqual(S.schedule(A(method="computer", cost=1800), 2025)[2025]["book_end"], 0.0)
    def test_sammelposten(self):
        r = S.schedule(A(method="sammelposten", cost=900), 2030); self.assertEqual(r[2025]["afa"], 180.0); self.assertEqual(r[2029]["book_end"], 0.0)
    def test_disposal(self):
        r = S.schedule(A(disposed={"date": "2026-06-30", "proceeds": 7000}), 2027)
        self.assertEqual(r[2026]["afa"], 1200.0); self.assertEqual(r[2026]["erloes"], 7000); self.assertNotIn(2027, r)
        self.assertEqual(r[2026]["abgang"], 12000 - 2000 - 1200)

class Register(unittest.TestCase):
    def test_eur_lines(self):
        s = {"assets": [A(), A(id="b", method="gwg", cost=400, acquired="2026-02-01")], "iab": [], "years": {}}
        r = S.register(s, 2026)
        self.assertEqual(r["eur_lines"]["Z33 AfA bewegliche WG"], 2400.0); self.assertEqual(r["eur_lines"]["Z36 GWG (§ 6 Abs. 2)"], 400.0)
        self.assertEqual(r["rows"][0]["buchwert_beginn"], 10000.0)

class IabLoss(unittest.TestCase):
    def test_iab_deadline(self):
        s = {"iab": [{"id": "i", "year": 2024, "amount": 5000, "status": "open"}]}
        self.assertIn("invest by", S.iab_check(s, 2027)["open"][0]["action"]); self.assertIn("REVERSE", S.iab_check(s, 2028)["open"][0]["action"])
    def test_iab_use(self): self.assertEqual(S.iab_use({"amount": 5000}, 8000), 4000.0)
    def test_iab_cap_warning(self):
        s = {"iab": [{"id": "i", "year": 2026, "amount": 210000, "status": "open"}]}; self.assertTrue(S.iab_check(s, 2026)["warnings"])
    def test_loss(self):
        self.assertEqual(S.apply_loss(-5000, 1000), (0.0, 6000.0, 5000.0))
        self.assertEqual(S.apply_loss(3000, 5000), (3000.0, 2000.0, 0.0))
        self.assertEqual(S.apply_loss(1_500_000, 2_000_000), (1_350_000.0, 650_000.0, 0.0))
    def test_close_year_and_compare(self):
        s = {"loss_carryforward": {"amount": 0, "as_of_year": None}, "years": {"2024": {"profit": 10000}}}
        S.close_year(s, 2025, 20000, profit=20000); self.assertTrue(S.compare_years(s, 2025)["flag"])

if __name__ == "__main__": unittest.main()
