import hashlib, json, os, sys, tempfile, types, unittest

TMP = tempfile.mkdtemp()
os.environ["TAX_DATA_ROOT"] = os.path.join(TMP, "data"); os.environ["TAX_TOKENS_FILE"] = os.path.join(TMP, "tokens.json")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config, sandbox, tools, agent, store, auth   # noqa: E402

def tok(role, label, clients):
    t = f"{role}-{label}-secret"; d = json.load(open(config.TOKENS_FILE)) if os.path.exists(config.TOKENS_FILE) else {}
    d[hashlib.sha256(t.encode()).hexdigest()] = {"role": role, "label": label, "clients": clients}; json.dump(d, open(config.TOKENS_FILE, "w")); return t

class Sandbox(unittest.TestCase):
    def test_bad_ids(self):
        for bad in ("../x", "A", "a", "x/y", "", "a" * 50):
            with self.assertRaises(ValueError): sandbox.client_dir(bad)
    def test_traversal_blocked(self):
        for rel in ("../other/work/x.csv", "/etc/passwd", "work/../../x", ""):
            with self.assertRaises(ValueError): sandbox.safe_path("client-a", rel)
    def test_symlink_escape_blocked(self):
        d = sandbox.client_dir("client-sym"); os.symlink("/etc", os.path.join(d, "work", "link"))
        with self.assertRaises(ValueError): sandbox.safe_path("client-sym", "work/link/passwd")

class Tools(unittest.TestCase):
    def run_tool(self, name, args, cid="client-t"): 
        out, err = tools.execute(name, args, cid); return (json.loads(out) if out.startswith(("{", "[")) else out), err
    def test_all_tools_have_dispatch_and_schema(self):
        self.assertEqual(sorted(t["name"] for t in tools.TOOLS), sorted(tools.DISPATCH))
        for t in tools.TOOLS: self.assertEqual(t["input_schema"]["type"], "object")
    def test_no_signoff_or_status_tools(self):
        names = set(tools.DISPATCH); self.assertFalse(names & {"review_set", "signoff", "review_signoff"})
    def test_statute_read_and_search(self):
        r, e = self.run_tool("read_statute_section", {"law": "UStG", "section": "§ 19", "absatz": "1"}); self.assertFalse(e); self.assertIn("25 000 Euro", r["text"])
        r, e = self.run_tool("search_statute", {"law": "EStG", "query": "Tagespauschale"}); self.assertTrue(r)
        r, e = self.run_tool("read_statute_section", {"law": "UStG", "section": "§ 999"}); self.assertIn("error", r)
    def test_cite_and_tariff(self):
        r, _ = self.run_tool("cite_check", {"text": "§ 19 UStG and § 999 EStG"}); self.assertEqual(r["invalid"], 1)
        r, _ = self.run_tool("tariff_estimate", {"zve": 50000, "year": 2025}); self.assertIn("warning", r)
        r, _ = self.run_tool("tariff_estimate", {"zve": 50000, "year": 2026}); self.assertEqual(r["est"], 10548)
    def test_files_and_eur(self):
        out, e = self.run_tool("write_file", {"path": "work/l.csv", "content": "date,description,category,net,vat\n2025-01-01,x,einnahme_steuerpflichtig,1000,190\n"}); self.assertFalse(e)
        r, e = self.run_tool("compute_eur", {"ledger_file": "work/l.csv", "regular_vat": True}); self.assertEqual(r["betriebseinnahmen_z23"], 1190.0)
        r, e = self.run_tool("write_file", {"path": "inbox/x.csv", "content": "a"}); self.assertIn("error", r)
        r, e = self.run_tool("write_file", {"path": "work/x.exe", "content": "a"}); self.assertTrue(e)
        r, e = self.run_tool("read_file", {"path": "../client-zzz/work/l.csv"}); self.assertTrue(e or "error" in str(r))
        r, e = self.run_tool("read_file", {"path": "/etc/passwd"}); self.assertTrue(e)
    def test_cross_client_isolation(self):
        self.run_tool("write_file", {"path": "work/secret.csv", "content": "a,b\n"}, "client-a")
        r, e = self.run_tool("read_file", {"path": "../client-a/work/secret.csv"}, "client-b"); self.assertTrue(e)
    def test_assets_and_iab(self):
        r, e = self.run_tool("asset_add", {"id": "a1", "description": "Cam", "acquired": "2025-08-10", "cost": 5000, "method": "degressive", "life_years": 7}, "client-s"); self.assertFalse(e)
        r, e = self.run_tool("asset_add", {"id": "a2", "description": "Old", "acquired": "2025-01-10", "cost": 5000, "method": "degressive", "life_years": 7}, "client-s"); self.assertTrue(e)   # date rule enforced
        r, _ = self.run_tool("asset_register", {"year": 2025}, "client-s"); self.assertEqual(r["rows"][0]["afa"], 625.0)
        self.run_tool("iab_add", {"id": "i", "year": 2023, "amount": 1000}, "client-s"); r, _ = self.run_tool("iab_status", {"year": 2026}, "client-s"); self.assertIn("invest by", r["open"][0]["action"])
    def test_vat_and_notice(self):
        r, _ = self.run_tool("vat_cross_border", {"direction": "sale", "kind": "service", "customer_type": "B2B", "region": "EU", "vat_id_valid": True}); self.assertEqual(r["kz"], "21")
        r, _ = self.run_tool("bescheid_deadline", {"date": "2026-05-04"}); self.assertEqual(r["objection_deadline"], "2026-06-08")
    def test_unknown_tool_and_bad_args(self):
        self.assertTrue(tools.execute("rm_rf", {}, "client-t")[1]); self.assertTrue(tools.execute("compute_eur", {}, "client-t")[1])
    def test_build_pack_end_to_end(self):
        self.run_tool("write_file", {"path": "work/i.json", "content": open(os.path.join(config.SKILL_DIR, "templates", "example-intake.json")).read()}, "client-p")
        self.run_tool("write_file", {"path": "work/l.csv", "content": open(os.path.join(config.SKILL_DIR, "templates", "ledger.csv")).read()}, "client-p")
        r, e = self.run_tool("build_pack", {"intake_file": "work/i.json", "ledger_file": "work/l.csv", "regular_vat": True}, "client-p"); self.assertTrue(r["ok"], r)
        r2, e = self.run_tool("review_list", {"pack": os.path.basename(r["pack"])}, "client-p"); self.assertTrue(len(r2) >= 7)

def blk(**k): return types.SimpleNamespace(**k)
def resp(stop, content, i=100, o=50): return types.SimpleNamespace(stop_reason=stop, content=content, usage=types.SimpleNamespace(input_tokens=i, output_tokens=o, cache_read_input_tokens=0))
class Fake:
    def __init__(self, seq): self.seq = list(seq); self.calls = []; self.beta = types.SimpleNamespace(messages=self); self.messages = self
    def create(self, **kw): self.calls.append(kw); return self.seq.pop(0)

class AgentLoop(unittest.TestCase):
    def test_tool_then_answer(self):
        f = Fake([resp("tool_use", [blk(type="tool_use", id="t1", name="tariff_estimate", input={"zve": 50000, "year": 2026})]),
                  resp("end_turn", [blk(type="text", text="Tax is 10,548 EUR (§ 32a EStG).")])])
        r = agent.run_agent(f, "client-l", [{"role": "user", "content": "x"}], system=[{"type": "text", "text": "s"}])
        self.assertEqual(r["status"], "ok"); self.assertEqual(r["tool_calls"], ["tariff_estimate"])
        self.assertEqual(f.calls[0]["thinking"], {"type": "adaptive"}); self.assertEqual(f.calls[0]["model"], "claude-opus-5-5"); self.assertEqual(f.calls[0]["output_config"]["effort"], config.EFFORT)
        tr = r["messages"][2]["content"][0]; self.assertEqual(tr["type"], "tool_result"); self.assertEqual(tr["tool_use_id"], "t1")
    def test_citation_guard_forces_rewrite(self):
        f = Fake([resp("end_turn", [blk(type="text", text="See § 999 EStG.")]), resp("end_turn", [blk(type="text", text="See § 19 UStG.")])])
        r = agent.run_agent(f, "client-l", [{"role": "user", "content": "x"}], system=[{"type": "text", "text": "s"}])
        self.assertEqual(r["answer"], "See § 19 UStG."); self.assertIn("AUTOMATIC CHECK FAILED", json.dumps(f.calls[1]["messages"]))
    def test_guard_gives_up_and_warns(self):
        f = Fake([resp("end_turn", [blk(type="text", text="§ 999 EStG")])] * 3)
        r = agent.run_agent(f, "client-l", [{"role": "user", "content": "x"}], system=[{"type": "text", "text": "s"}])
        self.assertEqual(r["status"], "unverified_citations"); self.assertIn("Unverified", r["answer"])
    def test_refusal_and_budget_and_turn_cap(self):
        f = Fake([resp("refusal", [])]); self.assertEqual(agent.run_agent(f, "client-l", [{"role": "user", "content": "x"}], system=[])["status"], "refusal")
        loop = resp("tool_use", [blk(type="tool_use", id="t", name="list_files", input={})])
        r = agent.run_agent(Fake([loop] * 30), "client-l", [{"role": "user", "content": "x"}], system=[]); self.assertEqual(r["status"], "max_turns")
        r = agent.run_agent(Fake([resp("tool_use", loop.content, 700000, 10)]), "client-l", [{"role": "user", "content": "x"}], system=[]); self.assertEqual(r["status"], "budget")
    def test_tool_error_is_returned_not_raised(self):
        f = Fake([resp("tool_use", [blk(type="tool_use", id="t", name="read_file", input={"path": "/etc/passwd"})]), resp("end_turn", [blk(type="text", text="ok")])])
        r = agent.run_agent(f, "client-l", [{"role": "user", "content": "x"}], system=[]); self.assertTrue(r["messages"][2]["content"][0].get("is_error"))
    def test_system_prompt_contains_skill(self):
        s = agent.build_system()[0]; self.assertIn("DE-Tax-Suite", s["text"]); self.assertEqual(s["cache_control"], {"type": "ephemeral"})

try:
    from fastapi.testclient import TestClient
    import app as appmod
except Exception as e:      # fastapi/httpx not installed
    TestClient = None

@unittest.skipIf(TestClient is None, "fastapi not installed")
class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(appmod.app); cls.ta = tok("client", "alice", ["client-a"]); cls.tb = tok("client", "bob", ["client-b"]); cls.adv = tok("advisor", "stb-meier", ["client-a"])
    def h(self, t): return {"Authorization": "Bearer " + t}
    def test_health_open_others_closed(self):
        self.assertEqual(self.c.get("/healthz").status_code, 200)
        self.assertEqual(self.c.post("/v1/clients/client-a/messages", json={"message": "hi"}).status_code, 401)
        self.assertEqual(self.c.post("/v1/clients/client-a/messages", json={"message": "hi"}, headers=self.h("nope")).status_code, 401)
    def test_isolation(self):
        self.assertEqual(self.c.post("/v1/clients/client-a/messages", json={"message": "hi"}, headers=self.h(self.tb)).status_code, 403)
        self.assertEqual(self.c.put("/v1/clients/client-a/files/x.csv", content=b"a", headers=self.h(self.tb)).status_code, 403)
    def test_upload_rules(self):
        self.assertEqual(self.c.put("/v1/clients/client-a/files/l.csv", content=b"a,b", headers=self.h(self.ta)).status_code, 200)
        self.assertEqual(self.c.put("/v1/clients/client-a/files/x.exe", content=b"a", headers=self.h(self.ta)).status_code, 400)
        self.assertEqual(self.c.put("/v1/clients/client-a/files/.hidden.csv", content=b"a", headers=self.h(self.ta)).status_code, 400)
    def test_message_flow_with_fake_model(self):
        appmod._client = Fake([resp("end_turn", [blk(type="text", text="Hello (§ 19 UStG).")])])
        r = self.c.post("/v1/clients/client-a/messages", json={"message": "hi"}, headers=self.h(self.ta)); self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "ok"); conv = r.json()["conversation_id"]
        appmod._client = Fake([resp("end_turn", [blk(type="text", text="again")])])
        r2 = self.c.post("/v1/clients/client-a/messages", json={"message": "more", "conversation_id": conv}, headers=self.h(self.ta)); self.assertEqual(len(appmod._client.calls[0]["messages"]), 3)
    def test_review_roles(self):
        d = sandbox.safe_path("client-a", "packs/p1"); os.makedirs(d, exist_ok=True); open(os.path.join(d, "review-pack.md"), "w").write("## 3. Open issues and flags\n1. one\n\n## 4. x\n"); open(os.path.join(d, "eur-lines.csv"), "w").write("a\n")
        import review as RV; RV.init(d)
        self.assertEqual(self.c.post("/v1/clients/client-a/packs/p1/signoff", headers=self.h(self.ta)).status_code, 403)       # client cannot sign
        self.assertEqual(self.c.post("/v1/clients/client-a/packs/p1/signoff", headers=self.h(self.adv)).status_code, 409)      # open items
        for it in RV.load(d)["items"]: self.assertEqual(self.c.post(f"/v1/clients/client-a/packs/p1/review/{it['id']}", json={"status": "accepted", "comment": "ok"}, headers=self.h(self.adv)).status_code, 200)
        r = self.c.post("/v1/clients/client-a/packs/p1/signoff", headers=self.h(self.adv)); self.assertEqual(r.status_code, 200); self.assertEqual(r.json()["by"], "stb-meier")
    def test_download_whitelist(self):
        d = sandbox.safe_path("client-a", "packs/p2"); os.makedirs(d, exist_ok=True); open(os.path.join(d, "review-pack.md"), "w").write("x"); open(os.path.join(d, "secret.txt"), "w").write("x")
        self.assertEqual(self.c.get("/v1/clients/client-a/packs/p2/review-pack.md", headers=self.h(self.ta)).status_code, 200)
        self.assertEqual(self.c.get("/v1/clients/client-a/packs/p2/secret.txt", headers=self.h(self.ta)).status_code, 404)
        self.assertEqual(self.c.get("/v1/clients/client-a/packs/p2/review-pack.md", headers=self.h(self.tb)).status_code, 403)



class SdkRoundTrip(unittest.TestCase):
    """Runs the real Anthropic SDK against a mocked transport: request shape, beta header, thinking block round-trip."""
    def test_roundtrip(self):
        try: import anthropic, httpx2 as httpx
        except ImportError: self.skipTest("anthropic not installed")
        bodies, step = [], {"n": 0}
        def handler(request):
            bodies.append(json.loads(request.content)); step["n"] += 1
            if step["n"] == 1: c, st = [{"type": "thinking", "thinking": "", "signature": "SIG"}, {"type": "tool_use", "id": "toolu_1", "name": "tariff_estimate", "input": {"zve": 50000, "year": 2026}}], "tool_use"
            else: c, st = [{"type": "text", "text": "Income tax is 10,548 EUR."}], "end_turn"
            return httpx.Response(200, json={"id": "m", "type": "message", "role": "assistant", "model": config.MODEL, "content": c, "stop_reason": st, "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 5}})
        cli = anthropic.Anthropic(api_key="x", http_client=anthropic.DefaultHttpxClient(transport=httpx.MockTransport(handler)))
        r = agent.run_agent(cli, "client-m", [{"role": "user", "content": "tax on 50k?"}])
        self.assertEqual(r["status"], "ok")
        self.assertEqual(bodies[0]["fallbacks"], "default"); self.assertEqual(bodies[0]["thinking"], {"type": "adaptive"}); self.assertEqual(bodies[0]["output_config"], {"effort": config.EFFORT})
        self.assertEqual(bodies[1]["messages"][1]["content"][0], {"signature": "SIG", "thinking": "", "type": "thinking"})   # returned unchanged
        self.assertEqual(bodies[1]["messages"][2]["content"][0]["tool_use_id"], "toolu_1")

if __name__ == "__main__": unittest.main()
