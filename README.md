# Codex Work Gate

Local Chrome/Brave gate for macOS. It blocks distracting sites unless recent Codex hook activity says an agent is actively working.

## How It Works

1. Global Codex hooks write a heartbeat to `~/.codex-work-gate/status.json`.
2. A Chrome/Brave Manifest V3 extension asks the native host for the current gate state.
3. The native host reads the heartbeat and returns `allowed=true` only when:
   - `state` is `active`
   - `lastActiveAt` is still inside the heartbeat TTL
4. The extension enables redirect rules for blocked sites when the gate is closed.

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
```

## Verify

```bash
./scripts/verify.sh
```

## Uninstall

```bash
./scripts/uninstall.sh
```

This removes the Chrome/Brave native messaging manifests and Codex Work Gate entries from `~/.codex/hooks.json`. It leaves config and heartbeat files in place.
