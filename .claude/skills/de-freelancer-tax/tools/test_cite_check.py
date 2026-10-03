import unittest, cite_check as c

class Cite(unittest.TestCase):
    def st(self, s): return [r[1] for r in c.check(s)]
    def test_valid(self):
        for s in ["§ 19 UStG", "§ 4 Abs. 5 Satz 1 Nr. 6c EStG", "§ 7g Abs. 1 EStG", "§ 10d EStG", "§ 32a Abs. 1 EStG", "§ 147 AO", "§ 138 Abs. 4 AO"]:
            self.assertEqual(self.st(s), ["OK"], s)
    def test_invalid_section(self): self.assertEqual(self.st("§ 999 EStG"), ["INVALID"])
    def test_invalid_absatz(self): self.assertEqual(self.st("§ 19 Abs. 9 UStG"), ["INVALID"])
    def test_invalid_nr(self): self.assertEqual(self.st("§ 4 Abs. 5 Satz 1 Nr. 99 EStG"), ["INVALID"])
    def test_not_in_corpus(self): self.assertEqual(self.st("§ 823 BGB"), ["NOT-IN-CORPUS"])
    def test_multi(self): self.assertEqual(self.st("§§ 2, 3 StBerG und § 6 Abs. 2 EStG"), ["OK", "OK", "OK"])
    def test_quote(self):
        self.assertTrue(c.quote_ok("25 000 Euro nicht überschritten", "§ 19 UStG"))
        self.assertFalse(c.quote_ok("30 000 Euro nicht überschritten", "§ 19 UStG"))

if __name__ == "__main__": unittest.main()
