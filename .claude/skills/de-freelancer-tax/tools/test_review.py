import unittest, tempfile, os, review as R

class Workspace(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        open(os.path.join(self.d, "review-pack.md"), "w").write("# x\n## 3. Open issues and flags (advisor please decide)\n1. first flag\n2. second flag\n\n## 4. Missing documents\n")
        open(os.path.join(self.d, "eur-lines.csv"), "w").write("a;1\n")
        R.init(self.d)
    def test_init_items(self):
        ids = [i["id"] for i in R.load(self.d)["items"]]; self.assertIn("F1", ids); self.assertIn("F2", ids); self.assertIn("D1", ids)
    def test_cannot_sign_with_open_items(self):
        with self.assertRaises(RuntimeError): R.signoff(self.d, "StB")
    def test_sign_and_void_on_change(self):
        for i in R.load(self.d)["items"]: R.set_status(self.d, i["id"], "accepted", "ok", "StB")
        R.signoff(self.d, "StB"); self.assertTrue(R.valid_signoff(self.d))
        open(os.path.join(self.d, "eur-lines.csv"), "a").write("b;2\n"); self.assertFalse(R.valid_signoff(self.d))
    def test_status_change_voids_signoff_and_history(self):
        for i in R.load(self.d)["items"]: R.set_status(self.d, i["id"], "accepted", "", "StB")
        R.signoff(self.d, "StB"); R.set_status(self.d, "F1", "question", "why?", "StB")
        self.assertIsNone(R.load(self.d)["signoff"]); self.assertTrue(len(R.load(self.d)["history"]) > 9)
    def test_bad_status(self):
        with self.assertRaises(ValueError): R.set_status(self.d, "F1", "done")
    def test_report(self): self.assertIn("none or voided", R.report(self.d))

if __name__ == "__main__": unittest.main()
