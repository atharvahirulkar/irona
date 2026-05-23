# WhatsApp in Cadbury (draft only)

Cadbury does **not** integrate with WhatsApp’s unofficial APIs. Those break often and violate WhatsApp’s terms for automated sending.

## What `whatsapp.draft` does

1. You enable `whatsapp.draft` in `enabled_tools` and approve it (or `/approve all`).
2. You run:
   ```bash
   cadbury whatsapp +14155551234 "Running late, see you at 3"
   ```
   Or in interactive mode:
   ```text
   whatsapp +14155551234 "Running late"
   ```
3. macOS opens **WhatsApp** (or WhatsApp Web) with the message **pre-filled**.
4. **You tap Send.** Cadbury never sends on your behalf.

## Optional phone allowlist

```yaml
enabled_tools:
  - whatsapp.draft

whatsapp_allowed_phones:
  - "14155551234"
  - "919876543210"
```

If the list is empty, any number is allowed (still requires your manual Send).

## Why not full “text my friend”?

| Approach | Problem |
|----------|---------|
| Unofficial WhatsApp libraries | ToS risk, account bans, brittle |
| Official Business API | Business accounts, templates, not personal chat |
| **Draft + human Send** | Safe, honest, good for learning agent boundaries |

For Siri-style messaging, use **Apple Shortcuts** + iMessage for contacts in Apple’s ecosystem.
