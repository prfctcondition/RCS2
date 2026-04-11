"""
Runtime path helpers for development and PyInstaller one-file packaging.
"""
from pathlib import Path
import sys


def get_bundle_dir() -> Path:
    """Return PyInstaller temp bundle dir or project root in dev."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def get_app_dir() -> Path:
    """Writable directory for config/log/output files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_path(*parts: str) -> Path:
    return get_bundle_dir().joinpath(*parts)


def writable_path(*parts: str) -> Path:
    return get_app_dir().joinpath(*parts)
