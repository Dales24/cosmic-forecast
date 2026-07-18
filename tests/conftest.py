import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _clear_scene_cache():
    """The /api/scene cache is process-global; clear it between tests so mocked
    fetchers in one test never serve a stale scene to another."""
    from app.api import _clear_scene_cache as clear

    clear()
    yield
