# Sharing Irona with someone else

Each person runs their **own** Irona on **their** Mac. No shared cloud account. No shared data.

## What they need

- macOS (Apple Silicon recommended)
- Python 3.11+
- [Ollama](https://ollama.com/download)
- ~10–30 GB free disk

## Setup (5 steps)

```bash
git clone https://github.com/YOUR_USERNAME/irona.git
cd irona
chmod +x install.sh
./install.sh
```

`install.sh` runs `scripts/init-user.sh`, which creates `config.yaml` and `user/questions.jsonl` (gitignored).

Edit `config.yaml` with **their** document folder (any path they own):

```yaml
allowed_paths:
  - "/path/to/their/documents"
  # or: "./user/corpus"  (files go in user/corpus/, still gitignored)
```

Edit `user/questions.jsonl` so `expected_sources` match **their** filenames (not the demo template).

Public smoke test (no personal data): `irona eval --demo`

Then:

```bash
source .venv/bin/activate
ollama pull qwen2.5:7b-instruct
irona index
irona doctor
irona start
```

Inside chat, run `/approve` or `/approve all` when prompted.

## Start commands

| Command | When to use |
|---------|-------------|
| `irona start` | Always works after install (venv active) |
| `irona` | Same as `irona start` |
| `start irona` | Only if `~/.local/bin` is on PATH (install.sh sets this up) |

From project folder without global `start`:

```bash
./bin/start irona
```

## Optional tools (off by default)

In `config.yaml`:

```yaml
enabled_tools:
  - calendar.read   # macOS Calendar
  - web.search      # needs: pip install duckduckgo-search
```

## What stays private

- `config.yaml` (their paths) — not in git
- `~/.irona/audit.log`
- `~/.irona/rag/` index
- All local files and prompts

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `irona: command not found` | `source .venv/bin/activate` |
| `start: command not found` | Use `irona start` or add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` |
| `search_notes denied` | Set `allowed_paths` to real folders; run `/approve` |
| Ollama errors | Open Ollama app; run `ollama pull qwen2.5:7b-instruct` |
