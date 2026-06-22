"""Associate CNN detections across frames into object tracks."""

from __future__ import annotations

import math

from app.detections import Detection, Track


class TrackBuilder:
    """Greedy nearest-neighbor track association."""

    def __init__(
        self,
        max_distance: float = 25.0,
        max_missed_frames: int = 3,
    ):
        self.max_distance = max_distance
        self.max_missed_frames = max_missed_frames
        self._tracks: list[Track] = []
        self._next_track_id = 1
        self._missed_counts: dict[int, int] = {}

    @property
    def tracks(self) -> list[Track]:
        return list(self._tracks)

    def _distance(self, detection: Detection, track: Track) -> float:
        latest = track.latest
        return math.hypot(detection.x - latest.x, detection.y - latest.y)

    def update(self, detections: list[Detection]) -> list[Track]:
        """Assign detections to tracks and return active tracks."""
        unmatched_tracks = set(range(len(self._tracks)))
        unmatched_detections = set(range(len(detections)))

        pairs = []
        for track_index, track in enumerate(self._tracks):
            for detection_index, detection in enumerate(detections):
                distance = self._distance(detection, track)
                if distance <= self.max_distance:
                    pairs.append((distance, track_index, detection_index))
        pairs.sort(key=lambda item: item[0])

        assignments: dict[int, int] = {}
        for _, track_index, detection_index in pairs:
            if track_index not in unmatched_tracks:
                continue
            if detection_index not in unmatched_detections:
                continue
            assignments[track_index] = detection_index
            unmatched_tracks.remove(track_index)
            unmatched_detections.remove(detection_index)

        for track_index, detection_index in assignments.items():
            track = self._tracks[track_index]
            track.detections.append(detections[detection_index])
            self._missed_counts[track.track_id] = 0

        for track_index in unmatched_tracks:
            track = self._tracks[track_index]
            self._missed_counts[track.track_id] = (
                self._missed_counts.get(track.track_id, 0) + 1
            )

        for detection_index in unmatched_detections:
            detection = detections[detection_index]
            track = Track(track_id=self._next_track_id, detections=[detection])
            self._tracks.append(track)
            self._missed_counts[track.track_id] = 0
            self._next_track_id += 1

        self._tracks = [
            track
            for track in self._tracks
            if self._missed_counts.get(track.track_id, 0) <= self.max_missed_frames
        ]
        self._missed_counts = {
            track.track_id: self._missed_counts[track.track_id]
            for track in self._tracks
            if track.track_id in self._missed_counts
        }
        return self.tracks
