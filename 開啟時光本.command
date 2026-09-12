#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m avc web --host 127.0.0.1 --port 8765
fi
if command -v python >/dev/null 2>&1; then
  exec python -m avc web --host 127.0.0.1 --port 8765
fi
echo "找不到 Python 3。請先安裝 Python。" >&2
exit 1
