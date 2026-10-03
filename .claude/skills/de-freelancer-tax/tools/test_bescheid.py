import unittest, datetime as dt, bescheid as B, cite_check as C

class Deadline(unittest.TestCase):
    def test_plain(self):
        r = B.deadline("2026-05-04"); self.assertEqual((r["deemed_served"], r["objection_deadline"]), ("2026-05-08", "2026-06-08"))
    def test_end_on_weekend_moves_to_monday(self):
        r = B.deadline("2026-05-24"); self.assertEqual(r["deemed_served"], "2026-05-28"); self.assertEqual(r["objection_deadline"], "2026-06-29")
        self.assertEqual(dt.date.fromisoformat(r["objection_deadline"]).weekday(), 0)
    def test_served_on_weekend_is_not_shifted(self):
        r = B.deadline("2026-05-01"); self.assertEqual(r["deemed_served"], "2026-05-05")
        r = B.deadline("2026-05-02"); self.assertEqual(r["deemed_served"], "2026-05-06")
    def test_month_end(self):
        r = B.deadline("2026-01-27"); self.assertEqual(r["deemed_served"], "2026-01-31"); self.assertEqual(r["objection_deadline"], "2026-03-02")  # 28 Feb 2026 is Saturday
    def test_year_end(self):
        r = B.deadline("2026-12-20"); self.assertEqual(r["objection_deadline"], "2027-01-25")

class Check(unittest.TestCase):
    N = {"steuerjahr": 2026, "zve": 40000, "est": 7928, "soli": 0, "kirchensteuer": 0, "vorauszahlungen": 5000, "saldo": 2928, "datum": "2026-05-04", "vorbehalt_nachpruefung": True}
    def test_recompute_ok_and_flags(self):
        import taxcalc as T
        n = dict(self.N, est=T.tariff(40000, False, 2026)); n["saldo"] = n["est"] - 5000
        r = B.check(n, {"est": n["est"], "zve": 40000}); self.assertTrue(all(x["status"] == "OK" for x in r["rows"] if x["filed"] is not None))
        self.assertTrue(any("Vorbehalt" in f for f in r["flags"]))
    def test_deviation_and_arithmetic(self):
        r = B.check(dict(self.N, est=9000), {"est": 7928, "zve": 40000})
        self.assertTrue(any("DIFFERS" == x["status"] for x in r["rows"])); self.assertTrue(any("recomputed" in f for f in r["flags"]))
        self.assertTrue(any("balance" in f for f in r["flags"]))
    def test_draft_german_and_citations(self):
        d = B.draft({"steuerjahr": 2025, "datum": "2026-05-04", "steuernummer": "12/345/67890"}, ["Die Werbungskosten wurden nicht berücksichtigt."], True)
        self.assertIn("Einspruch", d); self.assertIn("§ 361 AO", d); self.assertIn("2026-05-04", d)
        self.assertEqual([x[1] for x in C.check(d) if x[1] != "OK"], [])

if __name__ == "__main__": unittest.main()
