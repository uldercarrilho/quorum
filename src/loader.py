"""CSV ingestion engine for loading legislative data into SQLite."""

import csv
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


def _clean_str(val: Optional[str]) -> Optional[str]:
    """Strip whitespace and return None if empty."""
    if val is None:
        return None
    cleaned = val.strip()
    return cleaned if cleaned else None


def _clean_int(val: Optional[str]) -> Optional[int]:
    """Parse integer, returning None if empty or invalid."""
    cleaned = _clean_str(val)
    if cleaned is None:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def load_legislators(conn: sqlite3.Connection, csv_path: Union[str, Path]) -> int:
    """Ingest legislators.csv into the legislators table.
    
    Args:
        conn: Open SQLite connection.
        csv_path: Path to legislators.csv.
        
    Returns:
        Number of rows inserted.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Legislators CSV file not found at: {path}")

    rows: List[Tuple[int, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            cleaned_row = {k.strip(): v for k, v in row.items() if k}
            raw_id = _clean_int(cleaned_row.get("id"))
            name = _clean_str(cleaned_row.get("name"))
            if raw_id is None or name is None:
                logger.warning("Skipping invalid row in %s at line %d: %s", path.name, line_no, row)
                continue
            rows.append((raw_id, name))

    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO legislators (id, name) VALUES (?, ?);",
            rows,
        )
    logger.debug("Loaded %d legislators from %s", len(rows), path.name)
    return len(rows)


def load_bills(conn: sqlite3.Connection, csv_path: Union[str, Path]) -> int:
    """Ingest bills.csv into the bills table.
    
    Args:
        conn: Open SQLite connection.
        csv_path: Path to bills.csv.
        
    Returns:
        Number of rows inserted.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Bills CSV file not found at: {path}")

    rows: List[Tuple[int, str, Optional[int]]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            cleaned_row = {k.strip(): v for k, v in row.items() if k}
            raw_id = _clean_int(cleaned_row.get("id"))
            title = _clean_str(cleaned_row.get("title"))
            # Handles both 'sponsor_id' and 'Primary Sponsor' variations
            sponsor_id = _clean_int(cleaned_row.get("sponsor_id") or cleaned_row.get("Primary Sponsor"))
            
            if raw_id is None or title is None:
                logger.warning("Skipping invalid row in %s at line %d: %s", path.name, line_no, row)
                continue
            rows.append((raw_id, title, sponsor_id))

    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO bills (id, title, sponsor_id) VALUES (?, ?, ?);",
            rows,
        )
    logger.debug("Loaded %d bills from %s", len(rows), path.name)
    return len(rows)


def load_votes(conn: sqlite3.Connection, csv_path: Union[str, Path]) -> int:
    """Ingest votes.csv into the votes table.
    
    Args:
        conn: Open SQLite connection.
        csv_path: Path to votes.csv.
        
    Returns:
        Number of rows inserted.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Votes CSV file not found at: {path}")

    rows: List[Tuple[int, int]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            cleaned_row = {k.strip(): v for k, v in row.items() if k}
            raw_id = _clean_int(cleaned_row.get("id"))
            bill_id = _clean_int(cleaned_row.get("bill_id"))
            if raw_id is None or bill_id is None:
                logger.warning("Skipping invalid row in %s at line %d: %s", path.name, line_no, row)
                continue
            rows.append((raw_id, bill_id))

    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO votes (id, bill_id) VALUES (?, ?);",
            rows,
        )
    logger.debug("Loaded %d votes from %s", len(rows), path.name)
    return len(rows)


def load_vote_results(conn: sqlite3.Connection, csv_path: Union[str, Path]) -> int:
    """Ingest vote_results.csv into the vote_results table.
    
    Args:
        conn: Open SQLite connection.
        csv_path: Path to vote_results.csv.
        
    Returns:
        Number of rows inserted.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Vote results CSV file not found at: {path}")

    rows: List[Tuple[int, int, int, int]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            cleaned_row = {k.strip(): v for k, v in row.items() if k}
            raw_id = _clean_int(cleaned_row.get("id"))
            legislator_id = _clean_int(cleaned_row.get("legislator_id"))
            vote_id = _clean_int(cleaned_row.get("vote_id"))
            vote_type = _clean_int(cleaned_row.get("vote_type"))
            
            if raw_id is None or legislator_id is None or vote_id is None or vote_type is None:
                logger.warning("Skipping invalid row in %s at line %d: %s", path.name, line_no, row)
                continue
            if vote_type not in (1, 2):
                logger.warning("Skipping row with unsupported vote_type %s in %s at line %d", vote_type, path.name, line_no)
                continue
            rows.append((raw_id, legislator_id, vote_id, vote_type))

    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO vote_results (id, legislator_id, vote_id, vote_type) VALUES (?, ?, ?, ?);",
            rows,
        )
    logger.debug("Loaded %d vote results from %s", len(rows), path.name)
    return len(rows)


def load_all_csvs(conn: sqlite3.Connection, input_dir: Union[str, Path]) -> Dict[str, int]:
    """Load all 4 CSV datasets from the given directory into SQLite.
    
    Args:
        conn: Open SQLite connection.
        input_dir: Directory containing legislators.csv, bills.csv, votes.csv, vote_results.csv.
        
    Returns:
        Dict mapping entity names to loaded row counts.
    """
    dir_path = Path(input_dir)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {dir_path}")

    # Note: Order matters for foreign key dependencies (bills -> votes -> vote_results; legislators -> vote_results)
    counts = {
        "legislators": load_legislators(conn, dir_path / "legislators.csv"),
        "bills": load_bills(conn, dir_path / "bills.csv"),
        "votes": load_votes(conn, dir_path / "votes.csv"),
        "vote_results": load_vote_results(conn, dir_path / "vote_results.csv"),
    }
    logger.info(
        "Successfully loaded all datasets: %d legislators, %d bills, %d votes, %d vote results",
        counts["legislators"], counts["bills"], counts["votes"], counts["vote_results"]
    )
    return counts
