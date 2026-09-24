"""Unit tests for analytical SQL queries and edge cases (queries.py)."""

import unittest

from src.db import get_connection
from src.queries import get_bill_vote_summary, get_legislator_vote_summary
from src.schema import init_schema


class TestQueries(unittest.TestCase):
    """Test suite for legislative analytical queries."""

    def setUp(self) -> None:
        """Create an ephemeral in-memory database with initialized schema."""
        self.db_conn = get_connection(":memory:")
        init_schema(self.db_conn)

    def tearDown(self) -> None:
        """Close connection."""
        self.db_conn.close()

    def test_legislator_with_zero_votes_reports_zeros(self) -> None:
        """A legislator who cast no votes should report 0 supported and 0 opposed bills."""
        self.db_conn.execute("INSERT INTO legislators (id, name) VALUES (1, 'Silent Legislator')")
        self.db_conn.commit()

        summary = get_legislator_vote_summary(self.db_conn)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["id"], 1)
        self.assertEqual(summary[0]["name"], "Silent Legislator")
        self.assertEqual(summary[0]["num_supported_bills"], 0)
        self.assertEqual(summary[0]["num_opposed_bills"], 0)

    def test_bill_with_zero_votes_reports_zeros(self) -> None:
        """A bill that received no votes should report 0 supporters and 0 opposers."""
        self.db_conn.execute("INSERT INTO bills (id, title, sponsor_id) VALUES (10, 'Unvoted Bill', NULL)")
        self.db_conn.commit()

        summary = get_bill_vote_summary(self.db_conn)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["id"], 10)
        self.assertEqual(summary[0]["title"], "Unvoted Bill")
        self.assertEqual(summary[0]["supporter_count"], 0)
        self.assertEqual(summary[0]["opposer_count"], 0)
        self.assertEqual(summary[0]["primary_sponsor"], "Unknown")

    def test_bill_with_missing_sponsor_resolves_to_unknown(self) -> None:
        """A bill with a sponsor_id not present in legislators table reports 'Unknown'."""
        self.db_conn.execute("INSERT INTO bills (id, title, sponsor_id) VALUES (20, 'Mystery Bill', 9999)")
        self.db_conn.commit()

        summary = get_bill_vote_summary(self.db_conn)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["primary_sponsor"], "Unknown")

    def test_bill_with_valid_sponsor_resolves_name(self) -> None:
        """A bill with a valid sponsor_id reports the sponsor's name."""
        self.db_conn.execute("INSERT INTO legislators (id, name) VALUES (100, 'Senator Smith')")
        self.db_conn.execute("INSERT INTO bills (id, title, sponsor_id) VALUES (30, 'Education Act', 100)")
        self.db_conn.commit()

        summary = get_bill_vote_summary(self.db_conn)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["primary_sponsor"], "Senator Smith")

    def test_multi_vote_on_same_bill_does_not_double_count(self) -> None:
        """If a bill has multiple votes (e.g. amendments), distinct counting prevents double-counting."""
        # Seed 1 legislator, 1 bill
        self.db_conn.execute("INSERT INTO legislators (id, name) VALUES (1, 'Alice')")
        self.db_conn.execute("INSERT INTO bills (id, title) VALUES (10, 'Omnibus Bill')")
        # Seed 2 separate votes on the same bill (bill_id = 10)
        self.db_conn.execute("INSERT INTO votes (id, bill_id) VALUES (101, 10)")
        self.db_conn.execute("INSERT INTO votes (id, bill_id) VALUES (102, 10)")
        # Alice votes Yea on BOTH votes of this same bill
        self.db_conn.execute("INSERT INTO vote_results (id, legislator_id, vote_id, vote_type) VALUES (1, 1, 101, 1)")
        self.db_conn.execute("INSERT INTO vote_results (id, legislator_id, vote_id, vote_type) VALUES (2, 1, 102, 1)")
        self.db_conn.commit()

        leg_summary = get_legislator_vote_summary(self.db_conn)
        self.assertEqual(len(leg_summary), 1)
        # num_supported_bills should be 1 (distinct bill), NOT 2
        self.assertEqual(leg_summary[0]["num_supported_bills"], 1)
        self.assertEqual(leg_summary[0]["num_opposed_bills"], 0)

        bill_summary = get_bill_vote_summary(self.db_conn)
        self.assertEqual(len(bill_summary), 1)
        # supporter_count should be 1 (distinct legislator), NOT 2
        self.assertEqual(bill_summary[0]["supporter_count"], 1)
        self.assertEqual(bill_summary[0]["opposer_count"], 0)

    def test_mixed_voting_behavior(self) -> None:
        """Legislator who voted Yea on one bill and Nay on another reports 1 supported and 1 opposed."""
        self.db_conn.execute("INSERT INTO legislators (id, name) VALUES (1, 'Alice')")
        self.db_conn.execute("INSERT INTO bills (id, title) VALUES (10, 'Bill A'), (20, 'Bill B')")
        self.db_conn.execute("INSERT INTO votes (id, bill_id) VALUES (101, 10), (102, 20)")
        self.db_conn.execute("INSERT INTO vote_results (id, legislator_id, vote_id, vote_type) VALUES (1, 1, 101, 1)")
        self.db_conn.execute("INSERT INTO vote_results (id, legislator_id, vote_id, vote_type) VALUES (2, 1, 102, 2)")
        self.db_conn.commit()

        leg_summary = get_legislator_vote_summary(self.db_conn)
        self.assertEqual(len(leg_summary), 1)
        self.assertEqual(leg_summary[0]["num_supported_bills"], 1)
        self.assertEqual(leg_summary[0]["num_opposed_bills"], 1)


if __name__ == "__main__":
    unittest.main()
