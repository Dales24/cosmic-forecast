import numpy as np

from app.detections import Detection, Track
from app.kalman_refinement import KalmanRefiner
from app.object_classifier import generate_synthetic_dataset
from app.pipeline import FrameInput, create_default_pipeline
from app.track_builder import TrackBuilder
from app.trajectory_transformer import (
    create_trajectory_transformer,
    generate_synthetic_trajectories,
    linear_extrapolation,
    predict_trajectory,
    train_trajectory_model,
)


def test_track_builder_associates_moving_object():
    builder = TrackBuilder(max_distance=10.0)
    detections = [
        Detection(frame_id=0, timestamp=0.0, x=10.0, y=10.0),
        Detection(frame_id=1, timestamp=1.0, x=13.0, y=12.0),
        Detection(frame_id=2, timestamp=2.0, x=16.0, y=14.0),
    ]

    builder.update([detections[0]])
    builder.update([detections[1]])
    tracks = builder.update([detections[2]])

    assert len(tracks) == 1
    assert len(tracks[0].detections) == 3


def test_track_builder_creates_separate_tracks_for_distant_objects():
    builder = TrackBuilder(max_distance=5.0)
    builder.update([Detection(frame_id=0, timestamp=0.0, x=0.0, y=0.0)])
    tracks = builder.update([Detection(frame_id=1, timestamp=1.0, x=100.0, y=100.0)])

    assert len(tracks) == 2


def test_linear_extrapolation():
    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [2.0, 1.0, 1.0],
            [4.0, 2.0, 2.0],
        ],
        dtype=np.float32,
    )
    forecast = linear_extrapolation(positions, horizon=2)

    assert forecast.shape == (2, 3)
    assert forecast[-1, 0] == 8.0
    assert forecast[-1, 1] == 4.0


def test_trajectory_transformer_trains_and_predicts():
    model = create_trajectory_transformer()
    sequences, targets = generate_synthetic_trajectories(count=64)
    history = train_trajectory_model(model, sequences, targets, epochs=2, batch_size=16)

    assert "loss" in history.history
    prediction = predict_trajectory(model, sequences[0])
    assert prediction.shape == (3, 2)


def test_kalman_refiner_returns_uncertainty():
    track = Track(
        track_id=1,
        detections=[
            Detection(frame_id=0, timestamp=0.0, x=0.0, y=0.0),
            Detection(frame_id=1, timestamp=1.0, x=2.0, y=1.0),
            Detection(frame_id=2, timestamp=2.0, x=4.0, y=2.0),
        ],
    )
    refiner = KalmanRefiner()
    result = refiner.refine(
        track, predicted_xy=np.array([6.0, 3.0]), target_timestamp=3.0
    )

    assert result.track_id == 1
    assert result.uncertainty_x > 0.0
    assert result.uncertainty_y > 0.0


def test_end_to_end_pipeline():
    images, _ = generate_synthetic_dataset(samples_per_class=1, seed=1)
    patch = images[0]
    frames = []
    x, y = 50.0, 50.0

    for frame_id in range(8):
        frames.append(
            FrameInput(
                frame_id=frame_id,
                timestamp=float(frame_id),
                detections=[(patch, x, y)],
            )
        )
        x += 2.0
        y += 1.0

    pipeline = create_default_pipeline(train_trajectory=True, trajectory_epochs=2)
    result = pipeline.run(frames)

    assert len(result.tracks) == 1
    assert len(result.predictions) == 1
    assert result.predictions[0].x > x - 20.0
    assert result.predictions[0].object_class is not None
