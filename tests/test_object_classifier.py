import numpy as np

from app.object_classes import NUM_CLASSES, OBJECT_CLASSES, SLUG_TO_INDEX
from app.object_classifier import (
    create_cnn_model,
    generate_synthetic_dataset,
    predict_patch,
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
    assert result["group"] in {"natural", "artificial", "deep_space"}
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["probabilities"]) == NUM_CLASSES


def test_predict_accepts_grayscale_patch():
    model = create_cnn_model()
    gray_patch = np.random.randint(0, 255, size=(64, 64), dtype=np.uint8)
    result = predict_patch(model, gray_patch)
    assert "class" in result
