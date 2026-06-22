"""Transformer model for forecasting object trajectories from track history."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers

DEFAULT_SEQ_LEN = 8
DEFAULT_HORIZON = 3
DEFAULT_MODEL_DIR = Path("models/trajectory_transformer")


def create_trajectory_transformer(
    seq_len: int = DEFAULT_SEQ_LEN,
    horizon: int = DEFAULT_HORIZON,
    d_model: int = 32,
) -> tf.keras.Model:
    """Build a lightweight transformer for (x, y, t) sequence forecasting."""
    inputs = layers.Input(shape=(seq_len, 3), name="track_sequence")
    projected = layers.Dense(d_model)(inputs)
    attended = layers.MultiHeadAttention(num_heads=2, key_dim=16)(
        projected, projected
    )
    pooled = layers.GlobalAveragePooling1D()(attended)
    hidden = layers.Dense(64, activation="relu")(pooled)
    outputs = layers.Dense(horizon * 2, name="future_positions")(hidden)
    outputs = layers.Reshape((horizon, 2))(outputs)

    model = models.Model(inputs=inputs, outputs=outputs, name="trajectory_transformer")
    model.compile(
        optimizer=optimizers.Adam(learning_rate=1e-3),
        loss="mse",
    )
    return model


def _pad_sequence(positions: np.ndarray, seq_len: int) -> np.ndarray:
    """Pad or truncate track positions to fixed sequence length."""
    if len(positions) >= seq_len:
        return positions[-seq_len:]
    pad_rows = seq_len - len(positions)
    padding = np.repeat(positions[:1], pad_rows, axis=0)
    return np.vstack([padding, positions])


def _normalize_sequence(positions: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Normalize x/y relative to last point; scale time to unit step."""
    origin = positions[-1].copy()
    normalized = positions.copy()
    normalized[:, 0] -= origin[0]
    normalized[:, 1] -= origin[1]
    time_scale = max(np.diff(positions[:, 2]).mean() if len(positions) > 1 else 1.0, 1e-6)
    normalized[:, 2] = (positions[:, 2] - origin[2]) / time_scale
    return normalized.astype(np.float32), origin, time_scale


def _denormalize_prediction(
    prediction: np.ndarray,
    origin: np.ndarray,
) -> np.ndarray:
    """Convert model output back to absolute coordinates."""
    absolute = prediction.copy()
    absolute[:, 0] += origin[0]
    absolute[:, 1] += origin[1]
    return absolute


def generate_synthetic_trajectories(
    count: int = 256,
    seq_len: int = DEFAULT_SEQ_LEN,
    horizon: int = DEFAULT_HORIZON,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Create linear-motion trajectories for bootstrapping."""
    rng = np.random.default_rng(seed)
    sequences = []
    targets = []

    for _ in range(count):
        start_x, start_y = rng.uniform(0, 512, size=2)
        vx, vy = rng.uniform(-4, 4, size=2)
        times = np.arange(seq_len + horizon, dtype=np.float32)
        xs = start_x + vx * times
        ys = start_y + vy * times
        track = np.stack([xs, ys, times], axis=-1)
        sequences.append(track[:seq_len])
        targets.append(track[seq_len : seq_len + horizon, :2])

    return np.stack(sequences), np.stack(targets)


def train_trajectory_model(
    model: tf.keras.Model,
    sequences: np.ndarray,
    targets: np.ndarray,
    epochs: int = 5,
    batch_size: int = 32,
) -> tf.keras.callbacks.History:
    """Train the transformer on absolute track sequences."""
    normalized_x = []
    normalized_y = []
    for sequence, target in zip(sequences, targets):
        norm_seq, origin, _ = _normalize_sequence(sequence)
        norm_target = target.copy()
        norm_target[:, 0] -= origin[0]
        norm_target[:, 1] -= origin[1]
        normalized_x.append(norm_seq)
        normalized_y.append(norm_target)

    return model.fit(
        np.stack(normalized_x),
        np.stack(normalized_y),
        epochs=epochs,
        batch_size=batch_size,
        verbose=0,
    )


def predict_trajectory(
    model: tf.keras.Model,
    positions: np.ndarray,
    seq_len: int = DEFAULT_SEQ_LEN,
) -> np.ndarray:
    """Predict future (x, y) positions from a track history."""
    if len(positions) < 2:
        raise ValueError("Need at least two detections to forecast trajectory")

    padded = _pad_sequence(positions, seq_len)
    normalized, origin, _ = _normalize_sequence(padded)
    prediction = model.predict(
        np.expand_dims(normalized, axis=0),
        verbose=0,
    )[0]
    return _denormalize_prediction(prediction, origin)


def linear_extrapolation(positions: np.ndarray, horizon: int = DEFAULT_HORIZON) -> np.ndarray:
    """Fallback forecast using constant velocity from the last two points."""
    last = positions[-1]
    previous = positions[-2]
    dt = max(last[2] - previous[2], 1e-6)
    vx = (last[0] - previous[0]) / dt
    vy = (last[1] - previous[1]) / dt

    future = []
    for step in range(1, horizon + 1):
        t = last[2] + step * dt
        future.append([last[0] + vx * step * dt, last[1] + vy * step * dt, t])
    return np.array(future, dtype=np.float32)


def save_trajectory_model(
    model: tf.keras.Model,
    model_dir: str | Path = DEFAULT_MODEL_DIR,
) -> Path:
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save(model_dir / "model.keras")
    return model_dir


def load_trajectory_model(model_dir: str | Path = DEFAULT_MODEL_DIR) -> tf.keras.Model:
    return tf.keras.models.load_model(Path(model_dir) / "model.keras")
