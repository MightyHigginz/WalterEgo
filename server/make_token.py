#!/usr/bin/env python3
"""python3 make_token.py ROLE LABEL [CLIENT_ID ...]  -> prints the token ONCE and adds its hash to tokens.json."""
import hashlib, json, os, secrets, sys
import config
role, label, clients = sys.argv[1], sys.argv[2], sys.argv[3:]
assert role in ("client", "advisor", "admin")
tok = secrets.token_urlsafe(32); t = json.load(open(config.TOKENS_FILE)) if os.path.exists(config.TOKENS_FILE) else {}
t[hashlib.sha256(tok.encode()).hexdigest()] = {"role": role, "label": label, "clients": clients}
json.dump(t, open(config.TOKENS_FILE, "w"), indent=1); os.chmod(config.TOKENS_FILE, 0o600)
print("TOKEN (shown once):", tok)
