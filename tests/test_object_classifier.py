import numpy as np

from app.object_classes import NUM_CLASSES, OBJECT_CLASSES, SLUG_TO_INDEX
from app.object_classifier import (
    create_cnn_model,
    generate_synthetic_dataset,
    predict_patch,
    synthetic_patch,
    train_model,
)


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
