"""The value registry: every tracked number and its history, in .stalecheck/results.json.

Commit this file. Its history is what lets stalecheck say *which* run changed a number.
"""

from __future__ import annotations

import inspect
import json
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

STORE_ENV = "STALECHECK_STORE"
STORE_DIR = ".stalecheck"
STORE_FILE = "results.json"
KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def find_store(start: Path | str | None = None) -> Path:
    """$STALECHECK_STORE, else the nearest .stalecheck/ walking up from `start`, else start/.stalecheck/."""
    if os.environ.get(STORE_ENV):
        return Path(os.environ[STORE_ENV])
    here = Path(start or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    for d in (here, *here.parents):
        if (d / STORE_DIR).is_dir():
            return d / STORE_DIR / STORE_FILE
    return here / STORE_DIR / STORE_FILE


def load(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict[str, list[dict]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def git_commit(cwd: Path) -> str | None:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=cwd, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{sha}-dirty" if dirty else sha


def record(key: str, value: float, *, store: Path, source: str | None = None, commit: str | None = None) -> bool:
    """Append `value` to `key`'s history if it changed. Returns True if a new entry was written."""
    if not KEY_RE.match(key):
        raise ValueError(f"invalid key {key!r}: use letters, digits, and _ . : -")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key}: expected a number, got {type(value).__name__}")
    if not math.isfinite(value):
        raise ValueError(f"{key}: value must be finite, got {value}")
    data = load(store)
    history = data.setdefault(key, [])
    if history and history[-1]["value"] == value:
        return False
    history.append({
        "value": value,
        "commit": commit,
        "source": source,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    save(store, data)
    return True


def track(key: str, value: float, *, store: Path | str | None = None) -> float:
    """Register a number your manuscript reports. Returns `value` so it can be used inline:

        acc = track("main_acc", accuracy_score(y, y_hat))
    """
    caller = inspect.stack()[1]
    caller_file = Path(caller.filename).resolve()
    store_path = Path(store) if store else find_store()
    try:
        source = f"{caller_file.relative_to(store_path.parent.parent)}:{caller.lineno}"
    except ValueError:
        source = f"{caller_file.name}:{caller.lineno}"
    record(key, value, store=store_path, source=source, commit=git_commit(caller_file.parent))
    return value
