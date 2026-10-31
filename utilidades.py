"""Persistencia atómica y procedencia de ejecuciones."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import os
from contextlib import contextmanager
import fcntl
ROOT = Path(__file__).resolve().parent


@contextmanager
def store_lock(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with (output/'.pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)

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
    return {"commit": os.environ.get('LAB_GIT_COMMIT') or call("rev-parse", "HEAD"), "working_tree_status": call("status", "--porcelain"),
            "nota": "Un commit nulo o un árbol modificado no acredita una versión confirmada. Se guarda también la huella del pipeline."}
