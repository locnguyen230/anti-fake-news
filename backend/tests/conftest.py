import os

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Never let developer AFN settings change deterministic tests."""
    for name in os.environ:
        if name.upper().startswith("AFN_"):
            monkeypatch.delenv(name)
