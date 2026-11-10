"""Shared pytest bootstrap for MATRIX integration tests.

Environment is configured *before* any MATRIX module imports ``config.settings`` so the
suite never depends on a ``D:`` drive, a developer machine, or production data.
"""
from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEST_DATA_ROOT = _PROJECT_ROOT / ".testdata"

os.environ.setdefault("MATRIX_ENV", "test")
os.environ.setdefault("MATRIX_DEBUG", "false")
# Developer Studio endpoints are opt-in; tests exercise them explicitly.
os.environ.setdefault("MATRIX_DEVELOPER_MODE", "true")
if not os.environ.get("MATRIX_DATA_DIR"):
    os.environ["MATRIX_DATA_DIR"] = str(_TEST_DATA_ROOT)

import asyncio  # noqa: E402

from database.init_db import init_database  # noqa: E402


def pytest_sessionstart(session):
    """Create the configured test database schema before any test module imports it."""
    initialized = asyncio.run(init_database())
    if not initialized:
        raise RuntimeError("Could not initialize the MATRIX test database schema.")
