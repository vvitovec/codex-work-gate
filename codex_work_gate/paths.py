from __future__ import annotations

import os
from pathlib import Path


APP_DIR = Path(os.environ.get("CODEX_WORK_GATE_HOME", "~/.codex-work-gate")).expanduser()
LIB_DIR = APP_DIR / "lib"
STATUS_PATH = Path(os.environ.get("CODEX_WORK_GATE_STATUS", APP_DIR / "status.json")).expanduser()
CONFIG_PATH = Path(
    os.environ.get("CODEX_WORK_GATE_CONFIG", "~/.config/codex-work-gate/config.json")
).expanduser()
HOOKS_DIR = APP_DIR / "hooks"
HOOK_WRITER_PATH = HOOKS_DIR / "work_gate_hook.py"
NATIVE_HOST_DIR = APP_DIR / "native-host"
NATIVE_HOST_PATH = NATIVE_HOST_DIR / "codex-work-gate-native"
SERVER_DIR = APP_DIR / "server"
SERVER_PATH = SERVER_DIR / "codex-work-gate-server"
LAUNCH_AGENT_PATH = Path("~/Library/LaunchAgents/com.vvitovec.codex-work-gate.plist").expanduser()
CODEX_HOOKS_PATH = Path(os.environ.get("CODEX_HOOKS_PATH", "~/.codex/hooks.json")).expanduser()
CHROME_NATIVE_HOST_DIR = Path(
    "~/Library/Application Support/Google/Chrome/NativeMessagingHosts"
).expanduser()
BRAVE_NATIVE_HOST_DIR = Path(
    "~/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
).expanduser()
NATIVE_HOST_NAME = "com.vvitovec.codex_work_gate"
NATIVE_HOST_MANIFEST = CHROME_NATIVE_HOST_DIR / f"{NATIVE_HOST_NAME}.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
