from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExtensionStaticTests(unittest.TestCase):
    def test_manifest_has_required_permissions(self) -> None:
        manifest = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("nativeMessaging", manifest["permissions"])
        self.assertIn("declarativeNetRequest", manifest["permissions"])
        self.assertIn("tabs", manifest["permissions"])
        self.assertIn("127.0.0.1", manifest["content_security_policy"]["extension_pages"])
        self.assertIn("key", manifest)

    def test_docs_mention_brave(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("brave://extensions", readme)

    def test_background_contains_default_blocked_hosts(self) -> None:
        source = (ROOT / "extension" / "background.js").read_text(encoding="utf-8")
        for host in ["youtube.com", "netflix.com", "reddit.com", "twitch.tv"]:
            self.assertIn(host, source)

    def test_background_redirects_existing_tabs(self) -> None:
        source = (ROOT / "extension" / "background.js").read_text(encoding="utf-8")
        self.assertIn("redirectOpenBlockedTabs", source)
        self.assertNotIn("chrome.tabs.onUpdated.addListener", source)
        self.assertNotIn("chrome.tabs.onActivated.addListener", source)

    def test_background_uses_loopback_status_fallback(self) -> None:
        source = (ROOT / "extension" / "background.js").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:18732/status", source)
        self.assertIn("queryNativeGate", source)


if __name__ == "__main__":
    unittest.main()
