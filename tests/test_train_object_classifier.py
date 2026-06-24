"""Tests for scripts/train_object_classifier.py — interrupt-safe persistence."""

import signal
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.train_object_classifier import _raise_interrupt, train_and_persist

_MODEL = object()  # opaque stand-in; the helper only forwards it to save_model


def test_persists_after_normal_training():
    with patch(
        "scripts.train_object_classifier.save_model", return_value=Path("out")
    ) as save:
        result = train_and_persist(_MODEL, Path("out"), train_fn=lambda: None)
    save.assert_called_once_with(_MODEL, Path("out"), archive=True)
    assert result == Path("out")


def test_persists_when_interrupted():
    def interrupted_training():
        raise KeyboardInterrupt

    with patch(
        "scripts.train_object_classifier.save_model", return_value=Path("out")
    ) as save:
        result = train_and_persist(_MODEL, Path("out"), interrupted_training)
    # A killed run must still checkpoint the partial model.
    save.assert_called_once_with(_MODEL, Path("out"), archive=True)
    assert result == Path("out")


def test_archive_flag_forwarded_to_save():
    with patch(
        "scripts.train_object_classifier.save_model", return_value=Path("out")
    ) as save:
        train_and_persist(_MODEL, Path("out"), lambda: None, archive=False)
    save.assert_called_once_with(_MODEL, Path("out"), archive=False)


def test_real_error_skips_save():
    def failing_training():
        raise ValueError("bad data")

    with patch("scripts.train_object_classifier.save_model") as save:
        with pytest.raises(ValueError, match="bad data"):
            train_and_persist(_MODEL, Path("out"), failing_training)
    # Never persist a model when training errors out for real.
    save.assert_not_called()


def test_sigterm_handler_raises_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        _raise_interrupt(signal.SIGTERM, None)


def test_sigterm_handler_restored_after_run():
    original = signal.getsignal(signal.SIGTERM)
    with patch("scripts.train_object_classifier.save_model", return_value=Path("out")):
        train_and_persist(_MODEL, Path("out"), train_fn=lambda: None)
    assert signal.getsignal(signal.SIGTERM) is original
