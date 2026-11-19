"""Install the Phase44 import roots before test collection."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic_fixtures  # noqa: E402,F401  (installs the owner import roots)
