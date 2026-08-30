"""The `app.interface` module is a backwards-compat shim kept after api.py was
renamed. It must re-export the same FastAPI app object."""

from fastapi import FastAPI


def test_interface_reexports_the_api_app():
    from app.interface import app as shim_app
    from app.api import app as real_app

    assert isinstance(shim_app, FastAPI)
    assert shim_app is real_app
