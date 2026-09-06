"""CLI imports and artifact defaults must not depend on the shell directory."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.paths import PROJECT_ROOT, MODEL_ROOT


@pytest.mark.parametrize(
    "script", ["publish_model", "train_object_classifier", "run_pipeline"]
)
def test_direct_script_from_unrelated_directory(script, tmp_path):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / f"{script}.py"), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


def test_model_defaults_stay_in_checkout(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from app.object_classifier import DEFAULT_MODEL_DIR, DEFAULT_ARCHIVE_DIR
    from app.trajectory_transformer import DEFAULT_MODEL_DIR as trajectory

    assert DEFAULT_MODEL_DIR == MODEL_ROOT / "object_classifier"
    assert DEFAULT_ARCHIVE_DIR == MODEL_ROOT / "archive"
    assert trajectory == MODEL_ROOT / "trajectory_transformer"
    assert DEFAULT_MODEL_DIR.is_absolute()


def test_publisher_explicit_root_from_another_directory(tmp_path, monkeypatch):
    from scripts.publish_model import main

    root = tmp_path / "artifacts"
    model = root / "models" / "object_classifier" / "model.keras"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"dry-run artifact")
    monkeypatch.chdir(tmp_path)
    assert main(["classifier", "--repo", "test/model", "--root", str(root)]) == 0
