"""Load local settings without requiring a database connection."""
from pathlib import Path
import os

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_local_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
