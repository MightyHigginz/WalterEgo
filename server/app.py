"""HTTP API. Run: uvicorn app:app --host 127.0.0.1 --port 8080 (put TLS and a reverse proxy in front)."""
import json, logging, os
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import config, auth, store, tools, agent
from sandbox import client_dir, safe_path, check_ext, ID_RE
import review as RV   # via tools' sys.path

log = logging.getLogger("tax"); logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
app = FastAPI(title="DE Tax Suite", docs_url=None, redoc_url=None)
_client = None
def get_client():
    global _client
    if _client is None:
        import anthropic; _client = anthropic.Anthropic()       # ANTHROPIC_API_KEY from the environment
    return _client
PACK_FILES = {"review-pack.md", "eur-lines.csv", "advisor-workbook.xlsx", "datev-entwurf.csv", "ledger-annotated.csv", "register.json", "ustva.json", "review.json", "review-status.md", "citation-check.txt"}

def ident(authorization: str = Header(None)):
    i = auth.identify(authorization)
    if not i: raise HTTPException(401, "invalid token")
    if not auth.rate_ok(i["key"]): raise HTTPException(429, "too many requests")
    return i
def need(i, cid, roles=("client", "advisor", "admin")):
    if not ID_RE.match(cid) or not auth.allowed(i, cid, roles): raise HTTPException(403, "forbidden")

@app.get("/healthz")
def health(): return {"ok": True, "sources_refreshed": agent.sources_date(), "model": config.MODEL}

@app.post("/v1/clients/{cid}/messages")
def message(cid: str, body: dict = Body(...), i=Depends(ident)):
    need(i, cid, ("client", "admin"))
    text = (body.get("message") or "").strip()
    if not text or len(text) > 20000: raise HTTPException(400, "message required (max 20000 chars)")
    conv = body.get("conversation_id") or store.new_id(); hist = store.load(cid, conv)
    if len(hist) > 60: raise HTTPException(409, "conversation too long: start a new one (history is kept append-only)")
    try:
        res = agent.run_agent(get_client(), cid, hist + [{"role": "user", "content": agent.add_context(text)}])
    except Exception as e:
        import anthropic
        if isinstance(e, anthropic.RateLimitError): raise HTTPException(503, "model rate limit, retry later")
        if isinstance(e, anthropic.APIStatusError): log.error("api error %s", e.status_code); raise HTTPException(502, "model API error")
        raise
    store.save(cid, conv, res["messages"])
    log.info("client=%s conv=%s status=%s tools=%d in=%d out=%d", cid, conv[:8], res["status"], len(res["tool_calls"]), res["usage"]["input"], res["usage"]["output"])
    return {"conversation_id": conv, "answer": res["answer"], "status": res["status"], "tools_used": res["tool_calls"], "usage": res["usage"]}

@app.put("/v1/clients/{cid}/files/{name}")
async def upload(cid: str, name: str, request: Request, i=Depends(ident)):
    need(i, cid, ("client", "admin"))
    try: check_ext(name)
    except ValueError as e: raise HTTPException(400, str(e))
    if "/" in name or name.startswith("."): raise HTTPException(400, "bad file name")
    data = await request.body()
    if len(data) > config.MAX_UPLOAD: raise HTTPException(413, "file too large")
    open(safe_path(cid, os.path.join("inbox", name)), "wb").write(data); return {"saved": f"inbox/{name}", "bytes": len(data)}

@app.get("/v1/clients/{cid}/packs/{pack}/{fname}")
def download(cid: str, pack: str, fname: str, i=Depends(ident)):
    need(i, cid)
    if fname not in PACK_FILES or "/" in pack or pack.startswith("."): raise HTTPException(404)
    p = safe_path(cid, os.path.join("packs", pack, fname))
    if not os.path.isfile(p): raise HTTPException(404)
    return FileResponse(p, filename=fname)

@app.get("/v1/clients/{cid}/packs/{pack}/review")
def review_list(cid: str, pack: str, i=Depends(ident)):
    need(i, cid)
    try: return RV.load(safe_path(cid, os.path.join("packs", os.path.basename(pack))))
    except FileNotFoundError: raise HTTPException(404)

@app.post("/v1/clients/{cid}/packs/{pack}/review/{item}")
def review_set(cid: str, pack: str, item: str, body: dict = Body(...), i=Depends(ident)):
    need(i, cid, ("advisor", "admin"))
    try: return RV.set_status(safe_path(cid, os.path.join("packs", os.path.basename(pack))), item, body.get("status", ""), body.get("comment", ""), i["label"])
    except (ValueError, KeyError) as e: raise HTTPException(400, str(e))

@app.post("/v1/clients/{cid}/packs/{pack}/signoff")
def signoff(cid: str, pack: str, i=Depends(ident)):
    need(i, cid, ("advisor", "admin"))
    try: return RV.signoff(safe_path(cid, os.path.join("packs", os.path.basename(pack))), i["label"])
    except RuntimeError as e: raise HTTPException(409, str(e))
