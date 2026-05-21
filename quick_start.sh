#!/usr/bin/env bash
# Cam Kesim Optimizasyon - Tek Komutla Baslat (macOS / Linux)
# Ilk calistirmada kurulum yapar, sonrasinda dogrudan calistirir.

set -e
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
    echo "Ilk calistirma tespit edildi - kurulum baslatiliyor..."
    ./setup.sh
fi

./run.sh "$@"
