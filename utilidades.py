"""Persistencia atómica y procedencia de ejecuciones."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parent

def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_state():
    def call(*args):
        try:
            return subprocess.check_output(["/usr/bin/git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    return {"commit": call("rev-parse", "HEAD"), "working_tree_status": call("status", "--porcelain"),
            "nota": "Un commit nulo o un árbol modificado no acredita una versión confirmada. Se guarda también la huella del pipeline."}
