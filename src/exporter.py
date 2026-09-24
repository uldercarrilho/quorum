"""CSV export utilities adhering to required output schemas."""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union

logger = logging.getLogger(__name__)

LEGISLATOR_SUMMARY_COLUMNS = [
    "id",
    "name",
    "num_supported_bills",
    "num_opposed_bills",
]

BILL_SUMMARY_COLUMNS = [
    "id",
    "title",
    "supporter_count",
    "opposer_count",
    "primary_sponsor",
]


def export_to_csv(
    data: Sequence[Dict[str, Any]],
    fieldnames: Sequence[str],
    output_path: Union[str, Path],
) -> Path:
    """Export a sequence of dictionary rows to a CSV file.
    
    Args:
        data: List of dictionary records to write.
        fieldnames: Column header names in desired order.
        output_path: Destination file path.
        
    Returns:
        Path of the written CSV file.
    """
    path = Path(output_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    logger.info("Exported %d rows to %s", len(data), path)
    return path


def export_legislator_summary(
    data: Sequence[Dict[str, Any]],
    output_path: Union[str, Path],
) -> Path:
    """Export legislator support/oppose summary to CSV.
    
    Args:
        data: Summary records for legislators.
        output_path: Output CSV file path.
        
    Returns:
        Path of written CSV file.
    """
    return export_to_csv(data, LEGISLATOR_SUMMARY_COLUMNS, output_path)


def export_bill_summary(
    data: Sequence[Dict[str, Any]],
    output_path: Union[str, Path],
) -> Path:
    """Export bill support/oppose summary to CSV.
    
    Args:
        data: Summary records for bills.
        output_path: Output CSV file path.
        
    Returns:
        Path of written CSV file.
    """
    return export_to_csv(data, BILL_SUMMARY_COLUMNS, output_path)
