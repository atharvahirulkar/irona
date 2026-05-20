#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is required. Install from https://ollama.com/download"
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
pip install -r requirements.txt

if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  echo "Created config.yaml from example. Edit allowed_paths before use."
fi

mkdir -p "$HOME/.cadbury"
chmod +x bin/start

INSTALL_BIN="$HOME/.local/bin"
mkdir -p "$INSTALL_BIN"
ln -sf "$PWD/bin/start" "$INSTALL_BIN/start"

echo "Cadbury installed."
echo "Start chat: start cadbury"
echo "Health check: source .venv/bin/activate && cadbury doctor"
echo "If 'start' is not found, ensure ~/.local/bin is on your PATH."
