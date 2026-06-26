# Troubleshooting

Run:

```bash
./codex-work-gate doctor
```

Common issues:

- `native_host_manifest` is false: run `./scripts/install.sh`.
- `hook_writer` is false: run `./scripts/install.sh`.
- Sites stay blocked after prompting Codex: open `/hooks` in Codex and trust the hooks.
- Sites stay unblocked after Codex quits: wait for the TTL, then run `./codex-work-gate status`.
- Chrome says native host is missing: restart Chrome after installation and confirm the extension ID is `idfgjomaacpinnidblmackdpfnacipja`.

Manual heartbeat checks:

```bash
./codex-work-gate event UserPromptSubmit
./codex-work-gate status
./codex-work-gate event PermissionRequest
./codex-work-gate status
./codex-work-gate event Stop
./codex-work-gate status
```
