"""Tests for scripts/run_pipeline.py — the pipeline entry point.

The script is thin, but at 0% coverage a broken import or a renamed pipeline
argument would ship unnoticed, so cover the frame builder honestly and the
`main()` wiring with the expensive pipeline stubbed out.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.run_pipeline import build_linear_motion_frames, main


# ── build_linear_motion_frames ────────────────────────────────────────────────


def test_builds_the_requested_number_of_frames():
    frames = build_linear_motion_frames(steps=5)
    assert len(frames) == 5


def test_frame_ids_and_timestamps_advance_together():
    frames = build_linear_motion_frames(steps=4)
    assert [f.frame_id for f in frames] == [0, 1, 2, 3]
    assert [f.timestamp for f in frames] == [0.0, 1.0, 2.0, 3.0]


def test_detection_moves_at_the_given_velocity():
    frames = build_linear_motion_frames(steps=3, velocity=(5.0, -2.0))
    positions = [(f.detections[0][1], f.detections[0][2]) for f in frames]
    assert positions == [(100.0, 100.0), (105.0, 98.0), (110.0, 96.0)]


def test_each_frame_carries_exactly_one_detection_patch():
    for frame in build_linear_motion_frames(steps=3):
        assert len(frame.detections) == 1
        patch_image, _, _ = frame.detections[0]
        assert patch_image.ndim >= 2  # a real image patch, not a placeholder


def test_zero_steps_produces_no_frames():
    """The edge the loop is most likely to get wrong."""
    assert build_linear_motion_frames(steps=0) == []


def test_a_single_step_stays_at_the_start_position():
    frames = build_linear_motion_frames(steps=1)
    assert len(frames) == 1
    assert (frames[0].detections[0][1], frames[0].detections[0][2]) == (100.0, 100.0)


def test_frames_are_reproducible():
    """A fixed seed keeps runs comparable between invocations."""
    first = build_linear_motion_frames(steps=2)
    second = build_linear_motion_frames(steps=2)
    assert (first[0].detections[0][0] == second[0].detections[0][0]).all()


# ── main ──────────────────────────────────────────────────────────────────────


def test_main_runs_the_pipeline_and_prints_json(capsys):
    result = MagicMock()
    result.as_dict.return_value = {"tracks": [], "objects": 0}
    pipeline = MagicMock()
    pipeline.run.return_value = result

    with patch(
        "scripts.run_pipeline.create_default_pipeline", return_value=pipeline
    ) as make:
        main()

    make.assert_called_once_with(train_trajectory=True, trajectory_epochs=3)
    pipeline.run.assert_called_once()
    # Output must be machine-readable — the script's whole purpose is its stdout.
    assert json.loads(capsys.readouterr().out) == {"tracks": [], "objects": 0}


def test_main_propagates_a_pipeline_failure():
    """A failed run must exit loudly, not print an empty result."""
    pipeline = MagicMock()
    pipeline.run.side_effect = RuntimeError("model unavailable")

    with patch("scripts.run_pipeline.create_default_pipeline", return_value=pipeline):
        with pytest.raises(RuntimeError, match="model unavailable"):
            main()
