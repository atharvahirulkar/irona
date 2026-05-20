# Cadbury Security Model

## Defaults

- Tools are denied unless explicitly allowed by config and policy.
- File access is limited to `allowed_paths` directories only.
- Optional per-session approval is required before `search_notes` runs.
- Internet and calendar tools are disabled unless explicitly enabled in config.
- All tool requests and chat events are appended to `~/.cadbury/audit.log`.

## User controls

- `require_tool_approval: true` prompts before each tool use (or session grant).
- Interactive `/notes off` disables retrieval for the current session.
- Interactive `/strict on` blocks answers when no local sources are found.

## Not enabled by default

- Voice capture (`voice_enabled: false`)
- Calendar OAuth connectors (stub only)
- Web browsing/search (stub only)
- Autonomous file writes

These are intentionally deferred or off by default to avoid accidental over-permissioning.
