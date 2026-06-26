from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from codex_work_gate.heartbeat import (
    atomic_write_json,
    decide_gate,
    read_status,
    status_for_event,
)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


class HeartbeatTests(unittest.TestCase):
    def test_user_prompt_submit_marks_active(self) -> None:
        status = status_for_event(
            "UserPromptSubmit",
            timestamp="2026-06-26T09:30:00.000Z",
            metadata={"threadId": "thr", "sessionId": "ses", "cwd": "/tmp/project"},
        )
        self.assertEqual(status["state"], "active")
        self.assertEqual(status["lastEvent"], "UserPromptSubmit")
        self.assertEqual(status["lastActiveAt"], "2026-06-26T09:30:00.000Z")
        self.assertEqual(status["cwd"], "/tmp/project")

    def test_tool_events_refresh_last_active(self) -> None:
        previous = status_for_event("UserPromptSubmit", timestamp="2026-06-26T09:30:00.000Z")
        status = status_for_event("PostToolUse", previous=previous, timestamp="2026-06-26T09:30:03.000Z")
        self.assertEqual(status["state"], "active")
        self.assertEqual(status["lastActiveAt"], "2026-06-26T09:30:03.000Z")

    def test_permission_request_blocks_without_refreshing_active(self) -> None:
        previous = status_for_event("PreToolUse", timestamp="2026-06-26T09:30:00.000Z")
        status = status_for_event("PermissionRequest", previous=previous, timestamp="2026-06-26T09:30:05.000Z")
        self.assertEqual(status["state"], "waitingOnApproval")
        self.assertEqual(status["lastActiveAt"], "2026-06-26T09:30:00.000Z")
        decision = decide_gate(status, checked_at="2026-06-26T09:30:06.000Z")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "state:waitingOnApproval")

    def test_stop_marks_idle(self) -> None:
        previous = status_for_event("PostToolUse", timestamp="2026-06-26T09:30:00.000Z")
        status = status_for_event("Stop", previous=previous, timestamp="2026-06-26T09:30:10.000Z")
        self.assertEqual(status["state"], "idle")
        self.assertFalse(decide_gate(status, checked_at="2026-06-26T09:30:11.000Z").allowed)

    def test_stale_active_expires(self) -> None:
        status = status_for_event("PreToolUse", timestamp="2026-06-26T09:30:00.000Z", ttl_ms=30000)
        decision = decide_gate(status, checked_at="2026-06-26T09:30:31.000Z")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "expired")

    def test_recent_active_allows(self) -> None:
        status = status_for_event("PreToolUse", timestamp="2026-06-26T09:30:00.000Z", ttl_ms=30000)
        decision = decide_gate(status, checked_at="2026-06-26T09:30:20.000Z")
        self.assertTrue(decision.allowed)

    def test_malformed_json_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.json"
            path.write_text("{", encoding="utf-8")
            status, error = read_status(path)
        self.assertIsNone(status)
        self.assertEqual(error, "invalid_json")

    def test_atomic_write_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.json"
            atomic_write_json(path, {"state": "active"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["state"], "active")

    def test_older_stop_does_not_override_newer_active(self) -> None:
        active_time = datetime(2026, 6, 26, 9, 30, 10, tzinfo=timezone.utc)
        previous = status_for_event("PreToolUse", timestamp=iso(active_time))
        status = status_for_event("Stop", previous=previous, timestamp=iso(active_time - timedelta(seconds=5)))
        self.assertEqual(status["state"], "active")
        self.assertTrue(status["ignoredOlderTerminalEvent"])


if __name__ == "__main__":
    unittest.main()
