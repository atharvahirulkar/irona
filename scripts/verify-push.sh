#!/usr/bin/env bash
# Quick pre-push safety check (no git write).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Cadbury verify-push"
fail=0

for f in config.yaml user/questions.jsonl eval/questions.jsonl DEVLOG.private.md PUSH_CHECKLIST.md; do
  if git check-ignore -q "$f" 2>/dev/null; then
    echo "OK gitignored: $f"
  else
    echo "WARN: $f is NOT gitignored"
    fail=1
  fi
done

echo ""
echo "==> Scanning files that would be committed..."

# Only scan paths git would track (not gitignored personal files).
leak_found=0
while IFS= read -r f; do
  [[ -f "$f" ]] || continue
  case "$f" in
    scripts/verify-push.sh) continue ;;
  esac
  # Home-directory paths (accidental paste of machine paths).
  if grep -qF '/Users/' "$f" 2>/dev/null || grep -qF '/home/' "$f" 2>/dev/null; then
    echo "FAIL: home path in $f"
    leak_found=1
  fi
  # Obvious secret shapes.
  if grep -qE 'API_KEY|sk-[A-Za-z0-9]{10,}|password\s*=\s*["'"'"'][^"'"'"']{4,}' "$f" 2>/dev/null; then
    echo "FAIL: possible secret in $f"
    leak_found=1
  fi
done < <(git ls-files -co --exclude-standard 2>/dev/null || true)

if [[ $leak_found -eq 1 ]]; then
  fail=1
else
  echo "OK: no home paths or obvious secrets in committable files"
fi

echo ""
if [[ $fail -eq 0 ]]; then
  echo "==> verify-push passed (run cadbury doctor && cadbury eval --demo before commit)"
  exit 0
fi
echo "==> verify-push FAILED — fix before push"
exit 1
