from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import CONFIG_PATH


DEFAULT_CONFIG: dict[str, Any] = {
    "blockedHosts": [
        "youtube.com",
        "youtu.be",
        "netflix.com",
        "reddit.com",
        "x.com",
        "twitter.com",
        "instagram.com",
        "tiktok.com",
        "twitch.tv",
    ],
    "pollIntervalMs": 3000,
    "idleGraceMs": 10000,
    "ttlMs": 30000,
    "mode": "browser",
    "osLock": {"enabled": False},
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update(raw)
    if not isinstance(merged.get("blockedHosts"), list):
        merged["blockedHosts"] = list(DEFAULT_CONFIG["blockedHosts"])
    return merged


def write_default_config(path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
