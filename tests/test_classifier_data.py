"""Independent partitions and preprocessing checks using synthetic image files."""

import csv

import numpy as np
import pytest
from PIL import Image

from app.classifier_data import load_manifest
from scripts.check_model_portability import generate, verify


def manifest(tmp_path, groups=("a", "b", "c"), values=(20, 80, 150)):
    rows = []
    for split, group, value in zip(("train", "validation", "test"), groups, values):
        Image.fromarray(np.full((64, 64, 3), value, dtype=np.uint8)).save(
            tmp_path / f"{split}.png"
        )
        rows.append(
            {
                "path": f"{split}.png",
                "label": "satellite",
                "group": group,
                "split": split,
            }
        )
    path = tmp_path / "manifest.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_explicit_partitions_and_training_scale(tmp_path):
    arrays, report = load_manifest(manifest(tmp_path))
    assert report["split_counts"] == {"train": 1, "validation": 1, "test": 1}
    np.testing.assert_allclose(arrays["test"][0], 150 / 255)
    assert len(report["manifest_sha256"]) == 64


def test_reject_shared_group(tmp_path):
    with pytest.raises(ValueError, match="crosses partitions"):
        load_manifest(manifest(tmp_path, groups=("same", "same", "other")))


def test_reject_same_pixels_in_different_files(tmp_path):
    with pytest.raises(ValueError, match="pixels cross"):
        load_manifest(manifest(tmp_path, values=(20, 20, 80)))


def test_manifest_prepare_does_not_construct_model(tmp_path, monkeypatch):
    from scripts import train_object_classifier as script
    from unittest.mock import Mock

    path = manifest(tmp_path)
    model = Mock(side_effect=AssertionError("must not construct model"))
    monkeypatch.setattr(script, "create_cnn_model", model)
    monkeypatch.setattr(
        "sys.argv", ["train", "--manifest", str(path), "--prepare-only"]
    )
    script.main()
    model.assert_not_called()


@pytest.mark.parametrize("interrupted", [False, True])
def test_manifest_test_evaluation_follows_training(tmp_path, monkeypatch, interrupted):
    from scripts import train_object_classifier as script
    from unittest.mock import Mock

    path = manifest(tmp_path)
    model = Mock()
    events = []

    def fit(*args, **kwargs):
        events.append("train")
        if interrupted:
            raise KeyboardInterrupt

    model.fit.side_effect = fit
    model.evaluate.side_effect = lambda *a, **kw: events.append("test") or {
        "accuracy": 0.5
    }
    monkeypatch.setattr(script, "create_cnn_model", lambda: model)
    output = tmp_path / "output"

    def save(*args, **kwargs):
        output.mkdir()
        return output

    monkeypatch.setattr(script, "save_model", save)
    monkeypatch.setattr(
        "sys.argv", ["train", "--manifest", str(path), "--output", str(output)]
    )
    script.main()
    assert events == (["train"] if interrupted else ["train", "test"])
    assert (output / "evaluation.json").exists()
    np.testing.assert_allclose(model.fit.call_args.args[0], 20 / 255)
    if interrupted:
        model.evaluate.assert_not_called()
    else:
        np.testing.assert_allclose(model.evaluate.call_args.args[0], 150 / 255)


def test_portability_fixture_roundtrip_and_prediction_mismatch(tmp_path):
    root = tmp_path / "producer"
    generate(root)
    verify(root)
    with np.load(root / "orbital.npz") as data:
        inputs, outputs = data["inputs"], data["outputs"] + 1
    np.savez(root / "orbital.npz", inputs=inputs, outputs=outputs)
    with pytest.raises(AssertionError):
        verify(root)
