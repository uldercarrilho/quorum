"""End-to-end regression tests verifying the pipeline against the official challenge dataset."""

import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.main import run_pipeline


class TestE2E(unittest.TestCase):
    """End-to-end integration test suite."""

    def setUp(self) -> None:
        self.challenge_data_dir = Path(__file__).parent.parent / "docs" / "challenge"

    def test_pipeline_e2e_challenge_data(self) -> None:
        """Run full pipeline on the challenge dataset and verify outputs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            leg_out, bill_out = run_pipeline(
                input_dir=self.challenge_data_dir,
                output_dir=tmp_path,
                db_path=":memory:",
            )

            self.assertTrue(leg_out.is_file())
            self.assertTrue(bill_out.is_file())

            # 1. Verify Legislators Output CSV
            with leg_out.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, ["id", "name", "num_supported_bills", "num_opposed_bills"])
                leg_rows = list(reader)

            self.assertEqual(len(leg_rows), 20)

            # Locate Rep. John Yarmuth (who had 0 votes in vote_results)
            yarmuth_row = next((r for r in leg_rows if r["id"] == "412211"), None)
            self.assertIsNotNone(yarmuth_row)
            self.assertEqual(yarmuth_row["name"], "Rep. John Yarmuth (D-KY-3)")
            self.assertEqual(int(yarmuth_row["num_supported_bills"]), 0)
            self.assertEqual(int(yarmuth_row["num_opposed_bills"]), 0)

            # 2. Verify Bills Output CSV
            with bill_out.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                self.assertEqual(
                    reader.fieldnames,
                    ["id", "title", "supporter_count", "opposer_count", "primary_sponsor"],
                )
                bill_rows = list(reader)

            self.assertEqual(len(bill_rows), 2)

            # Map bills by ID
            bills_by_id = {r["id"]: r for r in bill_rows}

            # Bill 2952375: Build Back Better Act
            bbb = bills_by_id["2952375"]
            self.assertEqual(bbb["title"], "H.R. 5376: Build Back Better Act")
            self.assertEqual(int(bbb["supporter_count"]), 6)
            self.assertEqual(int(bbb["opposer_count"]), 13)
            self.assertEqual(bbb["primary_sponsor"], "Rep. John Yarmuth (D-KY-3)")

            # Bill 2900994: Infrastructure Investment and Jobs Act (sponsor 400100 not in legislators.csv)
            infra = bills_by_id["2900994"]
            self.assertEqual(infra["title"], "H.R. 3684: Infrastructure Investment and Jobs Act")
            self.assertEqual(int(infra["supporter_count"]), 13)
            self.assertEqual(int(infra["opposer_count"]), 6)
            self.assertEqual(infra["primary_sponsor"], "Unknown")

    def test_pipeline_with_persistent_db_flag(self) -> None:
        """Verify that specifying --db-path persists the SQLite database to disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_file = tmp_path / "test_persisted.db"
            out_dir = tmp_path / "out"

            run_pipeline(
                input_dir=self.challenge_data_dir,
                output_dir=out_dir,
                db_path=str(db_file),
            )

            self.assertTrue(db_file.is_file())

            # Query the persisted database directly
            conn = sqlite3.connect(str(db_file))
            try:
                cursor = conn.cursor()
                leg_count = cursor.execute("SELECT COUNT(*) FROM legislators").fetchone()[0]
                bill_count = cursor.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
                self.assertEqual(leg_count, 20)
                self.assertEqual(bill_count, 2)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
