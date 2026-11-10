"""Shared pytest bootstrap for MATRIX integration tests."""
import asyncio

from database.init_db import init_database


def pytest_sessionstart(session):
    """Create the configured test database schema before collection-order-dependent tests."""
    initialized = asyncio.run(init_database())
    if not initialized:
        raise RuntimeError("Could not initialize the MATRIX test database schema.")
