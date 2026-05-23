# Your personal Cadbury workspace

Everything in this folder (except this README) is **yours** and should **not** be committed to git.

## Setup (once per machine)

From the project root:

```bash
./scripts/init-user.sh
```

That creates:

| Path | Purpose |
|------|---------|
| `config.yaml` (repo root) | Your paths, tools, model — **gitignored** |
| `user/corpus/` | Optional local document folder (if you use `./user/corpus` in config) |
| `user/questions.jsonl` | Your private eval gold set — **gitignored** |

## Pointing at any folder

You do **not** have to use `user/corpus`. In `config.yaml`:

```yaml
allowed_paths:
  - "/path/to/any/folder/you/own"
```

After changing paths:

```bash
cadbury index
# Edit user/questions.jsonl so expected_sources match filenames in THAT folder
cadbury eval
```

## Eval questions

- **Template (generic, safe to commit):** `eval/questions.template.jsonl` — matches `eval/fixtures/corpus/` only.
- **Your gold set:** `user/questions.jsonl` — copy from template, then replace filenames and answer terms with **your** documents.

Never commit `user/questions.jsonl` or files under `user/corpus/`.
