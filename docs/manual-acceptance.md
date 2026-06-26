# Manual Acceptance

1. Run `./scripts/install.sh`.
2. Load `extension/` from `chrome://extensions`.
3. Trust the hooks from `/hooks` in Codex if prompted.
4. Start a Codex prompt.
5. Confirm `./codex-work-gate status` returns `allowed: true`.
6. Open a blocked site such as YouTube and confirm it loads while Codex is active.
7. Let Codex finish.
8. Confirm the blocked site redirects to the Codex Work Gate page after grace/TTL.
9. Trigger a permission request and confirm blocked sites are blocked while approval is pending.
10. Quit Codex and confirm the gate blocks after TTL expiry.
