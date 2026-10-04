"""Conversation storage per client (JSON files). Assistant content is stored exactly as returned, because thinking blocks must be
passed back unchanged on the same model."""
import json, os, re, uuid
from sandbox import client_dir

def _p(cid, conv):
    if not re.match(r"^[a-f0-9-]{8,40}$", conv): raise ValueError("bad conversation id")
    return os.path.join(client_dir(cid), "conversations", conv + ".json")
def new_id(): return uuid.uuid4().hex
def load(cid, conv):
    p = _p(cid, conv); return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
def save(cid, conv, messages):
    p = _p(cid, conv); tmp = p + ".tmp"; json.dump(messages, open(tmp, "w", encoding="utf-8"), ensure_ascii=False); os.replace(tmp, p)
