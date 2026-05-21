#!/usr/bin/env bash
# ============================================================
#  Cam Kesim Optimizasyon - macOS / Linux Calistirma Scripti
#
#  Kullanim:
#      ./run.sh                              -> ornek girdi ile calisir
#      ./run.sh my_job.json                  -> kendi girdi dosyaniz
#      ./run.sh my_job.json output_klasoru   -> ozel cikti klasoru
#      ./run.sh my_job.json output 60        -> 60 sn sure siniri
# ============================================================

set -e
cd "$(dirname "$0")"

JOB_FILE="${1:-examples/sample_input.json}"
OUT_DIR="${2:-output}"
TIME_LIMIT="${3:-30}"

if [ ! -f ".venv/bin/python" ]; then
    echo "Sanal ortam bulunamadi. Once ./setup.sh calistirin."
    exit 1
fi

if [ ! -f "$JOB_FILE" ]; then
    echo "HATA: Girdi dosyasi bulunamadi: $JOB_FILE"
    exit 1
fi

export PYTHONPATH="$PWD/src"

echo ""
echo "============================================================"
echo " Cam Kesim Optimizasyonu calistiriliyor"
echo " Girdi      : $JOB_FILE"
echo " Cikti      : $OUT_DIR"
echo " Sure siniri: $TIME_LIMIT saniye / plaka"
echo "============================================================"
echo ""

./.venv/bin/python main.py "$JOB_FILE" --output "$OUT_DIR" --time-limit "$TIME_LIMIT"

echo ""
echo "============================================================"
echo " Tamamlandi. Sonuclar: $OUT_DIR"
echo "============================================================"

# Cikti klasorunu otomatik ac (varsa)
if [ -d "$OUT_DIR" ]; then
    if command -v open >/dev/null 2>&1; then
        open "$OUT_DIR"          # macOS
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$OUT_DIR"      # Linux
    fi
fi
