"""Configurare pytest — adaugă app/ la sys.path."""

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
