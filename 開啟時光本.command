#!/bin/bash
cd "$(dirname "$0")" || exit 1
# GitHub 下載會帶上 Apple 隔離標記；能執行到這裡就清掉，之後雙擊不會再被擋
if command -v xattr >/dev/null 2>&1; then
  xattr -d com.apple.quarantine "$0" 2>/dev/null || true
  xattr -dr com.apple.quarantine . 2>/dev/null || true
fi
export PYTHONPATH="$(pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m avc web --host 127.0.0.1 --port 8765
fi
if command -v python >/dev/null 2>&1; then
  exec python -m avc web --host 127.0.0.1 --port 8765
fi
echo "找不到 Python 3。請先安裝 Python。" >&2
exit 1
