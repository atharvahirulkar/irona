# Cadbury evaluation

Measure **whether the right file is retrieved** (and optionally whether the LLM answers correctly).

---

## Personal vs public data

| Path | In git? | Use |
|------|---------|-----|
| `user/questions.jsonl` | **No** | Your gold Q&A tied to **your** `allowed_paths` |
| `user/corpus/` | **No** (contents) | Optional local docs if config uses `./user/corpus` |
| `eval/questions.template.jsonl` | Yes | Generic template — copy via `init-user.sh` |
| `eval/fixtures/corpus/` | Yes | Tiny demo docs for `cadbury eval --demo` only |

Run once: `./scripts/init-user.sh`

---

## Quick start (your documents)

```bash
./scripts/init-user.sh
# Edit config.yaml — set allowed_paths to YOUR folder (any path)
# Edit user/questions.jsonl — expected_sources = YOUR filenames

cadbury index
cadbury eval
```

## Public demo (safe to run after clone)

Uses only committed fixture files — no personal data:

```bash
cadbury index   # indexes your config paths; for demo-only:
cadbury eval --demo
```

For `--demo`, corpus is `eval/fixtures/corpus/` (overrides config paths for that run).

---

## Gold questions format (`user/questions.jsonl`)

```json
{
  "id": "budget-2026",
  "question": "What is the project budget?",
  "expected_sources": ["budget-report.pdf"],
  "expected_terms": ["budget"],
  "expected_answer_terms": ["50000"],
  "notes": "optional"
}
```

| Field | Meaning |
|-------|---------|
| `expected_sources` | Substrings matched against retrieved file **paths** |
| `expected_terms` | For retrieval eval: term in top snippet |
| `expected_answer_terms` | For generation eval: term in LLM answer |

---

## Commands

```bash
cadbury eval
cadbury eval --modes keyword,hybrid
cadbury eval --questions user/questions.jsonl
cadbury eval --demo
cadbury eval --generation --limit 5
```

Output: `eval/results/latest.md` (gitignored)

---

## Generation eval (v0.4)

```bash
cadbury eval --generation
```

Requires Ollama. Skips questions without `expected_answer_terms` (or `expected_terms` fallback).

Output: `eval/results/generation/latest.md`
