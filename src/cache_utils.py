from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

CACHE_DIR = Path("results") / "cache"


def ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def build_cache_key(*parts: object) -> str:
    raw = "||".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def cache_path(namespace: str, key: str) -> Path:
    directory = ensure_cache_dir() / namespace
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{key}.json"


def load_json_cache(namespace: str, key: str) -> Any | None:
    path = cache_path(namespace, key)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_cache(namespace: str, key: str, payload: Any) -> Path:
    path = cache_path(namespace, key)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def clear_cache(namespace: str | None = None) -> None:
    base = ensure_cache_dir()
    target = base / namespace if namespace else base
    if target.exists():
        shutil.rmtree(target)
    if namespace is None:
        base.mkdir(parents=True, exist_ok=True)
