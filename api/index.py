from __future__ import annotations

import sys
from pathlib import Path

# Cho phép import từ /backend/app trên Vercel
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402

