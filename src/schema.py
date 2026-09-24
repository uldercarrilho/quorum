"""Database schema definitions and DDL initialization for legislative data."""

import sqlite3

SCHEMA_DDL = """
-- Legislators table
CREATE TABLE IF NOT EXISTS legislators (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- Bills table (sponsor_id is nullable and soft-referenced to accommodate unknown/missing sponsors)
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    sponsor_id INTEGER
);

-- Votes table (each vote is associated with a bill)
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY,
    bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE
);

-- Vote results table (records each individual vote cast by a legislator)
CREATE TABLE IF NOT EXISTS vote_results (
    id INTEGER PRIMARY KEY,
    legislator_id INTEGER NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
    vote_id INTEGER NOT NULL REFERENCES votes(id) ON DELETE CASCADE,
    vote_type INTEGER NOT NULL CHECK (vote_type IN (1, 2))
);

-- Performance and lookup indexes
CREATE INDEX IF NOT EXISTS idx_bills_sponsor ON bills(sponsor_id);
CREATE INDEX IF NOT EXISTS idx_votes_bill_id ON votes(bill_id);
CREATE INDEX IF NOT EXISTS idx_vote_results_leg ON vote_results(legislator_id);
CREATE INDEX IF NOT EXISTS idx_vote_results_vote ON vote_results(vote_id);
CREATE INDEX IF NOT EXISTS idx_vote_results_type ON vote_results(vote_type);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Initialize tables and indexes in the database.
    
    Args:
        conn: Open SQLite database connection.
    """
    conn.executescript(SCHEMA_DDL)
    conn.commit()
