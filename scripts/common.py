"""Shared helpers: the tool's home directory, the model API key, and album names."""
import os
import sys
from pathlib import Path

# Windows: piped output (as in Claude Code) uses the locale code page rather than UTF-8.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = Path(os.environ.get("GALLERY_SORTER_HOME", Path.home() / ".gallery-sorter"))
ENV_FILE = HOME / ".env"

ALBUM_NAMES = {
    "trip": "Trips",
    "family": "Family",
    "friends": "Friends and events",
    "food": "Food",
    "pets": "Pets",
    "work": "Work",
    "receipt": "Receipts and documents",
    "docs": "Receipts and documents",
    "saved": "Things I saved",
    "screens": "Screenshots",
    "memes": "Memes",
    "shopping": "Shopping",
    "nature": "Nature and scenery",
    "other": "Miscellaneous",
    "dupes": "Duplicates",
    "blurry": "Blurry",
}
REVIEW_FOLDER = "Review before deleting"
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def album_name(album_id):
    if album_id.startswith("trip:"):
        return "Trip · " + album_id[5:]
    return ALBUM_NAMES.get(album_id, album_id)


def read_env():
    """Keys from the environment or from ~/.gallery-sorter/.env (KEY=value lines)."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k].strip()
    return env


def provider():
    """Gemini when a key is set (the cheaper option), otherwise OpenAI. Returns (name, key)."""
    env = read_env()
    if env.get("GEMINI_API_KEY"):
        return "gemini", env["GEMINI_API_KEY"]
    if env.get("OPENAI_API_KEY"):
        return "openai", env["OPENAI_API_KEY"]
    raise SystemExit(f"Missing an API key. Save one line in {ENV_FILE}: GEMINI_API_KEY=your-key (or OPENAI_API_KEY=your-key)")
