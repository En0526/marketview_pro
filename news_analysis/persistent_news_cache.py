"""聲量／盤前快取寫入專案根目錄 .cache/，程式重啟後 1 小時內仍可不重抓。"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

CACHE_ROOT = Path(__file__).resolve().parent.parent / ".cache"
TTL_SEC = 3600


def _ensure_dir() -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)


def _path(name: str) -> Path:
    return CACHE_ROOT / f"{name}.json"


def load_entry(name: str) -> Optional[Dict[str, Any]]:
    p = _path(name)
    if not p.is_file():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            blob = json.load(f)
        saved = float(blob.get("saved_at", 0))
        if (time.time() - saved) >= TTL_SEC:
            return None
        return blob.get("payload")
    except Exception:
        return None


def load_entry_saved_at(name: str) -> Optional[float]:
    """回傳快取檔的 saved_at（unix ts），若無效則 None。"""
    p = _path(name)
    if not p.is_file():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            blob = json.load(f)
        saved = float(blob.get("saved_at", 0))
        if (time.time() - saved) >= TTL_SEC:
            return None
        return saved
    except Exception:
        return None


def save_entry(name: str, payload: Dict[str, Any]) -> None:
    try:
        _ensure_dir()
        with open(_path(name), "w", encoding="utf-8") as f:
            json.dump({"saved_at": time.time(), "payload": payload}, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


def normalize_premarket_payload(d: Dict[str, Any]) -> Dict[str, Any]:
    """盤前結果寫入 JSON 前，將 datetime 轉成字串。"""
    import copy

    out = copy.deepcopy(d)
    for n in out.get("news") or []:
        if not isinstance(n, dict):
            continue
        pt = n.get("published_at")
        if isinstance(pt, datetime):
            n["published_at"] = pt.isoformat()
    return out
