"""
Entry point. Run with:

    python main.py

from the repository root.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from src.ui.app import main  # noqa: E402  (import after sys.path setup)

if __name__ == "__main__":
    main()
