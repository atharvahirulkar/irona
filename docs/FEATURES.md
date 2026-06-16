# Irona v0.4 — feature status

Intended scope for this release vs deferred work.

| Feature | Status | How to use |
|---------|--------|------------|
| **Local LLM chat** | Done | `irona start`, `irona ask`, `irona chat` |
| **Allowlisted file search** | Done | `irona search`, retrieval in `irona ask` |
| **Semantic RAG** | Done | `irona index`, hybrid retrieval |
| **Source citations** | Done | Answers include `Sources:` paths |
| **Policy + audit** | Done | `enabled_tools`, `/approve`, `~/.irona/audit.log` |
| **Strict mode** | Done | `/strict on` in interactive |
| **Calendar read** | Done (opt-in) | `calendar.read` in config, `/calendar` |
| **Web search** | Done (opt-in) | `web.search` in config, `/web` or `web …` |
| **WhatsApp** | Done (draft only) | `whatsapp.draft` — opens draft; **you tap Send** |
| **Voice input** | Done (opt-in) | `voice_enabled: true`, `/listen` |
| **Voice output** | Done (opt-in) | `/voice on` (macOS `say`) |
| **Retrieval eval** | Done | `irona eval`, `irona eval --demo` |
| **Generation eval** | Done | `irona eval --generation` (needs Ollama) |
| **Auto-send WhatsApp/SMS** | **Not planned** | No unofficial APIs; see [WHATSAPP.md](WHATSAPP.md) |
| **Siri / “ask anything”** | **Not planned** | Out of scope for v0.4 |
| **Menu-bar app** | Deferred | Future |

## Dependencies (optional tools)

```bash
pip install duckduckgo-search          # web.search
pip install faster-whisper sounddevice soundfile   # voice
```

Ollama + `qwen2.5:7b-instruct` required for chat and generation eval.
