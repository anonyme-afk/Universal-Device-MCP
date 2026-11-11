#!/usr/bin/env bash
set -e

echo "========================================================================"
echo "  Launching Universal Device MCP One-Command Setup..."
echo "========================================================================"

PYTHON=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "[x] Error: Python was not found in PATH."
    echo "    Please install Python 3.11+ using your package manager or https://www.python.org"
    exit 1
fi

"$PYTHON" quickstart.py "$@"

