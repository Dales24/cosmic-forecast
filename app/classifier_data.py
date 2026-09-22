"""Explicit group-disjoint image partitions for classifier experiments."""

import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from app.object_classes import SLUG_TO_INDEX
from app.object_classifier import PATCH_SIZE


def load_manifest(path):
    """Read path,label,group,split CSV; never randomly repartition observations."""
    path = Path(path).resolve()
    root = path.parent
    partitions = {name: [] for name in ("train", "validation", "test")}
    groups, files, pixels = {}, set(), {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"path", "label", "group", "split"}.issubset(reader.fieldnames or []):
            raise ValueError("Manifest requires path,label,group,split columns")
        for line, row in enumerate(reader, 2):
            split, group, label = (
                (row.get(key) or "").strip() for key in ("split", "group", "label")
            )
            if split not in partitions or not group or label not in SLUG_TO_INDEX:
                raise ValueError(f"Invalid split, group or label on line {line}")
            image_path = (root / row["path"]).resolve()
            if not image_path.is_relative_to(root):
                raise ValueError("Image paths must stay inside the manifest directory")
            if image_path in files:
                raise ValueError("Duplicate image path")
            files.add(image_path)
            if group in groups and groups[group] != split:
                raise ValueError(f"Group {group!r} crosses partitions")
            groups[group] = split
            with Image.open(image_path) as image:
                patch = np.asarray(
                    image.convert("RGB").resize(PATCH_SIZE), dtype=np.uint8
                )
            digest = hashlib.sha256(patch.tobytes()).hexdigest()
            if digest in pixels and pixels[digest] != split:
                raise ValueError("Identical model-input pixels cross partitions")
            pixels[digest] = split
            partitions[split].append((patch, SLUG_TO_INDEX[label], digest))
    if any(not rows for rows in partitions.values()):
        raise ValueError("Train, validation and test must all be nonempty")
    trained = {row[1] for row in partitions["train"]}
    if any(
        row[1] not in trained
        for name in ("validation", "test")
        for row in partitions[name]
    ):
        raise ValueError("Every held-out label needs training examples")
    arrays = {
        name: (
            np.stack([r[0] for r in rows]).astype(np.float32) / 255,
            np.array([r[1] for r in rows]),
        )
        for name, rows in partitions.items()
    }
    metadata = {
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "split_counts": {name: len(rows) for name, rows in partitions.items()},
        "class_counts": {
            name: {
                slug: sum(r[1] == index for r in rows)
                for slug, index in SLUG_TO_INDEX.items()
            }
            for name, rows in partitions.items()
        },
        "input_hashes": {
            name: [r[2] for r in rows] for name, rows in partitions.items()
        },
        "group_counts": {
            name: sum(s == name for s in groups.values()) for name in partitions
        },
    }
    return arrays, metadata
