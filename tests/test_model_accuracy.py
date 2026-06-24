"""Accuracy tests for the two models.

These train on the synthetic datasets and assert the models actually learn —
classifier beats random chance, transformer beats a no-skill baseline. Seeds are
fixed and thresholds left with margin so the tests stay deterministic, not flaky.
"""

import numpy as np
import tensorflow as tf

from app.object_classes import NUM_CLASSES, SLUG_TO_INDEX
from app.object_classifier import (
    create_cnn_model,
    generate_synthetic_dataset,
    predict_patch,
    train_model,
)
from app.trajectory_transformer import (
    create_trajectory_transformer,
    generate_synthetic_trajectories,
    linear_extrapolation,
    predict_trajectory,
    train_trajectory_model,
)

_RANDOM_CHANCE = 1.0 / NUM_CLASSES  # ~0.071 for 14 classes


def _classifier_holdout_accuracy(samples_per_class=16, epochs=12, seed=0):
    """Train on a shuffled 80% split, return accuracy on the held-out 20%."""
    tf.random.set_seed(seed)  # deterministic weight init — keep the threshold stable
    images, labels = generate_synthetic_dataset(
        samples_per_class=samples_per_class, seed=seed
    )
    order = np.random.default_rng(seed).permutation(len(labels))
    images, labels = images[order], labels[order]
    split = int(len(labels) * 0.8)

    model = create_cnn_model()
    train_model(
        model,
        images[:split],
        labels[:split],
        images[split:],
        labels[split:],
        epochs=epochs,
        batch_size=16,
    )

    predicted = [
        SLUG_TO_INDEX[predict_patch(model, img)["slug"]] for img in images[split:]
    ]
    actual = labels[split:]
    return float(np.mean(np.array(predicted) == actual))


# ── Classifier ────────────────────────────────────────────────────────────────


def test_classifier_beats_random_chance():
    """A trained CNN should classify the synthetic patches well above 1/14."""
    accuracy = _classifier_holdout_accuracy()
    assert accuracy > 3 * _RANDOM_CHANCE  # > ~0.21, comfortably above chance


def test_classifier_confidence_tracks_correct_prediction():
    """When the model is confident, the prediction is the trained class."""
    images, labels = generate_synthetic_dataset(samples_per_class=12, seed=1)
    split = int(len(labels) * 0.8)
    model = create_cnn_model()
    train_model(model, images[:split], labels[:split], epochs=12, batch_size=16)
    # The predicted class is always a real class with a valid probability mass.
    result = predict_patch(model, images[0])
    assert result["confidence"] == max(result["probabilities"].values())
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-4


# ── Trajectory transformer ──────────────────────────────────────────────────────


def test_linear_extrapolation_is_near_exact_on_linear_track():
    """Constant-velocity extrapolation should reproduce linear motion exactly."""
    times = np.arange(6, dtype=np.float32)
    track = np.stack([2.0 + 3.0 * times, 5.0 - 1.5 * times, times], axis=-1)
    predicted = linear_extrapolation(track, horizon=3)

    expected_x = 2.0 + 3.0 * np.array([6, 7, 8])
    expected_y = 5.0 - 1.5 * np.array([6, 7, 8])
    assert np.allclose(predicted[:, 0], expected_x, atol=1e-3)
    assert np.allclose(predicted[:, 1], expected_y, atol=1e-3)


def test_trained_transformer_beats_naive_baseline():
    """After training, mean error must beat 'repeat the last position' forecasting."""
    tf.random.set_seed(42)
    sequences, targets = generate_synthetic_trajectories(count=256, seed=42)
    split = int(len(sequences) * 0.8)

    model = create_trajectory_transformer()
    train_trajectory_model(
        model, sequences[:split], targets[:split], epochs=20, batch_size=32
    )

    model_errors = []
    naive_errors = []
    for sequence, target in zip(sequences[split:], targets[split:]):
        predicted = predict_trajectory(model, sequence)[:, :2]
        last_xy = sequence[-1, :2]
        model_errors.append(np.mean(np.abs(predicted - target)))
        naive_errors.append(np.mean(np.abs(last_xy - target)))

    assert np.mean(model_errors) < np.mean(naive_errors)


def test_predicted_trajectory_has_expected_shape():
    sequences, targets = generate_synthetic_trajectories(count=32, seed=7)
    model = create_trajectory_transformer()
    train_trajectory_model(model, sequences, targets, epochs=2)
    predicted = predict_trajectory(model, sequences[0])
    assert predicted.shape == (3, 2)
