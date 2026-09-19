import sys
from pathlib import Path

import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _clear_api_caches():
    """The scene and per-catalog caches are process-global; clear both between
    tests so mocked fetchers in one test never serve a stale result to another."""
    from app.api import _clear_catalog_cache, _clear_scene_cache
    from app.metrics import source_failures

    _clear_scene_cache()
    _clear_catalog_cache()
    source_failures.reset()
    # Live Horizons calls are integration checks, not unit-test dependencies.
    with patch("app.horizons.fetch_vectors", side_effect=ValueError("offline test")):
        yield
