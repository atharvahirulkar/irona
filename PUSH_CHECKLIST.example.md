# Pre-push checklist (v0.4)

Run from the project root before `git push`.

## 1. Secrets and personal data

```bash
git status
git check-ignore -v config.yaml user/questions.jsonl eval/questions.jsonl DEVLOG.private.md
./scripts/verify-push.sh
```

Confirm **none** of these are staged:

- `config.yaml` (real `allowed_paths`)
- `user/questions.jsonl`, `user/corpus/*` (except `.gitkeep`)
- `eval/questions.jsonl` (legacy personal eval)
- `DEVLOG.private.md`, `.env`, `eval/results/*`

## 2. Smoke test

```bash
source .venv/bin/activate
pip install -e .
cadbury doctor
cadbury eval --demo
cadbury version   # should print 0.4.0
```

## 3. Commit

```bash
git add -A
git status   # read every staged path
git commit -m "Release Cadbury v0.4: eval harness, user workspace, tools"
git push
```

Do **not** commit unless `git status` looks clean of personal paths.
