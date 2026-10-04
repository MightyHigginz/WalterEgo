"""Tool schemas and dispatcher. The model can only call these functions; they wrap the suite's Python tools
and never expose a shell. Results are JSON strings, truncated to MAX_RESULT characters."""
import contextlib, datetime as dt, io, json, os, re, subprocess, sys
import config
from sandbox import safe_path, client_dir, check_ext

sys.path.insert(0, os.path.join(config.SKILL_DIR, "tools"))
import taxcalc, ustva, state as ST, bescheid, invoice_check, cite_check, review as RV   # noqa: E402

MAX_RESULT = 20000
STAT = os.path.join(config.SKILL_DIR, "references", "statutes")
LAWS = sorted(cite_check.LAWS)
PLAYBOOKS = sorted(f[:-3] for f in os.listdir(os.path.join(config.SKILL_DIR, "playbooks")) if f.endswith(".md"))

def _s(obj):
    t = json.dumps(obj, ensure_ascii=False, indent=1, default=str)
    return t if len(t) <= MAX_RESULT else t[:MAX_RESULT] + "\n...[truncated]"

def _obj(**props):
    return {"type": "object", "properties": props, "required": [k for k, v in props.items() if v.pop("_req", False)], "additionalProperties": False}
def P(t, d, req=False, **kw):
    x = {"type": t, "description": d, **kw}
    if req: x["_req"] = True
    return x

SCHEMAS = [
 ("search_statute", "Search statute text (EStG, UStG, AO ...) or BMF texts for a keyword/regex. Returns matching paragraph headers with snippets. Use before quoting or citing any rule.",
  _obj(law=P("string", "Law abbreviation", True, enum=LAWS + ["UStAE", "BMF"]), query=P("string", "Case-insensitive regex or words", True), max_results=P("integer", "default 8"))),
 ("read_statute_section", "Read one paragraph of a law, e.g. law=UStG, section='§ 19'. Optionally restrict to one Absatz.",
  _obj(law=P("string", "Law abbreviation", True, enum=LAWS), section=P("string", "e.g. '§ 7g'", True), absatz=P("string", "e.g. '2'"))),
 ("read_playbook", "Read a playbook for a taxpayer type or topic.", _obj(name=P("string", "Playbook name", True, enum=PLAYBOOKS))),
 ("cite_check", "Verify that every '§ N Abs. n Nr. n LAW' in a text exists in the statute files. Run on drafts before answering.", _obj(text=P("string", "Text to check", True))),
 ("tariff_estimate", "Income tax from taxable income with Soli and church tax (tariff 2026 from statute; 2025 reconstructed - flag it).",
  _obj(zve=P("number", "zu versteuerndes Einkommen", True), year=P("integer", "2025 or 2026"), joint=P("boolean", "Splitting"), church_rate=P("number", "0, 0.08 or 0.09"))),
 ("compute_eur", "Build Anlage EÜR 2025 lines (Zeile/Kennzahl) from a ledger CSV in the client folder.",
  _obj(ledger_file=P("string", "relative path, e.g. work/ledger.csv", True), regular_vat=P("boolean", "true if VAT is charged (Regelbesteuerung)"))),
 ("compute_vat_return", "VAT advance return with Kennzahlen of form USt 1 A 2026 from a ledger CSV that has vat_treatment columns.",
  _obj(ledger_file=P("string", "relative path", True), special_prepayment=P("number", "Sondervorauszahlung"))),
 ("vat_cross_border", "Decide VAT treatment for a sale or purchase involving another country. Returns treatment, Kennzahl, invoice wording, statutes, flags.",
  _obj(direction=P("string", "sale or purchase", True, enum=["sale", "purchase"]), kind=P("string", "service or goods", True, enum=["service", "goods"]),
       customer_type=P("string", "B2B or B2C (sale)", enum=["B2B", "B2C"]), region=P("string", "customer (sale) or supplier (purchase) region", True, enum=["DE", "EU", "THIRD"]),
       vat_id_valid=P("boolean", "customer VAT ID validated"), digital=P("boolean", "digital/telecom service"), catalog_service=P("boolean", "§ 3a Abs. 4 catalogue service")))
 ,
 ("asset_suggest", "Suggest depreciation methods for a purchase.", _obj(cost=P("number", "net cost (gross for Kleinunternehmer)", True), kind=P("string", "computer|vehicle|other"), acquired=P("string", "YYYY-MM-DD"), electric=P("boolean", "e-vehicle"))),
 ("asset_add", "Add an asset to the client's register.", _obj(id=P("string", "short id", True), description=P("string", "", True), acquired=P("string", "YYYY-MM-DD", True), cost=P("number", "", True),
      method=P("string", "", True, enum=["linear", "degressive", "ecar75", "gwg", "computer", "sammelposten", "sofort"]), life_years=P("number", "useful life"), business_use_pct=P("number", "default 100"))),
 ("asset_register", "Asset register and EÜR depreciation lines for a year.", _obj(year=P("integer", "", True))),
 ("iab_add", "Record a § 7g investment deduction taken.", _obj(id=P("string", "", True), year=P("integer", "", True), amount=P("number", "", True), plan=P("string", "planned asset"))),
 ("iab_status", "Open § 7g deductions, deadlines, reversal warnings.", _obj(year=P("integer", "current tax year", True))),
 ("close_year", "Close a tax year: apply loss carry-forward and store figures. Only after the advisor has confirmed the year.", _obj(year=P("integer", "", True), gesamtbetrag=P("number", "Gesamtbetrag der Einkünfte", True), profit=P("number", "Gewinn"))),
 ("bescheid_deadline", "Objection deadline for a tax notice date.", _obj(date=P("string", "date on the notice YYYY-MM-DD", True))),
 ("bescheid_check", "Compare a tax notice with the filed return and recompute the tax.", _obj(notice=P("object", "notice figures (steuerjahr, zve, est, soli, kirchensteuer, vorauszahlungen, saldo, datum, vorbehalt_nachpruefung ...)", True), filed=P("object", "same keys from the return"))),
 ("einspruch_draft", "German objection letter draft saved to work/einspruch.md. Never send without the advisor.", _obj(notice=P("object", "steuerjahr, datum, steuernummer, finanzamt, absender", True), points=P("array", "reasons", items={"type": "string"}), suspend=P("boolean", "request suspension of payment"))),
 ("invoice_check", "Check an invoice (fields extracted from a receipt) against § 14 Abs. 4 UStG / § 33 UStDV.", _obj(invoice=P("object", "invoice fields", True), kleinunternehmer=P("boolean", "supplier is a Kleinunternehmer"))),
 ("bank_import", "Turn a bank CSV in inbox/ into a ledger CSV with category suggestions; lists lines needing a decision.",
  _obj(bank_file=P("string", "e.g. inbox/bank.csv", True), out_file=P("string", "e.g. work/ledger.csv", True), delimiter=P("string", "default ;"))),
 ("write_file", "Write a small json/csv/txt/md file into work/ (intake, ledger, notice).", _obj(path=P("string", "work/...", True), content=P("string", "", True))),
 ("read_file", "Read a small text file from the client folder.", _obj(path=P("string", "", True))),
 ("list_files", "List files in the client folder.", _obj(subdir=P("string", "inbox|work|packs|state"))),
 ("build_pack", "Build the Steuerberater review pack (markdown, EÜR lines, ledger, VAT, register, review checklist, Excel/CSV, draft booking CSV). Writes to packs/<timestamp>/.",
  _obj(intake_file=P("string", "e.g. work/intake.json", True), ledger_file=P("string", "e.g. work/ledger.csv", True), regular_vat=P("boolean", ""), vat_form=P("boolean", "include UStVA Kennzahlen"), use_state=P("boolean", "include asset register / IAB / loss carry-forward"), hebesatz=P("number", "trade tax Hebesatz in %"))),
 ("review_list", "Read-only: advisor review items and their status for a pack. You cannot change status or sign off; that is the advisor's role.", _obj(pack=P("string", "pack folder name under packs/", True))),
]
TOOLS = [{"name": n, "description": d, "input_schema": s} for n, d, s in SCHEMAS]
TOOLS[-1]["cache_control"] = {"type": "ephemeral"}      # cache the tool block (tools come first in the prefix)

def _law_file(law):
    return os.path.join(STAT, cite_check.LAWS[law] + ".md")

def _section(law, sec):
    return cite_check.sections(law).get(re.sub(r"\s+", " ", sec.strip()).replace("§§", "§"))

def search_statute(a, cid):
    q = re.compile(a["query"], re.I); n = int(a.get("max_results") or 8); out = []
    if a["law"] in ("UStAE", "BMF"):
        files = [os.path.join(config.SKILL_DIR, "references", "bmf", f) for f in sorted(os.listdir(os.path.join(config.SKILL_DIR, "references", "bmf"))) if f.endswith(".txt") and (a["law"] == "BMF") == (not f.startswith("ustae"))]
        for p in files:
            for i, line in enumerate(open(p, encoding="utf-8")):
                if q.search(line):
                    out.append({"file": os.path.basename(p), "line": i + 1, "text": line.strip().replace("\xa0", " ")[:300]})
                    if len(out) >= n: return out
        return out
    for sec, body in cite_check.sections(a["law"]).items():
        m = q.search(re.sub(r"\s+", " ", body))
        if m:
            flat = re.sub(r"\s+", " ", body).replace("\xa0", " "); s = max(m.start() - 150, 0)
            out.append({"section": f"{sec} {a['law']}", "snippet": flat[s:s + 450]})
            if len(out) >= n: break
    return out

def read_statute_section(a, cid):
    body = _section(a["law"], a["section"])
    if body is None: return {"error": f"{a['section']} not found in {a['law']}"}
    if a.get("absatz"):
        m = re.search(rf"(?ms)^\({re.escape(str(a['absatz']))}\)(.*?)(?=^\(\d+[a-z]?\)|\Z)", body)
        if not m: return {"error": f"Absatz {a['absatz']} not found"}
        body = f"({a['absatz']}){m.group(1)}"
    return {"law": a["law"], "section": a["section"], "text": body.replace("\xa0", " ").strip()[:12000]}

def read_playbook(a, cid):
    with open(os.path.join(config.SKILL_DIR, "playbooks", a["name"] + ".md"), encoding="utf-8") as fh: return fh.read()

def _cite(a, cid):
    r = cite_check.check(a["text"]); return {"results": [{"citation": c, "status": s, "why": w} for c, s, w in r], "invalid": sum(1 for _, s, _ in r if s == "INVALID")}

def tariff_estimate(a, cid):
    y = int(a.get("year") or 2026); j = bool(a.get("joint")); est = taxcalc.tariff(a["zve"], j, y); so = taxcalc.soli(est, j, y)
    ki = taxcalc.kirchensteuer(est, a["church_rate"]) if a.get("church_rate") else 0.0
    r = {"year": y, "est": est, "soli": so, "kirchensteuer": ki}
    if y == 2025: r["warning"] = "2025 tariff constants are reconstructed and unconfirmed; advisor must confirm"
    return r

def compute_eur(a, cid): return taxcalc.eur_from_ledger(safe_path(cid, a["ledger_file"]), bool(a.get("regular_vat")))
def compute_vat_return(a, cid): return ustva.compute(safe_path(cid, a["ledger_file"]), float(a.get("special_prepayment") or 0))

def vat_cross_border(a, cid):
    if a["direction"] == "sale":
        return ustva.sale(a["kind"], a.get("customer_type") or "B2B", a["region"], bool(a.get("vat_id_valid")), bool(a.get("digital")), bool(a.get("catalog_service")))
    return ustva.purchase(a["kind"], a["region"])

def _state(cid): return os.path.join(client_dir(cid), "state")
def asset_suggest(a, cid): return ST.classify_new(a["cost"], a.get("kind", "other"), bool(a.get("electric")), a.get("acquired"))
def asset_add(a, cid):
    s = ST.load(_state(cid)); 
    if any(x["id"] == a["id"] for x in s["assets"]): return {"error": "asset id exists"}
    rec = {k: a[k] for k in ("id", "description", "acquired", "cost", "method")}; rec["life_years"] = a.get("life_years"); rec["business_use_pct"] = a.get("business_use_pct", 100)
    ST.schedule(rec, int(rec["acquired"][:4]) + 1)          # validates method/date rules, raises ValueError
    s["assets"].append(rec); ST.save(_state(cid), s); return {"added": rec["id"]}
def asset_register(a, cid): return ST.register(ST.load(_state(cid)), int(a["year"]))
def iab_add(a, cid):
    s = ST.load(_state(cid)); s["iab"].append({"id": a["id"], "year": int(a["year"]), "amount": float(a["amount"]), "plan": a.get("plan", ""), "status": "open"}); ST.save(_state(cid), s); return {"added": a["id"]}
def iab_status(a, cid): return ST.iab_check(ST.load(_state(cid)), int(a["year"]))
def close_year(a, cid):
    s = ST.load(_state(cid)); r = ST.close_year(s, int(a["year"]), float(a["gesamtbetrag"]), profit=a.get("profit")); ST.save(_state(cid), s); return r

def bescheid_deadline(a, cid): return bescheid.deadline(a["date"])
def bescheid_check(a, cid): return bescheid.check(a["notice"], a.get("filed"))
def einspruch_draft(a, cid):
    txt = bescheid.draft(a["notice"], a.get("points") or [], bool(a.get("suspend")))
    p = safe_path(cid, "work/einspruch.md")
    with open(p, "w", encoding="utf-8") as fh: fh.write(txt)
    return {"saved": "work/einspruch.md", "text": txt}
def invoice_check_(a, cid): return invoice_check.check(a["invoice"], bool(a.get("kleinunternehmer")))

def bank_import(a, cid):
    src, dst = safe_path(cid, a["bank_file"]), safe_path(cid, a["out_file"]); check_ext(a["out_file"])
    r = subprocess.run([sys.executable, os.path.join(config.SKILL_DIR, "tools", "bank_import.py"), src, dst, "--delimiter", a.get("delimiter") or ";"], capture_output=True, text=True, timeout=60)
    return {"stdout": r.stdout[-4000:], "stderr": r.stderr[-1000:], "ok": r.returncode == 0}

def write_file(a, cid):
    if not a["path"].startswith("work/"): return {"error": "writes are limited to work/"}
    check_ext(a["path"]); 
    if len(a["content"]) > 200_000: return {"error": "file too large"}
    p = safe_path(cid, a["path"]); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh: fh.write(a["content"])
    return {"written": a["path"], "bytes": len(a["content"])}
def read_file(a, cid):
    check_ext(a["path"]); p = safe_path(cid, a["path"])
    if not os.path.isfile(p): return {"error": "not found"}
    with open(p, encoding="utf-8", errors="replace") as fh: return fh.read()[:MAX_RESULT]
def list_files(a, cid):
    sub = a.get("subdir") or "."; p = safe_path(cid, sub if sub != "." else "work"); base = os.path.realpath(client_dir(cid))
    return sorted(os.path.relpath(os.path.join(r, f), base) for r, _, fs in os.walk(os.path.dirname(p) if sub == "." else p) for f in fs)[:300]

def build_pack(a, cid):
    cd = client_dir(cid); intake, ledger = safe_path(cid, a["intake_file"]), safe_path(cid, a["ledger_file"])
    out = os.path.join(cd, "packs", dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    cmd = [sys.executable, os.path.join(config.SKILL_DIR, "tools", "build_pack.py"), intake, ledger, out]
    if a.get("regular_vat"): cmd.append("--regular-vat")
    if a.get("vat_form"): cmd.append("--vat-form")
    if a.get("use_state"): cmd += ["--state", os.path.join(cd, "state")]
    if a.get("hebesatz"): cmd += ["--hebesatz", str(a["hebesatz"])]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=os.path.join(config.SKILL_DIR, "tools"))
    pack = open(os.path.join(out, "review-pack.md"), encoding="utf-8").read() if os.path.exists(os.path.join(out, "review-pack.md")) else ""
    return {"ok": r.returncode == 0, "pack": os.path.relpath(out, cd), "log": (r.stdout + r.stderr)[-1500:], "review_pack_markdown": pack[:14000]}

def review_list(a, cid):
    d = safe_path(cid, os.path.join("packs", os.path.basename(a["pack"]))); return RV.load(d)["items"]

DISPATCH = {"search_statute": search_statute, "read_statute_section": read_statute_section, "read_playbook": read_playbook, "cite_check": _cite,
            "tariff_estimate": tariff_estimate, "compute_eur": compute_eur, "compute_vat_return": compute_vat_return, "vat_cross_border": vat_cross_border,
            "asset_suggest": asset_suggest, "asset_add": asset_add, "asset_register": asset_register, "iab_add": iab_add, "iab_status": iab_status, "close_year": close_year,
            "bescheid_deadline": bescheid_deadline, "bescheid_check": bescheid_check, "einspruch_draft": einspruch_draft, "invoice_check": invoice_check_,
            "bank_import": bank_import, "write_file": write_file, "read_file": read_file, "list_files": list_files, "build_pack": build_pack, "review_list": review_list}

def execute(name, args, client_id):
    """Run a tool; errors are returned to the model as text, never raised to the caller."""
    fn = DISPATCH.get(name)
    if fn is None: return json.dumps({"error": f"unknown tool {name}"}), True
    try:
        res = fn(args or {}, client_id)
        return (res if isinstance(res, str) else _s(res))[:MAX_RESULT + 100], False
    except Exception as e:                     # validation, sandbox, missing file ...
        return json.dumps({"error": f"{type(e).__name__}: {e}"}), True
