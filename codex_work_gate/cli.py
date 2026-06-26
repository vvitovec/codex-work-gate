from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import DEFAULT_CONFIG, load_config, write_default_config
from .heartbeat import decide_gate, now_iso, read_status, write_event
from .http_server import DEFAULT_HOST, DEFAULT_PORT, serve_http
from .paths import (
    APP_DIR,
    BRAVE_NATIVE_HOST_DIR,
    CHROME_NATIVE_HOST_DIR,
    CODEX_HOOKS_PATH,
    CONFIG_PATH,
    HOOK_WRITER_PATH,
    LAUNCH_AGENT_PATH,
    LIB_DIR,
    NATIVE_HOST_PATH,
    NATIVE_HOST_MANIFEST,
    NATIVE_HOST_NAME,
    SERVER_PATH,
    STATUS_PATH,
    repo_root,
)

EXTENSION_ID = "idfgjomaacpinnidblmackdpfnacipja"


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def status_command(_: argparse.Namespace) -> int:
    status, error = read_status(STATUS_PATH)
    print_json(decide_gate(status, error, now_iso()).as_json())
    return 0


def event_command(args: argparse.Namespace) -> int:
    payload = write_event(args.event, STATUS_PATH)
    print_json(payload)
    return 0


def _hook_command(event: str) -> str:
    return f'/usr/bin/python3 "{HOOK_WRITER_PATH}" {event}'


def _hook_entry(event: str) -> list[dict[str, Any]]:
    return [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": _hook_command(event),
                    "timeout": 5,
                    "statusMessage": "Updating Codex Work Gate",
                }
            ]
        }
    ]


def build_hooks_config(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    config = dict(existing or {})
    hooks = dict(config.get("hooks") or {})
    for event in ["UserPromptSubmit", "PreToolUse", "PostToolUse", "PermissionRequest", "Stop"]:
        entries = [
            entry
            for entry in hooks.get(event, [])
            if NATIVE_HOST_NAME not in json.dumps(entry, sort_keys=True)
            and "codex-work-gate" not in json.dumps(entry, sort_keys=True)
        ]
        entries.extend(_hook_entry(event))
        hooks[event] = entries
    config["hooks"] = hooks
    return config


def write_hook_script() -> None:
    HOOK_WRITER_PATH.parent.mkdir(parents=True, exist_ok=True)
    source = repo_root() / "hooks" / "work_gate_hook.py"
    shutil.copy2(source, HOOK_WRITER_PATH)
    current = HOOK_WRITER_PATH.stat().st_mode
    HOOK_WRITER_PATH.chmod(current | stat.S_IXUSR)


def write_runtime_package() -> None:
    package_source = repo_root() / "codex_work_gate"
    package_target = LIB_DIR / "codex_work_gate"
    if package_target.exists():
        shutil.rmtree(package_target)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        package_source,
        package_target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def write_native_host_launcher() -> None:
    NATIVE_HOST_PATH.parent.mkdir(parents=True, exist_ok=True)
    root = str(LIB_DIR.resolve())
    log_path = str((NATIVE_HOST_PATH.parent / "native-host.log").resolve())
    launcher = f"""#!/usr/bin/python3
from __future__ import annotations

import datetime
import traceback
import sys

sys.path.insert(0, {root!r})

from codex_work_gate.native_host import serve

LOG_PATH = {log_path!r}

def log(message: str) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            stamp = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            handle.write(f"{{stamp}} {{message}}\\n")
    except OSError:
        pass

if __name__ == "__main__":
    log("start")
    try:
        code = serve()
    except Exception:
        log("error " + traceback.format_exc().replace("\\n", "\\\\n"))
        raise
    log(f"exit {{code}}")
    raise SystemExit(code)
"""
    NATIVE_HOST_PATH.write_text(launcher, encoding="utf-8")
    current = NATIVE_HOST_PATH.stat().st_mode
    NATIVE_HOST_PATH.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_server_launcher() -> None:
    SERVER_PATH.parent.mkdir(parents=True, exist_ok=True)
    root = str(LIB_DIR.resolve())
    launcher = f"""#!/usr/bin/python3
from __future__ import annotations

import sys

sys.path.insert(0, {root!r})

from codex_work_gate.http_server import serve_http

if __name__ == "__main__":
    serve_http()
"""
    SERVER_PATH.write_text(launcher, encoding="utf-8")
    current = SERVER_PATH.stat().st_mode
    SERVER_PATH.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_launch_agent() -> None:
    LAUNCH_AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.vvitovec.codex-work-gate</string>
  <key>ProgramArguments</key>
  <array>
    <string>{SERVER_PATH}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{APP_DIR / "server.log"}</string>
  <key>StandardErrorPath</key>
  <string>{APP_DIR / "server.err.log"}</string>
</dict>
</plist>
"""
    LAUNCH_AGENT_PATH.write_text(plist, encoding="utf-8")


def restart_launch_agent() -> None:
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(LAUNCH_AGENT_PATH)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(LAUNCH_AGENT_PATH)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def install_hooks() -> None:
    existing: dict[str, Any] | None = None
    if CODEX_HOOKS_PATH.exists():
        existing = json.loads(CODEX_HOOKS_PATH.read_text(encoding="utf-8"))
    CODEX_HOOKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CODEX_HOOKS_PATH.write_text(
        json.dumps(build_hooks_config(existing), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def native_host_manifest(extension_id: str = EXTENSION_ID) -> dict[str, Any]:
    return {
        "name": NATIVE_HOST_NAME,
        "description": "Codex Work Gate native host",
        "path": str(NATIVE_HOST_PATH.resolve()),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }


def browser_native_host_dirs(browsers: list[str]) -> dict[str, Path]:
    all_dirs = {
        "chrome": CHROME_NATIVE_HOST_DIR,
        "brave": BRAVE_NATIVE_HOST_DIR,
    }
    if "all" in browsers:
        return all_dirs
    return {name: all_dirs[name] for name in browsers if name in all_dirs}


def install_native_hosts(extension_id: str = EXTENSION_ID, browsers: list[str] | None = None) -> dict[str, Path]:
    targets = browser_native_host_dirs(browsers or ["chrome"])
    written: dict[str, Path] = {}
    for browser, directory in targets.items():
        directory.mkdir(parents=True, exist_ok=True)
        manifest_path = directory / f"{NATIVE_HOST_NAME}.json"
        manifest_path.write_text(
            json.dumps(native_host_manifest(extension_id), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written[browser] = manifest_path
    return written


def install_native_host(extension_id: str = EXTENSION_ID) -> None:
    CHROME_NATIVE_HOST_DIR.mkdir(parents=True, exist_ok=True)
    NATIVE_HOST_MANIFEST.write_text(
        json.dumps(native_host_manifest(extension_id), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def install_command(args: argparse.Namespace) -> int:
    write_default_config(CONFIG_PATH)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    write_runtime_package()
    write_hook_script()
    write_native_host_launcher()
    write_server_launcher()
    write_launch_agent()
    restart_launch_agent()
    install_hooks()
    native_hosts = install_native_hosts(args.extension_id, args.browser)
    browser_pages = {
        "chrome": "chrome://extensions",
        "brave": "brave://extensions",
    }
    extension_pages = [browser_pages[name] for name in native_hosts if name in browser_pages]
    print_json(
        {
            "installed": True,
            "browsers": sorted(native_hosts.keys()),
            "config": str(CONFIG_PATH),
            "status": str(STATUS_PATH),
            "hooks": str(CODEX_HOOKS_PATH),
            "hookWriter": str(HOOK_WRITER_PATH),
            "nativeHost": str(NATIVE_HOST_PATH),
            "server": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/status",
            "serverLaunchAgent": str(LAUNCH_AGENT_PATH),
            "nativeHostManifests": {browser: str(path) for browser, path in native_hosts.items()},
            "extensionId": args.extension_id,
            "extensionPath": str((repo_root() / "extension").resolve()),
            "nextStep": f"Open {', '.join(extension_pages)}, enable Developer mode, and Load unpacked extension/.",
        }
    )
    return 0


def uninstall_command(_: argparse.Namespace) -> int:
    removed: list[str] = []
    subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}", str(LAUNCH_AGENT_PATH)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if LAUNCH_AGENT_PATH.exists():
        LAUNCH_AGENT_PATH.unlink()
        removed.append(str(LAUNCH_AGENT_PATH))
    if NATIVE_HOST_MANIFEST.exists():
        NATIVE_HOST_MANIFEST.unlink()
        removed.append(str(NATIVE_HOST_MANIFEST))
    brave_manifest = BRAVE_NATIVE_HOST_DIR / f"{NATIVE_HOST_NAME}.json"
    if brave_manifest.exists():
        brave_manifest.unlink()
        removed.append(str(brave_manifest))
    if CODEX_HOOKS_PATH.exists():
        config = json.loads(CODEX_HOOKS_PATH.read_text(encoding="utf-8"))
        hooks = dict(config.get("hooks") or {})
        for event, entries in list(hooks.items()):
            hooks[event] = [
                entry
                for entry in entries
                if "codex-work-gate" not in json.dumps(entry, sort_keys=True)
            ]
            if not hooks[event]:
                del hooks[event]
        config["hooks"] = hooks
        CODEX_HOOKS_PATH.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        removed.append("Codex Work Gate hook entries")
    for path in [NATIVE_HOST_PATH, SERVER_PATH]:
        if path.exists():
            path.unlink()
            removed.append(str(path))
    print_json({"removed": removed})
    return 0


def doctor_command(_: argparse.Namespace) -> int:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add("python", sys.version_info >= (3, 9), sys.version.split()[0])
    add("config", CONFIG_PATH.exists(), str(CONFIG_PATH))
    add("hook_writer", HOOK_WRITER_PATH.exists() and os.access(HOOK_WRITER_PATH, os.X_OK), str(HOOK_WRITER_PATH))
    add("native_host", NATIVE_HOST_PATH.exists() and os.access(NATIVE_HOST_PATH, os.X_OK), str(NATIVE_HOST_PATH))
    add("server_launcher", SERVER_PATH.exists() and os.access(SERVER_PATH, os.X_OK), str(SERVER_PATH))
    add("codex_hooks", CODEX_HOOKS_PATH.exists(), str(CODEX_HOOKS_PATH))
    brave_manifest = BRAVE_NATIVE_HOST_DIR / f"{NATIVE_HOST_NAME}.json"
    browser_manifests = {
        "chrome": str(NATIVE_HOST_MANIFEST) if NATIVE_HOST_MANIFEST.exists() else None,
        "brave": str(brave_manifest) if brave_manifest.exists() else None,
    }
    add(
        "browser_native_host_manifest",
        any(browser_manifests.values()),
        json.dumps(browser_manifests, sort_keys=True),
    )
    status, error = read_status(STATUS_PATH)
    decision = decide_gate(status, error, now_iso()).as_json()
    add("heartbeat_readable", error is None or error == "missing", error or "ok")
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/status", timeout=1) as response:
            add("status_server", response.status == 200, f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/status")
    except OSError as exc:
        add("status_server", False, f"{exc.__class__.__name__}: {exc}")
    add("chrome_extension_path", (repo_root() / "extension" / "manifest.json").exists(), str(repo_root() / "extension"))
    hook_trust = "Run /hooks in Codex and trust Codex Work Gate hooks if they are pending."
    print_json({"ok": all(check["ok"] for check in checks), "checks": checks, "gate": decision, "hookTrust": hook_trust})
    return 0


def config_command(args: argparse.Namespace) -> int:
    config = load_config(CONFIG_PATH)
    if args.config_action == "get":
        print_json(config)
        return 0
    key, value = args.key, args.value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value
    config[key] = parsed
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print_json(config)
    return 0


def verify_command(_: argparse.Namespace) -> int:
    return subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-work-gate")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status").set_defaults(func=status_command)

    event = sub.add_parser("event")
    event.add_argument("event")
    event.set_defaults(func=event_command)

    install = sub.add_parser("install")
    install.add_argument("--extension-id", default=EXTENSION_ID)
    install.add_argument(
        "--browser",
        action="append",
        choices=["chrome", "brave", "all"],
        default=None,
        help="Browser native host to install. Repeatable. Defaults to chrome.",
    )
    install.set_defaults(func=install_command)

    sub.add_parser("uninstall").set_defaults(func=uninstall_command)
    sub.add_parser("doctor").set_defaults(func=doctor_command)
    sub.add_parser("verify").set_defaults(func=verify_command)

    serve = sub.add_parser("serve")
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.set_defaults(func=lambda args: serve_http(args.host, args.port) or 0)

    config = sub.add_parser("config")
    config_sub = config.add_subparsers(dest="config_action", required=True)
    config_sub.add_parser("get").set_defaults(func=config_command)
    set_parser = config_sub.add_parser("set")
    set_parser.add_argument("key")
    set_parser.add_argument("value")
    set_parser.set_defaults(func=config_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
