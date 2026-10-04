"""Server configuration (environment variables)."""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.environ.get("TAX_SKILL_DIR") or os.path.normpath(os.path.join(ROOT, "..", ".claude", "skills", "de-freelancer-tax"))
DATA_ROOT = os.environ.get("TAX_DATA_ROOT", os.path.join(ROOT, "data"))   # one folder per client; never inside git
MODEL = os.environ.get("TAX_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("TAX_EFFORT", "high")                              # low|medium|high|xhigh|max
MAX_TOKENS = int(os.environ.get("TAX_MAX_TOKENS", "16000"))
MAX_TURNS = int(os.environ.get("TAX_MAX_TURNS", "14"))                    # tool-loop iterations per request
FALLBACKS = os.environ.get("TAX_FALLBACKS", "1") == "1"                    # server-side refusal fallback (beta header)
MAX_UPLOAD = int(os.environ.get("TAX_MAX_UPLOAD", str(5 * 1024 * 1024)))
TOKENS_FILE = os.environ.get("TAX_TOKENS_FILE", os.path.join(ROOT, "tokens.json"))
