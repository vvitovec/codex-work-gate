from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DEFAULT_CONFIG
from .paths import STATUS_PATH


ACTIVE_EVENTS = {"UserPromptSubmit", "PreToolUse", "PostToolUse"}
WAITING_EVENTS = {"PermissionRequest"}
STOP_EVENTS = {"Stop", "SubagentStop"}
BLOCKING_STATES = {"idle", "completed", "waitingOnApproval", "unknown"}


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def read_status(path: Path = STATUS_PATH) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError:
        return None, "invalid_json"
    except OSError as exc:
        return None, f"read_error:{exc.__class__.__name__}"


def _metadata_from_env() -> dict[str, Any]:
    return {
        "threadId": os.environ.get("CODEX_THREAD_ID"),
        "sessionId": os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_CONVERSATION_ID"),
        "cwd": os.getcwd(),
    }


def _should_preserve_newer_active(
    previous: dict[str, Any] | None, next_state: str, timestamp: str
) -> bool:
    if not previous:
        return False
    if next_state not in {"idle", "completed", "waitingOnApproval"}:
        return False
    if previous.get("state") != "active":
        return False
    previous_active = parse_iso(previous.get("lastActiveAt"))
    current = parse_iso(timestamp)
    if not previous_active or not current:
        return False
    return previous_active > current


def status_for_event(
    event: str,
    previous: dict[str, Any] | None = None,
    timestamp: str | None = None,
    ttl_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = timestamp or now_iso()
    if ttl_ms is None:
        ttl_ms = int(previous.get("ttlMs") if previous else DEFAULT_CONFIG["ttlMs"])
    else:
        ttl_ms = int(ttl_ms)
    metadata = metadata or _metadata_from_env()

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

    if previous and _should_preserve_newer_active(previous, state, timestamp):
        merged = dict(previous)
        merged.update(
            {
                "lastEvent": event,
                "updatedAt": timestamp,
                "ignoredOlderTerminalEvent": True,
            }
        )
        return merged

    return {
        "state": state,
        "lastEvent": event,
        "lastActiveAt": last_active,
        "updatedAt": timestamp,
        "threadId": metadata.get("threadId"),
        "sessionId": metadata.get("sessionId"),
        "cwd": metadata.get("cwd"),
        "ttlMs": ttl_ms,
    }


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    state: str
    reason: str
    checked_at: str
    status: dict[str, Any] | None

    def as_json(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "state": self.state,
            "reason": self.reason,
            "checkedAt": self.checked_at,
            "status": self.status,
        }


def decide_gate(
    status: dict[str, Any] | None,
    read_error: str | None = None,
    checked_at: str | None = None,
) -> GateDecision:
    checked_at = checked_at or now_iso()
    if status is None:
        return GateDecision(False, "unknown", read_error or "missing", checked_at, None)

    state = str(status.get("state") or "unknown")
    if state != "active":
        return GateDecision(False, state, f"state:{state}", checked_at, status)

    last_active = parse_iso(status.get("lastActiveAt"))
    checked = parse_iso(checked_at)
    if not last_active or not checked:
        return GateDecision(False, state, "invalid_timestamp", checked_at, status)

    ttl_ms = int(status.get("ttlMs") or DEFAULT_CONFIG["ttlMs"])
    age_ms = (checked - last_active).total_seconds() * 1000
    if age_ms > ttl_ms:
        return GateDecision(False, state, "expired", checked_at, status)

    return GateDecision(True, state, "active", checked_at, status)


def write_event(event: str, path: Path = STATUS_PATH) -> dict[str, Any]:
    previous, _ = read_status(path)
    next_status = status_for_event(event, previous=previous)
    atomic_write_json(path, next_status)
    return next_status


def main_hook(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: work_gate_hook.py EVENT", file=sys.stderr)
        return 2
    write_event(argv[0])
    return 0
