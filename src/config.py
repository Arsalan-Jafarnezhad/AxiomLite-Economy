"""
Central path configuration for Axiom Economy.

Every mutable/runtime path (the SQLite database, the cached USD price)
lives under DATA_DIR, which is entirely git-ignored - nothing under it
should ever need to be committed. Static, tracked assets (icons, images)
live under ASSETS_DIR instead.
"""

import sys
from pathlib import Path

# Repository root: .../src/config.py -> up 2 levels.
REPO_ROOT = Path(__file__).resolve().parents[1]

ASSETS_DIR = REPO_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"

DATA_DIR = REPO_ROOT / "data"
DB_PATH = DATA_DIR / "database.sqlite3"
PRICE_CACHE_PATH = DATA_DIR / "price_cache.txt"

ICON_PATH = IMAGES_DIR / "icon.ico"
GITHUB_ICON_PATH = IMAGES_DIR / "github.png"
TELEGRAM_ICON_PATH = IMAGES_DIR / "telegram.png"
LINKEDIN_ICON_PATH = IMAGES_DIR / "linkedin.png"


def resource_path(relative_path: str) -> Path:
    """
    Resolve a path relative to the app's base directory. When frozen into
    a PyInstaller executable, sys._MEIPASS points at the temp extraction
    directory instead of the source tree.
    """
    try:
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    except AttributeError:
        base_path = REPO_ROOT
    return base_path / relative_path
