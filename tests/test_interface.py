"""The `app.interface` module is a backwards-compat shim kept after api.py was
renamed. It must re-export the same FastAPI app object."""

from fastapi import FastAPI
from pathlib import Path


def test_interface_reexports_the_api_app():
    from app.interface import app as shim_app
    from app.api import app as real_app

    assert isinstance(shim_app, FastAPI)
    assert shim_app is real_app


def test_cosmic_forecast_panel_sections_are_collapsible():
    html = (Path(__file__).parents[1] / "front_end" / "index.html").read_text()

    assert html.count('class="panel-section"') == 4
    assert '<details class="panel-section" open>' in html
    for title in (
        "Load a Scene",
        "Add Object to Scene",
        "Classify Image Patch",
        "Upload Position CSV",
    ):
        assert f"<summary>{title}</summary>" in html


def test_object_detail_sections_are_collapsible():
    html = (Path(__file__).parents[1] / "front_end" / "index.html").read_text()

    assert html.count('class="obj-section"') == 4
    assert 'class="obj-section" id="obj-about" open' in html
    for title in ("Demo classification", "Coordinates", "Details", "About"):
        assert f'class="obj-section-title">{title}</summary>' in html
