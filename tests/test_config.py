"""Tests for app/config.py — the scene object caps and their env overrides."""

import pytest

from app import config


def test_known_kinds_have_documented_defaults():
    assert config.scene_cap("satellite") == 40
    assert config.scene_cap("iss") == 3
    assert config.scene_cap("near_earth_object") == 10
    assert config.scene_cap("galaxy") == 6


def test_unknown_kind_is_capped_at_zero():
    assert config.scene_cap("dyson_sphere") == 0


def test_scene_caps_covers_every_capped_kind():
    caps = config.scene_caps()
    for kind in (
        "satellite",
        "iss",
        "space_debris",
        "rocket_body",
        "supernova_remnant",
    ):
        assert kind in caps
    assert all(count >= 0 for count in caps.values())


def test_env_override_replaces_default(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_GALAXY", "25")
    assert config.scene_cap("galaxy") == 25
    assert config.scene_caps()["galaxy"] == 25


def test_env_override_of_multiword_kind(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_BLACK_HOLE", "7")
    assert config.scene_cap("black_hole") == 7


def test_blank_override_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_GALAXY", "  ")
    assert config.scene_cap("galaxy") == 6


def test_negative_override_clamps_to_zero(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_SATELLITE", "-5")
    assert config.scene_cap("satellite") == 0


def test_zero_override_is_honoured(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_SATELLITE", "0")
    assert config.scene_cap("satellite") == 0


def test_non_numeric_override_fails_loudly(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_GALAXY", "lots")
    with pytest.raises(ValueError, match="COSMIC_CAP_GALAXY"):
        config.scene_cap("galaxy")


def test_object_limit_default_and_override(monkeypatch):
    assert config.object_limit() == 20
    monkeypatch.setenv("COSMIC_CAP_OBJECT_QUERY", "5")
    assert config.object_limit() == 5
