# Codex Work Gate Notes

- Always run `./scripts/verify.sh` before committing.
- This project is local-only for now. It is not hosted on Baller and has no production deployment target.
- Keep the hook writer in `hooks/work_gate_hook.py` standalone; installed hooks must keep working even if Python package imports are unavailable.
- Do not modify unrelated `~/.codex/config.toml` settings. The installer uses `~/.codex/hooks.json` for reversible hook setup.
- Default Chrome extension ID is `idfgjomaacpinnidblmackdpfnacipja`; if the manifest key changes, update the native-host allowed origin and docs.
