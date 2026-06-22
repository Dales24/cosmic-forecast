"""Tests for app/object_classes.py — registry completeness and integrity."""

import pytest

from app.object_classes import (
    CLASS_GROUPS,
    CLASS_NAMES,
    CLASS_SLUGS,
    DEEP_SPACE_OBJECTS,
    INDEX_TO_CLASS,
    NUM_CLASSES,
    NATURAL_OBJECTS,
    ARTIFICIAL_OBJECTS,
    OBJECT_CLASSES,
    ObjectClass,
    SLUG_TO_INDEX,
    UNKNOWN_OBJECTS,
)

# ── Count and completeness ────────────────────────────────────────────────────


def test_num_classes_matches_object_classes():
    assert NUM_CLASSES == len(OBJECT_CLASSES)


def test_total_class_count():
    assert NUM_CLASSES == 14


def test_natural_objects_count():
    assert len(NATURAL_OBJECTS) == 5


def test_artificial_objects_count():
    assert len(ARTIFICIAL_OBJECTS) == 4


def test_deep_space_objects_count():
    assert len(DEEP_SPACE_OBJECTS) == 4


def test_unknown_objects_count():
    assert len(UNKNOWN_OBJECTS) == 1


# ── Group membership ──────────────────────────────────────────────────────────


def test_natural_objects_have_natural_group():
    assert all(o.group == "natural" for o in NATURAL_OBJECTS)


def test_artificial_objects_have_artificial_group():
    assert all(o.group == "artificial" for o in ARTIFICIAL_OBJECTS)


def test_deep_space_objects_have_deep_space_group():
    assert all(o.group == "deep_space" for o in DEEP_SPACE_OBJECTS)


def test_unknown_objects_have_unknown_group():
    assert all(o.group == "unknown" for o in UNKNOWN_OBJECTS)


# ── Expected slugs present ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "slug",
    [
        "asteroid",
        "comet",
        "meteor",
        "meteoroid",
        "near_earth_object",
    ],
)
def test_natural_slugs_present(slug):
    assert slug in CLASS_SLUGS


@pytest.mark.parametrize(
    "slug",
    [
        "satellite",
        "space_debris",
        "rocket_body",
        "iss",
    ],
)
def test_artificial_slugs_present(slug):
    assert slug in CLASS_SLUGS


@pytest.mark.parametrize(
    "slug",
    [
        "galaxy",
        "nebula",
        "star_cluster",
        "variable_star",
    ],
)
def test_deep_space_slugs_present(slug):
    assert slug in CLASS_SLUGS


def test_ufo_slug_present():
    assert "ufo" in CLASS_SLUGS


# ── Uniqueness ────────────────────────────────────────────────────────────────


def test_slugs_are_unique():
    assert len(CLASS_SLUGS) == len(set(CLASS_SLUGS))


def test_names_are_unique():
    assert len(CLASS_NAMES) == len(set(CLASS_NAMES))


# ── Lookup tables ─────────────────────────────────────────────────────────────


def test_slug_to_index_covers_all_slugs():
    assert set(SLUG_TO_INDEX.keys()) == set(CLASS_SLUGS)


def test_slug_to_index_values_are_unique():
    indices = list(SLUG_TO_INDEX.values())
    assert len(indices) == len(set(indices))


def test_slug_to_index_zero_based():
    assert min(SLUG_TO_INDEX.values()) == 0
    assert max(SLUG_TO_INDEX.values()) == NUM_CLASSES - 1


def test_index_to_class_is_inverse_of_slug_to_index():
    for slug, idx in SLUG_TO_INDEX.items():
        assert INDEX_TO_CLASS[idx].slug == slug


def test_class_names_list_matches_object_classes():
    assert CLASS_NAMES == [o.name for o in OBJECT_CLASSES]


def test_class_slugs_list_matches_object_classes():
    assert CLASS_SLUGS == [o.slug for o in OBJECT_CLASSES]


def test_class_groups_list_matches_object_classes():
    assert CLASS_GROUPS == [o.group for o in OBJECT_CLASSES]


# ── ObjectClass dataclass ─────────────────────────────────────────────────────


def test_object_class_is_frozen():
    obj = OBJECT_CLASSES[0]
    with pytest.raises((AttributeError, TypeError)):
        obj.name = "mutated"


def test_object_class_fields():
    obj = ObjectClass(name="Test", slug="test", group="natural")
    assert obj.name == "Test"
    assert obj.slug == "test"
    assert obj.group == "natural"


def test_object_class_equality():
    a = ObjectClass("Galaxy", "galaxy", "deep_space")
    b = ObjectClass("Galaxy", "galaxy", "deep_space")
    assert a == b


def test_object_class_inequality():
    a = ObjectClass("Galaxy", "galaxy", "deep_space")
    b = ObjectClass("Nebula", "nebula", "deep_space")
    assert a != b


# ── No empty strings ─────────────────────────────────────────────────────────


def test_no_empty_names():
    assert all(o.name.strip() for o in OBJECT_CLASSES)


def test_no_empty_slugs():
    assert all(o.slug.strip() for o in OBJECT_CLASSES)


def test_slugs_are_snake_case():
    import re

    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for slug in CLASS_SLUGS:
        assert pattern.match(slug), f"slug not snake_case: {slug!r}"
