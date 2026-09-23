"""Generate synthetic trained artifacts or verify inference in another runtime."""

import argparse
import json
import platform
from pathlib import Path

import setuptools  # noqa: F401
import numpy as np
import tensorflow as tf

from app.object_classifier import create_cnn_model
from app.trajectory_transformer import create_trajectory_transformer
from app.orbital_forecast import create_residual_model
from app.paths import PROJECT_ROOT


def generate(root):
    root.mkdir(parents=True, exist_ok=False)
    tf.keras.utils.set_random_seed(42)
    rng = np.random.default_rng(42)
    inputs = {
        "classifier": rng.random((2, 64, 64, 3), dtype=np.float32),
        "trajectory": rng.random((2, 8, 3), dtype=np.float32),
        "orbital": rng.random((2, 14), dtype=np.float32),
    }
    models = {
        "classifier": create_cnn_model(),
        "trajectory": create_trajectory_transformer(),
        "orbital": create_residual_model(inputs["orbital"]),
    }
    for name, model in models.items():
        x = inputs[name]
        target = (
            np.array([0, 1])
            if name == "classifier"
            else np.ones(model(x).shape, dtype=np.float32)
        )
        model.train_on_batch(x, target)
        model.save(root / f"{name}.keras")
        np.savez(
            root / f"{name}.npz", inputs=x, outputs=model(x, training=False).numpy()
        )
    (root / "runtime.json").write_text(
        json.dumps({"tensorflow": tf.__version__, "platform": platform.system()})
    )


def verify(root):
    for name in ("classifier", "trajectory", "orbital"):
        model = tf.keras.models.load_model(root / f"{name}.keras", compile=False)
        with np.load(root / f"{name}.npz", allow_pickle=False) as data:
            actual = model(data["inputs"], training=False).numpy()
            np.testing.assert_allclose(actual, data["outputs"], rtol=1e-4, atol=1e-5)
    print(f"Verified {root.name} on {platform.system()} TensorFlow {tf.__version__}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["generate", "verify"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if not args.root.is_absolute():
        args.root = PROJECT_ROOT / args.root
    if args.mode == "generate":
        generate(args.root)
    else:
        roots = sorted(args.root.glob("*/runtime.json"))
        if len(roots) != 3:
            raise ValueError("Expected artifacts from all three producer platforms")
        producers = {json.loads(path.read_text())["platform"] for path in roots}
        if producers != {"Windows", "Linux", "Darwin"}:
            raise ValueError("Expected Windows, Linux and macOS producer artifacts")
        for metadata in roots:
            verify(metadata.parent)


if __name__ == "__main__":
    main()
