from __future__ import annotations

import io
import json
import os
import subprocess
import struct
import unittest
from pathlib import Path

from codex_work_gate.native_host import handle_message, read_message, write_message

ROOT = Path(__file__).resolve().parents[1]


class NativeHostTests(unittest.TestCase):
    def test_native_message_round_trip(self) -> None:
        source = {"action": "status"}
        encoded = json.dumps(source).encode("utf-8")
        stream = io.BytesIO(struct.pack("<I", len(encoded)) + encoded)
        self.assertEqual(read_message(stream), source)

        out = io.BytesIO()
        write_message({"ok": True}, out)
        out.seek(0)
        length = struct.unpack("<I", out.read(4))[0]
        payload = json.loads(out.read(length).decode("utf-8"))
        self.assertEqual(payload, {"ok": True})

    def test_unknown_action_blocks(self) -> None:
        response = handle_message({"action": "wat"})
        self.assertFalse(response["allowed"])
        self.assertIn("unknown_action", response["reason"])

    def test_native_host_runs_with_gui_style_python_path(self) -> None:
        source = {"action": "status"}
        encoded = json.dumps(source).encode("utf-8")
        env = {
            "HOME": str(Path.home()),
        }
        result = subprocess.run(
            [str(ROOT / "native-host" / "codex-work-gate-native")],
            input=struct.pack("<I", len(encoded)) + encoded,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertGreaterEqual(len(result.stdout), 4)
        length = struct.unpack("<I", result.stdout[:4])[0]
        payload = json.loads(result.stdout[4 : 4 + length].decode("utf-8"))
        self.assertIn("allowed", payload)


if __name__ == "__main__":
    unittest.main()
