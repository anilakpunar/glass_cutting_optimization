#!/usr/bin/env bash
# Cam Kesim Optimizasyon - Birim Test Calistirma (macOS / Linux)

set -e
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
    echo "Sanal ortam bulunamadi. Once ./setup.sh calistirin."
    exit 1
fi

export PYTHONPATH="$PWD/src"
./.venv/bin/python -m pip install -q pytest
./.venv/bin/python -m pytest tests/ -v
