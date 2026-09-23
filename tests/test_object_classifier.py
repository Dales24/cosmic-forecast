import numpy as np
import pytest

from app.object_classes import NUM_CLASSES, OBJECT_CLASSES, SLUG_TO_INDEX
from app.object_classifier import (
    create_cnn_model,
    generate_synthetic_dataset,
    predict_patch,
    synthetic_patch,
    train_model,
    _normalize_patch,
    load_image_dataset,
    stratified_split,
)


def test_dark_byte_images_have_same_scale_as_training():
    patch = np.ones((64, 64, 3), dtype=np.uint8)
    np.testing.assert_allclose(_normalize_patch(patch), 1 / 255)
    np.testing.assert_allclose(
        _normalize_patch(patch.astype(np.float32) / 255), 1 / 255
    )


def test_directory_training_and_inference_use_same_pixel_scale(tmp_path):
    from PIL import Image
    from app.object_classes import CLASS_SLUGS

    patch = np.full((64, 64, 3), 128, dtype=np.uint8)
    for slug in CLASS_SLUGS:
        folder = tmp_path / slug
        folder.mkdir()
        for index in range(2):
            Image.fromarray(patch).save(folder / f"{index}.png")
    for dataset in load_image_dataset(tmp_path):
        images, labels = next(iter(dataset))
        np.testing.assert_allclose(images.numpy()[0], _normalize_patch(patch))
        assert float(images.numpy().max()) <= 1


def test_stratified_split_covers_all_classes_without_overlap():
    labels = np.repeat(np.arange(NUM_CLASSES), 5)
    images = np.arange(len(labels))[:, None]
    first = stratified_split(images, labels)
    second = stratified_split(images, labels)
    train_x, train_y, val_x, val_y = first
    assert set(train_y) == set(val_y) == set(range(NUM_CLASSES))
    assert set(train_x[:, 0]).isdisjoint(val_x[:, 0])
    assert len(train_y) + len(val_y) == len(labels)
    for a, b in zip(first, second):
        np.testing.assert_array_equal(a, b)


def test_stratified_split_rejects_single_example_class():
    with pytest.raises(ValueError, match="at least two"):
        stratified_split(np.array([[1], [2], [3]]), np.array([0, 0, 1]))


def test_object_class_registry_matches_plan():
    names = [obj.name for obj in OBJECT_CLASSES]
    assert "Asteroid" in names
    assert "International Space Station" in names
    assert "Variable Star" in names
    assert "Black Hole" in names
    assert NUM_CLASSES == 23
    assert SLUG_TO_INDEX["iss"] == names.index("International Space Station")


def test_cnn_output_shape():
    model = create_cnn_model()
    assert model.output_shape == (None, NUM_CLASSES)


def test_train_and_predict_on_synthetic_patches():
    model = create_cnn_model()
    images, labels = generate_synthetic_dataset(samples_per_class=8, seed=0)
    split = int(len(labels) * 0.8)

    history = train_model(
        model,
        images[:split],
        labels[:split],
        images[split:],
        labels[split:],
        epochs=2,
        batch_size=8,
    )

    assert "loss" in history.history
    assert len(history.history["loss"]) == 2

    result = predict_patch(model, images[0])
    assert result["class"] in [obj.name for obj in OBJECT_CLASSES]
    assert result["group"] in {oc.group for oc in OBJECT_CLASSES}
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["probabilities"]) == NUM_CLASSES


def test_predict_accepts_grayscale_patch():
    model = create_cnn_model()
    gray_patch = np.random.randint(0, 255, size=(64, 64), dtype=np.uint8)
    result = predict_patch(model, gray_patch)
    assert "class" in result


def test_synthetic_patch_is_deterministic_and_kind_specific():
    # Same slug + seed -> identical patch (so classification is stable per object).
    assert np.array_equal(
        synthetic_patch("satellite", seed=3), synthetic_patch("satellite", seed=3)
    )
    sat = synthetic_patch("satellite", seed=0)
    gal = synthetic_patch("galaxy", seed=0)
    assert sat.shape == (64, 64, 3)
    assert sat[32, 32].max() == 255  # artificial kinds carry a bright marker
    assert not np.array_equal(sat, gal)  # different kinds look different


def test_trained_model_classifies_kind_patches_as_that_kind():
    """A patch generated for a kind is classified as that kind by a trained model.

    The dataset is seeded, but weight init and batch shuffling come from
    TensorFlow's global RNG — unseeded, this test trains a different model every
    run and fails intermittently. Seed the whole stack so a failure means the
    classifier regressed, not that the dice came up wrong.
    """
    import tensorflow as tf

    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(1234)

    model = create_cnn_model()
    images, labels = generate_synthetic_dataset(samples_per_class=20)
    # Eight epochs left a held-out galaxy misclassified on Intel macOS.
    # Allow convergence across CPU backends without relaxing held-out checks.
    train_model(model, images, labels, epochs=16)
    for slug in ("satellite", "galaxy", "comet", "ufo"):
        assert predict_patch(model, synthetic_patch(slug, seed=7))["slug"] == slug
