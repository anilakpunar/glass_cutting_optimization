"""Ana giris noktasi.

Kullanim:
    python main.py examples/sample_input.json
"""

import sys
from pathlib import Path

# src/ klasorunu PYTHONPATH'a ekle (kurulum yapilmadan calistirma icin)
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from glass_optimizer.presentation.cli import app  # noqa: E402


if __name__ == "__main__":
    app()
