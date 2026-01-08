"""Helpers for caching language scan metadata and results."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app import settings


def _cache_path() -> Path:
    return settings.get_data_dir() / "language_snapshot.json"


def build_signature(folders: Iterable[str]) -> str:
    entries: List[Dict[str, object]] = []
    for raw_path in sorted(set(folders)):
        path = os.path.abspath(raw_path)
        try:
            stat = os.stat(path)
            # Count files in folder for better invalidation detection
            # (catches file additions/deletions that may not change folder mtime)
            try:
                file_count = sum(1 for _ in Path(path).rglob('*') if _.is_file())
            except (OSError, PermissionError):
                file_count = -1
            entries.append(
                {
                    "path": path,
                    "mtime": stat.st_mtime_ns,
                    "size": stat.st_size,
                    "file_count": file_count,
                }
            )
        except FileNotFoundError:
            entries.append({"path": path, "missing": True})
    payload = json.dumps(entries, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_cached_snapshot() -> Optional[Tuple[str, Dict[str, List[str]]]]:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    signature = data.get("signature")
    language_files = data.get("language_files")
    if not isinstance(signature, str) or not isinstance(language_files, dict):
        return None
    normalised: Dict[str, List[str]] = {}
    for key, value in language_files.items():
        if isinstance(key, str) and isinstance(value, list):
            normalised[key] = [str(item) for item in value]
    return signature, normalised


def save_snapshot(signature: str, language_files: Dict[str, List[str]]) -> None:
    path = _cache_path()
    payload = {"signature": signature, "language_files": language_files}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh)
