"""Tests for the CSV ingestion engine (loader.py)."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.db import get_connection
from src.loader import (
    load_all_csvs,
    load_bills,
    load_legislators,
    load_vote_results,
    load_votes,
)
from src.schema import init_schema


class TestLoader(unittest.TestCase):
    """Test suite for CSV ingestion functions."""

    def setUp(self) -> None:
        """Create an ephemeral in-memory database with initialized schema."""
        self.db_conn = get_connection(":memory:")
        init_schema(self.db_conn)
        self.challenge_data_dir = Path(__file__).parent.parent / "docs" / "challenge"

    def tearDown(self) -> None:
        """Close connection."""
        self.db_conn.close()

    def test_load_all_csvs_from_challenge_data(self) -> None:
        """Test ingesting all 4 challenge CSV files into SQLite."""
        counts = load_all_csvs(self.db_conn, self.challenge_data_dir)

        self.assertEqual(counts["legislators"], 20)
        self.assertEqual(counts["bills"], 2)
        self.assertEqual(counts["votes"], 2)
        self.assertEqual(counts["vote_results"], 38)

        # Verify counts directly in the database
        cursor = self.db_conn.cursor()
        self.assertEqual(cursor.execute("SELECT COUNT(*) FROM legislators").fetchone()[0], 20)
        self.assertEqual(cursor.execute("SELECT COUNT(*) FROM bills").fetchone()[0], 2)
        self.assertEqual(cursor.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 2)
        self.assertEqual(cursor.execute("SELECT COUNT(*) FROM vote_results").fetchone()[0], 38)

    def test_loader_missing_file_raises_error(self) -> None:
        """Test that missing CSV files raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_file = Path(tmp_dir) / "non_existent.csv"
            with self.assertRaises(FileNotFoundError):
                load_legislators(self.db_conn, missing_file)

    def test_loader_missing_dir_raises_error(self) -> None:
        """Test that missing directory raises NotADirectoryError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_dir = Path(tmp_dir) / "non_existent_dir"
            with self.assertRaises(NotADirectoryError):
                load_all_csvs(self.db_conn, missing_dir)

    def test_loader_handles_whitespace_and_empty_sponsor(self) -> None:
        """Test that whitespace is cleaned and blank sponsors are handled as NULL."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bills_csv = Path(tmp_dir) / "bills.csv"
            bills_csv.write_text("id, title , sponsor_id \n100,  Healthcare Reform  , \n", encoding="utf-8")

            loaded = load_bills(self.db_conn, bills_csv)
            self.assertEqual(loaded, 1)

            row = self.db_conn.cursor().execute("SELECT id, title, sponsor_id FROM bills WHERE id = 100").fetchone()
            self.assertEqual(row[0], 100)
            self.assertEqual(row[1], "Healthcare Reform")
            self.assertIsNone(row[2])

    def test_loader_skips_invalid_vote_type(self) -> None:
        """Test that rows with vote_type not in (1, 2) are skipped gracefully."""
        self.db_conn.execute("INSERT INTO legislators (id, name) VALUES (1, 'Alice')")
        self.db_conn.execute("INSERT INTO bills (id, title) VALUES (10, 'Bill A')")
        self.db_conn.execute("INSERT INTO votes (id, bill_id) VALUES (50, 10)")
        self.db_conn.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            vr_csv = Path(tmp_dir) / "vote_results.csv"
            vr_csv.write_text(
                "id,legislator_id,vote_id,vote_type\n"
                "1,1,50,1\n"
                "2,1,50,3\n",
                encoding="utf-8",
            )

            loaded = load_vote_results(self.db_conn, vr_csv)
            self.assertEqual(loaded, 1)

            rows = self.db_conn.cursor().execute("SELECT id, vote_type FROM vote_results").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1], 1)


if __name__ == "__main__":
    unittest.main()
