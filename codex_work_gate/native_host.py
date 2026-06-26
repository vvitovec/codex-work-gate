from __future__ import annotations

import json
import struct
import sys
from typing import Any, BinaryIO

from .config import load_config
from .heartbeat import decide_gate, now_iso, read_status
from .paths import STATUS_PATH


def read_message(stdin: BinaryIO = sys.stdin.buffer) -> dict[str, Any] | None:
    raw_length = stdin.read(4)
    if not raw_length:
        return None
    if len(raw_length) != 4:
        raise ValueError("incomplete native message length")
    message_length = struct.unpack("<I", raw_length)[0]
    if message_length > 1024 * 1024:
        raise ValueError("native message too large")
    payload = stdin.read(message_length)
    if len(payload) != message_length:
        raise ValueError("incomplete native message payload")
    return json.loads(payload.decode("utf-8"))


def write_message(message: dict[str, Any], stdout: BinaryIO = sys.stdout.buffer) -> None:
    encoded = json.dumps(message, separators=(",", ":")).encode("utf-8")
    stdout.write(struct.pack("<I", len(encoded)))
    stdout.write(encoded)
    stdout.flush()


def build_status_response() -> dict[str, Any]:
    status, error = read_status(STATUS_PATH)
    decision = decide_gate(status, error, now_iso()).as_json()
    config = load_config()
    decision["blockedHosts"] = config["blockedHosts"]
    decision["pollIntervalMs"] = config["pollIntervalMs"]
    return decision


def handle_message(message: dict[str, Any] | None) -> dict[str, Any]:
    action = (message or {}).get("action", "status")
    if action == "status":
        return build_status_response()
    return {
        "allowed": False,
        "state": "unknown",
        "reason": f"unknown_action:{action}",
        "checkedAt": now_iso(),
    }


def serve() -> int:
    message = read_message()
    if message is None:
        return 0
    write_message(handle_message(message))
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
