# Codex Work Gate

Local Chrome/Brave gate for macOS. It blocks distracting sites unless recent Codex hook activity says an agent is actively working.

## How It Works

1. Global Codex hooks write a heartbeat to `~/.codex-work-gate/status.json`.
2. A tiny local status server runs at `http://127.0.0.1:18732/status`.
3. A Chrome/Brave Manifest V3 extension reads that local status endpoint, with native messaging retained as a fallback.
4. The gate returns `allowed=true` only when:
   - `state` is `active`
   - `lastActiveAt` is still inside the heartbeat TTL
5. The extension enables redirect rules for blocked sites when the gate is closed.

Approvals count as blocked. Idle/completed/missing/expired heartbeat states count as blocked.

## Install

```bash
./scripts/install.sh
```

For Brave too:

```bash
./codex-work-gate install --browser brave
```

Then open `chrome://extensions` or `brave://extensions`, enable Developer mode, choose **Load unpacked**, and select:

```text
extension/
```

The bundled extension key gives it this stable extension ID:

```text
idfgjomaacpinnidblmackdpfnacipja
```

After installing, open Codex and run `/hooks` if Codex says the hooks need review. Trust the Codex Work Gate hooks.

## Commands

```bash
./codex-work-gate status
./codex-work-gate doctor
./codex-work-gate config get
./codex-work-gate config set blockedHosts '["youtube.com","reddit.com"]'
./codex-work-gate event UserPromptSubmit
./codex-work-gate event Stop
./codex-work-gate serve
```

## Verify

```bash
./scripts/verify.sh
```

## Uninstall

```bash
./scripts/uninstall.sh
```

This removes the Chrome/Brave native messaging manifests, the local LaunchAgent, installed launchers, and Codex Work Gate entries from `~/.codex/hooks.json`. It leaves config and heartbeat files in place.
