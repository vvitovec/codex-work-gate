#!/usr/bin/python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(os.environ.get("CODEX_WORK_GATE_HOME", "~/.codex-work-gate")).expanduser()
STATUS_PATH = Path(os.environ.get("CODEX_WORK_GATE_STATUS", APP_DIR / "status.json")).expanduser()
DEFAULT_TTL_MS = 30000
ACTIVE_EVENTS = {"UserPromptSubmit", "PreToolUse", "PostToolUse"}
WAITING_EVENTS = {"PermissionRequest"}
STOP_EVENTS = {"Stop", "SubagentStop"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_previous() -> dict | None:
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def atomic_write(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{STATUS_PATH.name}.", suffix=".tmp", dir=str(STATUS_PATH.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, STATUS_PATH)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def should_preserve_newer_active(previous: dict | None, next_state: str, timestamp: str) -> bool:
    if not previous or next_state not in {"idle", "completed", "waitingOnApproval"}:
        return False
    if previous.get("state") != "active":
        return False
    previous_active = parse_iso(previous.get("lastActiveAt"))
    current = parse_iso(timestamp)
    return bool(previous_active and current and previous_active > current)


def status_for_event(event: str, previous: dict | None, timestamp: str) -> dict:
    if event in ACTIVE_EVENTS:
        state = "active"
        last_active = timestamp
    elif event in WAITING_EVENTS:
        state = "waitingOnApproval"
        last_active = previous.get("lastActiveAt") if previous else timestamp
    elif event in STOP_EVENTS:
        state = "idle"
        last_active = previous.get("lastActiveAt") if previous else timestamp
    else:
        state = previous.get("state", "unknown") if previous else "unknown"
        last_active = previous.get("lastActiveAt") if previous else timestamp

    if should_preserve_newer_active(previous, state, timestamp):
        merged = dict(previous)
        merged.update({"lastEvent": event, "updatedAt": timestamp, "ignoredOlderTerminalEvent": True})
        return merged

    return {
        "state": state,
        "lastEvent": event,
        "lastActiveAt": last_active,
        "updatedAt": timestamp,
        "threadId": os.environ.get("CODEX_THREAD_ID"),
        "sessionId": os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_CONVERSATION_ID"),
        "cwd": os.getcwd(),
        "ttlMs": int((previous or {}).get("ttlMs") or DEFAULT_TTL_MS),
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: work_gate_hook.py EVENT", file=sys.stderr)
        return 2
    timestamp = now_iso()
    previous = read_previous()
    atomic_write(status_for_event(argv[0], previous, timestamp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
