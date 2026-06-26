# Codex Hook Setup

The installer writes `~/.codex/hooks.json` entries for:

- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `PermissionRequest`
- `Stop`

Each event runs:

```text
/usr/bin/env python3 ~/.codex-work-gate/hooks/work_gate_hook.py <EventName>
```

Codex requires non-managed hooks to be reviewed and trusted. If hooks do not fire, open Codex and run:

```text
/hooks
```

Trust the Codex Work Gate hook definitions.

The hook writer is standalone on purpose. It should not import the project package because it lives outside the repo after installation.
