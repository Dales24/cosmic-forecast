"""Stable default artifact locations, independent of the caller's directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = PROJECT_ROOT / "models"
