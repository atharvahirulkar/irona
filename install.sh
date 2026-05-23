#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_DIR="$PWD"

echo "==> Cadbury installer"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is required. Install from https://ollama.com/download"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "==> Python $PY_VERSION"

python3 -m venv .venv
# shellcheck disable=SC1091
source ".venv/bin/activate"
pip install -U pip
pip install -e .
pip install -r requirements.txt

chmod +x scripts/init-user.sh 2>/dev/null || true
if [ -x scripts/init-user.sh ]; then
  ./scripts/init-user.sh
else
  if [ ! -f config.yaml ]; then
    cp config.example.yaml config.yaml
    echo "==> Created config.yaml — edit allowed_paths before use."
  fi
fi

mkdir -p "$HOME/.cadbury"
chmod +x bin/start

INSTALL_BIN="$HOME/.local/bin"
mkdir -p "$INSTALL_BIN"
ln -sf "$PROJECT_DIR/bin/start" "$INSTALL_BIN/start"

if ! ollama list 2>/dev/null | grep -q "qwen2.5:7b-instruct"; then
  echo "==> Model not found. Run: ollama pull qwen2.5:7b-instruct"
fi

echo ""
echo "Cadbury installed in: $PROJECT_DIR"
echo ""
echo "Next steps:"
echo "  1. source .venv/bin/activate"
echo "  2. Edit config.yaml (allowed_paths — any folder you own)"
echo "     Edit user/questions.jsonl for eval (filenames in YOUR corpus)"
echo "  3. ollama pull qwen2.5:7b-instruct   # if not already pulled"
echo "  4. cadbury index"
echo "  5. cadbury doctor"
echo "  6. cadbury start"
echo ""
echo "Start options:"
echo "  - cadbury start          (recommended)"
echo "  - ./bin/start cadbury    (from project folder)"
if echo ":$PATH:" | grep -q ":$HOME/.local/bin:"; then
  echo "  - start cadbury          (available — ~/.local/bin is on PATH)"
else
  echo "  - start cadbury          (add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\")"
fi
echo ""

cadbury doctor || true
