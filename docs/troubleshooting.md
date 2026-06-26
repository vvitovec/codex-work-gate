# Troubleshooting

Run:

```bash
./codex-work-gate doctor
```

Common issues:

- `native_host_manifest` is false: run `./scripts/install.sh`.
- `status_server` is false: run `./scripts/install.sh`, then check `~/.codex-work-gate/server.err.log`.
- `hook_writer` is false: run `./scripts/install.sh`.
- Sites stay blocked after prompting Codex: open `/hooks` in Codex and trust the hooks.
- Sites stay unblocked after Codex quits: wait for the TTL, then run `./codex-work-gate status`.
- Chrome or Brave says native host is missing: restart the browser after installation and confirm the extension ID is `idfgjomaacpinnidblmackdpfnacipja`.
- Brave stays blocked while `./codex-work-gate status` says allowed: open `brave://extensions`, enable Developer mode, press **Update**, then reload Codex Work Gate.

Manual heartbeat checks:

```bash
./codex-work-gate event UserPromptSubmit
./codex-work-gate status
curl http://127.0.0.1:18732/status
./codex-work-gate event PermissionRequest
./codex-work-gate status
./codex-work-gate event Stop
./codex-work-gate status
```
