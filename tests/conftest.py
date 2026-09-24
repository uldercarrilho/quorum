"""Shared pytest fixtures and test setup."""

import sqlite3
from pathlib import Path
from typing import Generator

import pytest

from src.db import get_connection
from src.schema import init_schema


@pytest.fixture
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Provide an in-memory SQLite database connection with initialized schema."""
    conn = get_connection(":memory:")
    init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def challenge_data_dir() -> Path:
    """Return the path to the official challenge dataset."""
    return Path(__file__).parent.parent / "docs" / "challenge"
