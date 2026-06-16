#!/usr/bin/env bash
# Create gitignored personal paths from public templates.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p user/corpus

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo "Created config.yaml — edit allowed_paths for your document folder."
else
  echo "config.yaml already exists (unchanged)."
fi

if [[ ! -f user/questions.jsonl ]]; then
  cp eval/questions.template.jsonl user/questions.jsonl
  echo "Created user/questions.jsonl from template."
  echo "  → Edit expected_sources / expected_answer_terms to match YOUR files."
else
  echo "user/questions.jsonl already exists (unchanged)."
fi

echo ""
echo "Next:"
echo "  1. Set allowed_paths in config.yaml (e.g. ./user/corpus or an external folder)"
echo "  2. Add documents OR point at your existing folder"
echo "  3. irona index && irona eval"
echo ""
echo "Public demo (no personal data): irona eval --demo"
