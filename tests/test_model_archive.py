"""Tests for archived-model save/list/load in app/object_classifier.py."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app import object_classifier
from app.object_classifier import (
    list_archived_models,
    load_archived_model,
    save_model,
)


class _FakeModel:
    """Stands in for a Keras model — only needs a `save` that writes a file."""

    def save(self, path):
        Path(path).write_text("weights")


def test_save_without_archive_leaves_archive_dir_empty(tmp_path):
    primary = tmp_path / "model"
    archive = tmp_path / "archive"
    save_model(_FakeModel(), model_dir=primary, archive=False, archive_dir=archive)
    assert (primary / "model.keras").exists()
    assert (primary / "metadata.json").exists()
    assert not archive.exists()


def test_save_with_archive_writes_timestamped_copy(tmp_path):
    primary = tmp_path / "model"
    archive = tmp_path / "archive"
    save_model(_FakeModel(), model_dir=primary, archive=True, archive_dir=archive)
    snapshots = list(archive.iterdir())
    assert len(snapshots) == 1
    assert (snapshots[0] / "model.keras").exists()
    assert (snapshots[0] / "metadata.json").exists()


def test_list_archived_models_newest_first(tmp_path):
    for name in ("20240101T000000_000000", "20260101T000000_000000"):
        snap = tmp_path / name
        snap.mkdir()
        (snap / "model.keras").write_text("weights")
    result = list_archived_models(tmp_path)
    assert [p.name for p in result] == [
        "20260101T000000_000000",
        "20240101T000000_000000",
    ]


def test_list_archived_models_ignores_incomplete_dirs(tmp_path):
    (tmp_path / "empty").mkdir()  # no model.keras → not a usable archive
    good = tmp_path / "20250101T000000_000000"
    good.mkdir()
    (good / "model.keras").write_text("weights")
    assert [p.name for p in list_archived_models(tmp_path)] == [good.name]


def test_list_archived_models_missing_dir_returns_empty(tmp_path):
    assert list_archived_models(tmp_path / "nope") == []


def test_load_archived_model_by_name(tmp_path):
    snap = tmp_path / "snap1"
    snap.mkdir()
    (snap / "model.keras").write_text("weights")
    with patch.object(object_classifier, "load_model", return_value="loaded") as load:
        result = load_archived_model("snap1", archive_dir=tmp_path)
    load.assert_called_once_with(snap)
    assert result == "loaded"


def test_load_archived_model_unknown_name_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="No archived model named"):
        load_archived_model("does-not-exist", archive_dir=tmp_path)


def test_load_archived_model_defaults_to_newest(tmp_path):
    for name in ("20240101T000000_000000", "20260101T000000_000000"):
        snap = tmp_path / name
        snap.mkdir()
        (snap / "model.keras").write_text("weights")
    with patch.object(object_classifier, "load_model", return_value="loaded") as load:
        load_archived_model(archive_dir=tmp_path)
    load.assert_called_once_with(tmp_path / "20260101T000000_000000")


def test_load_archived_model_raises_when_empty(tmp_path):
    with pytest.raises(FileNotFoundError, match="No archived models"):
        load_archived_model(archive_dir=tmp_path)
