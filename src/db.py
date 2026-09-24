"""Database connection and lifecycle management for SQLite."""

import sqlite3
from typing import Union
from pathlib import Path


def get_connection(db_path: Union[str, Path] = ":memory:") -> sqlite3.Connection:
    """Create and return a configured SQLite connection.
    
    Args:
        db_path: Path to database file or ':memory:' for ephemeral in-memory database.
        
    Returns:
        Configured sqlite3.Connection instance with foreign keys enabled and Row factory.
    """
    path_str = str(db_path)
    
    # If path is a file on disk, ensure parent directory exists
    if path_str != ":memory:":
        file_path = Path(path_str)
        if file_path.parent and not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
    conn = sqlite3.connect(path_str)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
