# Status Heartbeat Schema

Path:

```text
~/.codex-work-gate/status.json
```

Example:

```json
{
  "state": "active",
  "lastEvent": "PreToolUse",
  "lastActiveAt": "2026-06-26T09:30:00.000Z",
  "updatedAt": "2026-06-26T09:30:00.000Z",
  "threadId": null,
  "sessionId": null,
  "cwd": "/abs/path",
  "ttlMs": 30000
}
```

Allowed states:

- `active`: browsing is allowed only while `lastActiveAt` is inside `ttlMs`.
- `waitingOnApproval`: browsing is blocked.
- `idle`: browsing is blocked.
- `unknown`: browsing is blocked.

Rules:

- `UserPromptSubmit`, `PreToolUse`, and `PostToolUse` set or refresh `active`.
- `PermissionRequest` sets `waitingOnApproval`.
- `Stop` sets `idle`.
- Missing, malformed, or expired status files block by default.
