"""Helpers for caching language scan metadata and results."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app import settings


def _cache_path() -> Path:
    from app.portable_data import get_data_manager
    return get_data_manager().get_active_profile_dir() / "language_snapshot.json"


def build_signature(folders: Iterable[str]) -> str:
    """Fast signature based on folder paths, mtimes, and ignore settings."""
    entries: List[Dict[str, object]] = []
    
    # 1. Include folder metadata
    for raw_path in sorted(set(folders)):
        path = os.path.abspath(raw_path)
        try:
            stat = os.stat(path)
            entries.append({
                "path": path,
                "mtime": stat.st_mtime_ns,
                "size": stat.st_size
            })
        except FileNotFoundError:
            entries.append({"path": path, "missing": True})
            
    # 2. Include ignore settings (if they change, we MUST re-scan)
    raw_files = settings.get_setting("ignored_files", "")
    raw_folders = settings.get_setting("ignored_folders", "")
    entries.append({"ignored_files": raw_files, "ignored_folders": raw_folders})
    
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
