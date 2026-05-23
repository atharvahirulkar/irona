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
- Calendar read (`calendar.read` must be listed in `enabled_tools`)
- Web search (`web.search` must be listed in `enabled_tools`)
- Autonomous file writes

Calendar uses macOS Calendar via AppleScript (read-only). Web search uses DuckDuckGo and sends queries over the network. Both require runtime approval when `require_tool_approval` is true.

**WhatsApp (`whatsapp.draft`):** Opens a pre-filled draft in the WhatsApp app via `wa.me` URL. Cadbury does **not** auto-send messages. Optional `whatsapp_allowed_phones` restricts which numbers can be drafted. See [docs/WHATSAPP.md](docs/WHATSAPP.md).
