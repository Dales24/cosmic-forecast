"""Patch-based CNN for classifying telescope image objects."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers

from app.object_classes import (
    CLASS_GROUPS,
    CLASS_NAMES,
    CLASS_SLUGS,
    INDEX_TO_CLASS,
    NUM_CLASSES,
    SLUG_TO_INDEX,
)

PATCH_SIZE = (64, 64)
DEFAULT_MODEL_DIR = Path("models/object_classifier")
DEFAULT_ARCHIVE_DIR = Path("models/archive")
MODEL_FILENAME = "model.keras"
METADATA_FILENAME = "metadata.json"


def create_cnn_model(
    input_shape: tuple[int, int, int] = (*PATCH_SIZE, 3)
) -> tf.keras.Model:
    """Build a small CNN for multi-class object classification."""
    model = models.Sequential(
        [
            layers.Input(shape=input_shape),
            layers.Conv2D(32, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(128, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.3),
            layers.Flatten(),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.4),
            layers.Dense(NUM_CLASSES, activation="softmax"),
        ],
        name="object_patch_cnn",
    )
    model.compile(
        optimizer=optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def _normalize_patch(patch: np.ndarray) -> np.ndarray:
    """Scale a single patch to float32 in [0, 1] with shape (H, W, 3)."""
    array = np.asarray(patch, dtype=np.float32)
    if array.ndim == 2:
        array = np.stack([array] * 3, axis=-1)
    elif array.shape[-1] == 1:
        array = np.repeat(array, 3, axis=-1)
    if array.max() > 1.0:
        array = array / 255.0
    return array


def load_image_dataset(data_dir: str | Path, validation_split: float = 0.2):
    """Load labeled patches from subdirectories named by class slug."""
    data_dir = Path(data_dir)
    missing = [slug for slug in CLASS_SLUGS if not (data_dir / slug).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing class folders under {data_dir}: {', '.join(missing)}"
        )

    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        labels="inferred",
        label_mode="int",
        class_names=CLASS_SLUGS,
        image_size=PATCH_SIZE,
        batch_size=32,
        validation_split=validation_split,
        subset="training",
        seed=42,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        labels="inferred",
        label_mode="int",
        class_names=CLASS_SLUGS,
        image_size=PATCH_SIZE,
        batch_size=32,
        validation_split=validation_split,
        subset="validation",
        seed=42,
    )
    return train_ds, val_ds


def _class_base_color(class_index: int) -> np.ndarray:
    """A stable, class-specific base RGB colour (the signal each class carries)."""
    return np.random.default_rng(1000 + class_index).integers(
        20, 80, size=3, dtype=np.int16
    )


def synthetic_patch(slug: str, seed: int = 0) -> np.ndarray:
    """A single synthetic RGB patch characteristic of `slug`'s class.

    Shared by the training set and by live classification so that a patch
    generated for a kind is classified as that kind by the trained model.
    """
    class_index = SLUG_TO_INDEX[slug]
    rng = np.random.default_rng(seed)
    base = _class_base_color(class_index)
    noise = rng.integers(-15, 16, size=(*PATCH_SIZE, 3), dtype=np.int16)
    patch = np.clip(base + noise, 0, 255).astype(np.uint8)
    if slug in {"galaxy", "nebula", "star_cluster"}:
        patch = np.clip(patch.astype(np.int16) + 40, 0, 255).astype(np.uint8)
    elif slug in {"satellite", "iss", "rocket_body"}:
        mid_r, mid_c = PATCH_SIZE[0] // 2, PATCH_SIZE[1] // 2
        patch[mid_r - 2 : mid_r + 2, mid_c - 2 : mid_c + 2] = 255
    return patch


def generate_synthetic_dataset(
    samples_per_class: int = 32,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Create synthetic RGB patches for smoke tests and bootstrapping."""
    rng = np.random.default_rng(seed)
    images = []
    labels = []
    for class_index, slug in enumerate(CLASS_SLUGS):
        for _ in range(samples_per_class):
            images.append(synthetic_patch(slug, seed=int(rng.integers(0, 2**31))))
            labels.append(class_index)
    return np.stack(images), np.array(labels, dtype=np.int32)


def train_model(
    model: tf.keras.Model,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray | None = None,
    y_val: np.ndarray | None = None,
    epochs: int = 10,
    batch_size: int = 32,
) -> tf.keras.callbacks.History:
    """Train the CNN on normalized patch arrays."""
    x_train = np.stack([_normalize_patch(patch) for patch in x_train])
    callbacks = []
    validation_data = None
    if x_val is not None and y_val is not None:
        x_val = np.stack([_normalize_patch(patch) for patch in x_val])
        validation_data = (x_val, y_val)

    return model.fit(
        x_train,
        y_train,
        validation_data=validation_data,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=0,
    )


def predict_patch(model: tf.keras.Model, patch: np.ndarray) -> dict:
    """Classify a single image patch."""
    normalized = _normalize_patch(patch)
    probabilities = model.predict(np.expand_dims(normalized, axis=0), verbose=0)[0]
    class_index = int(np.argmax(probabilities))
    obj = INDEX_TO_CLASS[class_index]
    return {
        "class": obj.name,
        "slug": obj.slug,
        "group": obj.group,
        "confidence": float(probabilities[class_index]),
        "probabilities": {
            name: float(prob) for name, prob in zip(CLASS_NAMES, probabilities)
        },
    }


def _write_model(model: tf.keras.Model, target_dir: Path) -> Path:
    """Write the model weights and class metadata into `target_dir`."""
    target_dir.mkdir(parents=True, exist_ok=True)
    model.save(target_dir / MODEL_FILENAME)
    metadata = {
        "patch_size": list(PATCH_SIZE),
        "class_names": CLASS_NAMES,
        "class_slugs": CLASS_SLUGS,
        "class_groups": CLASS_GROUPS,
    }
    (target_dir / METADATA_FILENAME).write_text(json.dumps(metadata, indent=2))
    return target_dir


def save_model(
    model: tf.keras.Model,
    model_dir: str | Path = DEFAULT_MODEL_DIR,
    archive: bool = False,
    archive_dir: str | Path = DEFAULT_ARCHIVE_DIR,
) -> Path:
    """Persist the classifier; optionally keep a timestamped archived copy.

    The primary copy at `model_dir` is always overwritten (latest model). When
    `archive` is set, a second copy is written under `archive_dir/<timestamp>/`
    so prior runs are never lost and can be reloaded later.
    """
    saved = _write_model(model, Path(model_dir))
    if archive:
        # Microseconds keep back-to-back runs from colliding; lexical sort = newest last.
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S_%f")
        _write_model(model, Path(archive_dir) / stamp)
    return saved


def list_archived_models(archive_dir: str | Path = DEFAULT_ARCHIVE_DIR) -> list[Path]:
    """Return archived model directories, newest first."""
    archive_dir = Path(archive_dir)
    if not archive_dir.exists():
        return []
    archives = [p for p in archive_dir.iterdir() if (p / MODEL_FILENAME).exists()]
    return sorted(archives, reverse=True)


def load_model(model_dir: str | Path = DEFAULT_MODEL_DIR) -> tf.keras.Model:
    """Load a saved classifier."""
    model_dir = Path(model_dir)
    return tf.keras.models.load_model(model_dir / MODEL_FILENAME)


def load_archived_model(
    name: str | None = None,
    archive_dir: str | Path = DEFAULT_ARCHIVE_DIR,
) -> tf.keras.Model:
    """Load an archived classifier by directory name, or the newest if `name` is None."""
    archive_dir = Path(archive_dir)
    if name is not None:
        target = archive_dir / name
        if not (target / MODEL_FILENAME).exists():
            raise FileNotFoundError(
                f"No archived model named {name!r} in {archive_dir}"
            )
        return load_model(target)
    archives = list_archived_models(archive_dir)
    if not archives:
        raise FileNotFoundError(f"No archived models found in {archive_dir}")
    return load_model(archives[0])
