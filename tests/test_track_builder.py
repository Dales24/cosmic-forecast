"""Tests for app/track_builder.py — track association and pruning."""

import numpy as np
import pytest

from app.detections import Detection, Track
from app.track_builder import TrackBuilder


def _det(frame_id, t, x, y, cls="satellite"):
    return Detection(
        frame_id=frame_id,
        timestamp=float(t),
        x=float(x), y=float(y),
        patch=np.zeros((64, 64, 3), dtype=np.uint8),
        classification=cls,
    )


# ── Basic association ─────────────────────────────────────────────────────────

def test_single_detection_creates_track():
    tb = TrackBuilder()
    tb.update([_det(0, 0, 0, 0)])
    assert len(tb.tracks) == 1


def test_moving_object_stays_in_one_track():
    tb = TrackBuilder(max_distance=5.0)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([_det(1, 1, 0.5, 0.5)])
    tb.update([_det(2, 2, 1.0, 1.0)])
    assert len(tb.tracks) == 1
    assert len(tb.tracks[0].detections) == 3


def test_distant_objects_become_separate_tracks():
    tb = TrackBuilder(max_distance=1.0)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([_det(1, 1, 100.0, 100.0)])
    assert len(tb.tracks) == 2


def test_two_objects_two_tracks():
    tb = TrackBuilder(max_distance=1.0)
    tb.update([_det(0, 0, 0.0, 0.0), _det(0, 0, 10.0, 10.0)])
    assert len(tb.tracks) == 2


def test_detection_assigned_to_nearest_track():
    tb = TrackBuilder(max_distance=5.0)
    tb.update([_det(0, 0, 0.0, 0.0), _det(0, 0, 10.0, 0.0)])
    # Move close to the first track
    tb.update([_det(1, 1, 0.5, 0.0)])
    track_lengths = sorted(len(t.detections) for t in tb.tracks)
    assert track_lengths == [1, 2]


# ── Missed frames and pruning ─────────────────────────────────────────────────

def test_missed_frame_does_not_immediately_prune():
    tb = TrackBuilder(max_distance=5.0, max_missed_frames=2)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([])           # no detection → 1 missed frame
    assert len(tb.tracks) == 1


def test_track_pruned_after_max_missed_frames():
    tb = TrackBuilder(max_distance=5.0, max_missed_frames=2)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([])   # miss 1
    tb.update([])   # miss 2
    tb.update([])   # miss 3 → prune
    assert len(tb.tracks) == 0


def test_track_survives_within_missed_frame_budget():
    tb = TrackBuilder(max_distance=5.0, max_missed_frames=3)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([])
    tb.update([])
    tb.update([])   # still within budget
    assert len(tb.tracks) == 1


def test_missed_count_resets_on_reassociation():
    tb = TrackBuilder(max_distance=5.0, max_missed_frames=2)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([])                         # miss 1
    tb.update([_det(2, 2, 0.2, 0.2)])    # reassociated → count resets
    tb.update([])                         # miss 1 again
    assert len(tb.tracks) == 1            # not pruned


# ── tracks property ───────────────────────────────────────────────────────────

def test_tracks_property_returns_list():
    tb = TrackBuilder()
    assert isinstance(tb.tracks, list)


def test_tracks_property_empty_initially():
    tb = TrackBuilder()
    assert tb.tracks == []


def test_update_returns_active_tracks():
    tb = TrackBuilder()
    active = tb.update([_det(0, 0, 1.0, 1.0)])
    assert len(active) == 1
    assert isinstance(active[0], Track)


# ── Track contents ────────────────────────────────────────────────────────────

def test_track_contains_detections_in_order():
    tb = TrackBuilder(max_distance=10.0)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([_det(1, 1, 1.0, 0.0)])
    tb.update([_det(2, 2, 2.0, 0.0)])
    track = tb.tracks[0]
    timestamps = [d.timestamp for d in track.detections]
    assert timestamps == sorted(timestamps)


def test_track_latest_returns_last_detection():
    tb = TrackBuilder(max_distance=10.0)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([_det(1, 5, 3.0, 4.0)])
    track = tb.tracks[0]
    assert track.latest.x == pytest.approx(3.0)
    assert track.latest.y == pytest.approx(4.0)


def test_track_positions_returns_array():
    tb = TrackBuilder(max_distance=10.0)
    tb.update([_det(0, 0, 0.0, 0.0)])
    tb.update([_det(1, 1, 1.0, 2.0)])
    pts = tb.tracks[0].positions()
    assert pts.shape == (2, 3)  # (x, y, t)
    assert pts[1, 0] == pytest.approx(1.0)
    assert pts[1, 1] == pytest.approx(2.0)


# ── Distance metric ───────────────────────────────────────────────────────────

def test_distance_exact_match_is_zero():
    tb = TrackBuilder()
    tb.update([_det(0, 0, 3.0, 4.0)])
    track = tb.tracks[0]
    det2 = _det(1, 1, 3.0, 4.0)
    assert tb._distance(det2, track) == pytest.approx(0.0)


def test_distance_3_4_5_triangle():
    tb = TrackBuilder()
    tb.update([_det(0, 0, 0.0, 0.0)])
    track = tb.tracks[0]
    det2 = _det(1, 1, 3.0, 4.0)
    assert tb._distance(det2, track) == pytest.approx(5.0)
