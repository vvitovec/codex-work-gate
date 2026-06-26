from __future__ import annotations

import io
import json
import struct
import unittest

from codex_work_gate.native_host import handle_message, read_message, write_message


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


if __name__ == "__main__":
    unittest.main()
