"""Bearer-token auth. tokens.json maps sha256(token) -> {"role": "client|advisor|admin", "label": "...", "clients": ["id", ...]}.
Create entries with `python3 make_token.py ROLE LABEL CLIENT...`. Tokens themselves are never stored."""
import hashlib, hmac, json, os, time
import config

def _load():
    return json.load(open(config.TOKENS_FILE)) if os.path.exists(config.TOKENS_FILE) else {}
def identify(header):
    if not header or not header.startswith("Bearer "): return None
    h = hashlib.sha256(header[7:].strip().encode()).hexdigest(); tokens = _load()
    for k, v in tokens.items():
        if hmac.compare_digest(k, h): return {**v, "key": h[:12]}
    return None
def allowed(ident, client_id, roles=("client", "advisor", "admin")):
    return bool(ident) and ident["role"] in roles and (ident["role"] == "admin" or client_id in ident.get("clients", []))

_hits = {}
def rate_ok(key, limit=30, window=60):
    now = time.time(); q = [t for t in _hits.get(key, []) if now - t < window]; ok = len(q) < limit
    if ok: q.append(now)
    _hits[key] = q; return ok
