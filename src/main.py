"""CLI entrypoint and orchestration pipeline for Quorum Legislative Data."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Tuple, Union

from src.db import get_connection
from src.exporter import export_bill_summary, export_legislator_summary
from src.loader import load_all_csvs
from src.queries import get_bill_vote_summary, get_legislator_vote_summary
from src.schema import init_schema

logger = logging.getLogger("quorum")


def configure_logging(level_name: str) -> None:
    """Configure stdout logging with standard format."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_pipeline(
    input_dir: Union[str, Path] = Path("docs/challenge"),
    output_dir: Union[str, Path] = Path("output"),
    db_path: str = ":memory:",
) -> Tuple[Path, Path]:
    """Execute the end-to-end data processing pipeline.
    
    Args:
        input_dir: Directory containing input CSV files.
        output_dir: Directory where output CSV reports will be saved.
        db_path: SQLite database path (':memory:' for in-memory).
        
    Returns:
        Tuple of paths to (legislators_summary_csv, bills_summary_csv).
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    logger.info("Starting legislative data pipeline")
    logger.info("Input directory:  %s", input_path.resolve())
    logger.info("Output directory: %s", output_path.resolve())
    logger.info("Database path:    %s", db_path)

    # 1. Initialize SQLite Database & Schema
    conn = get_connection(db_path)
    try:
        init_schema(conn)

        # 2. Ingest CSV Data
        counts = load_all_csvs(conn, input_path)

        # 3. Compute Analytical Summaries
        legislator_records = get_legislator_vote_summary(conn)
        bill_records = get_bill_vote_summary(conn)

        # 4. Export CSV Deliverables
        leg_out_file = output_path / "legislators-support-oppose-count.csv"
        bill_out_file = output_path / "bills.csv"

        export_legislator_summary(legislator_records, leg_out_file)
        export_bill_summary(bill_records, bill_out_file)

        logger.info("Pipeline completed successfully!")
        logger.info("Generated: %s (%d rows)", leg_out_file, len(legislator_records))
        logger.info("Generated: %s (%d rows)", bill_out_file, len(bill_records))

        return leg_out_file, bill_out_file
    finally:
        conn.close()


def parse_args(args=None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Quorum Legislative Data Processor - Ingests voting data and generates summary reports."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("docs/challenge"),
        help="Path to directory containing input CSV files (default: docs/challenge)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Path to directory where output CSV files will be written (default: output)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=":memory:",
        help="Path to SQLite database file or ':memory:' for ephemeral database (default: :memory:)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging verbosity (default: INFO)",
    )
    return parser.parse_args(args)


def main() -> None:
    """Main CLI entrypoint."""
    args = parse_args()
    configure_logging(args.log_level)

    try:
        leg_path, bill_path = run_pipeline(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            db_path=args.db_path,
        )
        print("\nSUCCESS: Summary reports generated:")
        print(f"  1. Legislator summary: {leg_path}")
        print(f"  2. Bill summary:       {bill_path}")
    except Exception as exc:
        logger.error("Execution failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
