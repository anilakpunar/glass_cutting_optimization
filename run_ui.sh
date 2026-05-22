#!/usr/bin/env bash
# Cam Kesim Optimizasyon - Web Arayuzu (macOS / Linux)
# Streamlit arayuzunu baslatir ve tarayicida acar.

set -e
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
    echo "Sanal ortam bulunamadi. Once ./setup.sh calistirin."
    exit 1
fi

# streamlit kurulu degilse kur
if ! ./.venv/bin/python -c "import streamlit" 2>/dev/null; then
    echo "streamlit kuruluyor..."
    ./.venv/bin/python -m pip install -q streamlit
fi

echo "Arayuz baslatiliyor... Tarayici otomatik acilacak (http://localhost:8501)"
exec ./.venv/bin/python -m streamlit run streamlit_app.py
