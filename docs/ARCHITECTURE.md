# Cadbury architecture (v0.3)

Cadbury is a **terminal-native agent** with three layers: inference, retrieval, and policy. File and tool access never go through the LLM directly — the Python runtime gathers context, then calls Ollama.

---

## Request flow

```text
User input (CLI / interactive)
        │
        ▼
┌───────────────────┐
│  Command router   │  /web, /calendar, web …, or natural language
│  (chat.py / cli)  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     deny / prompt
│  Policy layer     │◄──── config.enabled_tools, allowed_paths
│  (policy.py)      │      SessionPolicy /approve, audit.log
└─────────┬─────────┘
          │ allow
          ▼
┌───────────────────┐
│  Tool execution   │  search_notes, calendar.read, web.search
│  (notes, tools,  │
│   retrieval, rag) │
└─────────┬─────────┘
          │ context text + paths
          ▼
┌───────────────────┐
│  Ollama HTTP API  │  qwen2.5:7b-instruct (configurable)
│  (chat.py)        │  stream: false, messages[]
└─────────┬─────────┘
          ▼
     Answer + Sources:
```

---

## Components

| Module | Role |
|--------|------|
| `src/cli.py` | Subcommands: `start`, `ask`, `search`, `index`, `eval`, `web`, `calendar`, `doctor` |
| `src/chat.py` | Interactive loop, `run_ask`, Ollama `chat()`, session memory for follow-ups |
| `src/config.py` | YAML: paths, model URL, `enabled_tools`, `use_embeddings` |
| `src/policy.py` | `can_use_tool`, session grants, `append_audit` |
| `src/notes.py` | Allowlisted walk, PDF/DOCX/text extract, keyword scoring |
| `src/rag.py` | Chunk index under `~/.cadbury/rag/`, `semantic_search`, offline model load |
| `src/retrieval.py` | **keyword / semantic / hybrid** — shared by chat and `eval/run_eval.py` |
| `src/intent.py` | Lightweight hints for calendar/web in natural questions |
| `src/tools.py` | macOS Calendar (AppleScript), DuckDuckGo web search |
| `src/voice.py` | Optional STT/TTS (off by default) |
| `eval/run_eval.py` | Retrieval benchmark (no LLM) |

---

## Retrieval modes

Production uses **hybrid** (`search_hybrid`):

1. Semantic top-k if `use_embeddings: true` and index exists  
2. Keyword fan-out on question terms + filename scores  
3. Merge by best score per file path  

Evaluation runs each mode in isolation — see [EVAL.md](../EVAL.md).

**Index build:** `cadbury index` → reads allowlisted files → chunks (900 chars, overlap 120) → `sentence-transformers` embeddings → JSON in `~/.cadbury/rag/`.

---

## Configuration & data on disk

| Path | Purpose |
|------|---------|
| `./config.yaml` or `~/.cadbury/config.yaml` | Allowlisted roots, tools, model name |
| `~/.cadbury/rag/` | Embedding index (not in git) |
| `~/.cadbury/audit.log` | Prompts, tool grants, results |

---

## Failure modes (documented in development)

| Symptom | Cause | Mitigation |
|---------|-------|------------|
| Wrong file in Sources | Keyword “grade” hits syllabus | Hybrid + larger PDF snippets + session file memory |
| HuggingFace `RemoteProtocolError` | Hub fetch during embed load | `local_files_only=True` when index exists |
| `web` searches PDFs | Missing `/web` command routing | Top-of-loop `web` / `/web` handler |
| Eval / CLI hangs | `search_notes` approval prompt | `cadbury eval` bypasses policy (retrieval only) |

---

## Extension points

- **Gold eval set:** `user/questions.jsonl` — personal, gitignored; template in `eval/questions.template.jsonl`  
- **Stricter policy:** per-tool config, domain allowlist for web  
- **Incremental index:** mtime check per file (not implemented)  
- **Generation eval:** optional second harness calling Ollama with frozen retrieval  

See [THE_LOCAL_GAP.md](THE_LOCAL_GAP.md) for why these layers matter for local pre-trained deployments.
