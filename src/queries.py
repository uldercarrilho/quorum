"""Analytical SQL queries for legislative data summaries."""

import sqlite3
from typing import Any, Dict, List

QUERY_LEGISLATOR_SUMMARY = """
SELECT 
    l.id AS id,
    l.name AS name,
    COUNT(DISTINCT CASE WHEN vr.vote_type = 1 THEN v.bill_id END) AS num_supported_bills,
    COUNT(DISTINCT CASE WHEN vr.vote_type = 2 THEN v.bill_id END) AS num_opposed_bills
FROM legislators l
LEFT JOIN vote_results vr ON l.id = vr.legislator_id
LEFT JOIN votes v ON vr.vote_id = v.id
GROUP BY l.id, l.name
ORDER BY l.id ASC;
"""

QUERY_BILL_SUMMARY = """
SELECT 
    b.id AS id,
    b.title AS title,
    COUNT(DISTINCT CASE WHEN vr.vote_type = 1 THEN vr.legislator_id END) AS supporter_count,
    COUNT(DISTINCT CASE WHEN vr.vote_type = 2 THEN vr.legislator_id END) AS opposer_count,
    COALESCE(l.name, 'Unknown') AS primary_sponsor
FROM bills b
LEFT JOIN legislators l ON b.sponsor_id = l.id
LEFT JOIN votes v ON b.id = v.bill_id
LEFT JOIN vote_results vr ON v.id = vr.vote_id
GROUP BY b.id, b.title, l.name
ORDER BY b.id ASC;
"""


def get_legislator_vote_summary(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Retrieve vote support/oppose metrics for every legislator.
    
    Args:
        conn: Open SQLite connection.
        
    Returns:
        List of dicts with keys: id, name, num_supported_bills, num_opposed_bills.
    """
    cursor = conn.cursor()
    cursor.execute(QUERY_LEGISLATOR_SUMMARY)
    results = [dict(row) for row in cursor.fetchall()]
    return results


def get_bill_vote_summary(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Retrieve supporter/opposer counts and primary sponsor for every bill.
    
    Args:
        conn: Open SQLite connection.
        
    Returns:
        List of dicts with keys: id, title, supporter_count, opposer_count, primary_sponsor.
    """
    cursor = conn.cursor()
    cursor.execute(QUERY_BILL_SUMMARY)
    results = [dict(row) for row in cursor.fetchall()]
    return results
