#!/usr/bin/env bash
# ============================================================
#  Cam Kesim Optimizasyon - macOS / Linux Kurulum Scripti
#  Python sanal ortami olusturur ve bagimliliklari kurar.
# ============================================================

set -e
cd "$(dirname "$0")"

echo ""
echo "[1/4] Python kontrol ediliyor..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "HATA: python3 bulunamadi."
    echo "  macOS    : brew install python    (Homebrew kurulu degilse https://brew.sh)"
    echo "  Linux    : sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
python3 --version

echo ""
echo "[2/4] Sanal ortam (venv) olusturuluyor..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Sanal ortam olusturuldu: .venv"
else
    echo "Sanal ortam zaten mevcut."
fi

echo ""
echo "[3/4] pip guncelleniyor..."
./.venv/bin/python -m pip install --upgrade pip

echo ""
echo "[4/4] Gerekli paketler kuruluyor..."
./.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "============================================================"
echo " Kurulum tamamlandi."
echo " Optimizasyonu calistirmak icin: ./run.sh"
echo "============================================================"
