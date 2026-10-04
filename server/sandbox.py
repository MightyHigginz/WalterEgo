"""Per-client sandbox: every file the tools touch lives under DATA_ROOT/<client_id>/. No shell for the model."""
import os, re
from config import DATA_ROOT

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,39}$")
ALLOWED_EXT = {".csv", ".json", ".txt", ".md", ".xlsx"}
SUBDIRS = ("inbox", "work", "packs", "state", "conversations")

def client_dir(client_id, create=True):
    if not ID_RE.match(client_id or ""):
        raise ValueError("invalid client id")
    d = os.path.join(DATA_ROOT, client_id)
    if create:
        for s in SUBDIRS: os.makedirs(os.path.join(d, s), exist_ok=True)
    return d

def safe_path(client_id, rel, create=True):
    """Resolve rel inside the client folder or raise. Blocks absolute paths, '..' and symlink escapes."""
    base = os.path.realpath(client_dir(client_id, create))
    if not rel or os.path.isabs(rel) or "\x00" in rel:
        raise ValueError("path must be relative to the client folder")
    p = os.path.realpath(os.path.join(base, rel))
    if p != base and not p.startswith(base + os.sep):
        raise ValueError("path escapes the client folder")
    return p

def check_ext(name):
    if os.path.splitext(name)[1].lower() not in ALLOWED_EXT:
        raise ValueError("file type not allowed: " + os.path.splitext(name)[1])
