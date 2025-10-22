#!/usr/bin/env python3
"""
Researcher Enrichment CLI Tool
===============================

Extract and consolidate researcher profiles from publication author data.

Usage:
    python enrich_researchers.py                    # Enrich all researchers
    python enrich_researchers.py --threshold 85     # Custom fuzzy match threshold
    python enrich_researchers.py --output stats.json

Requires:
    - PYTHONPATH includes parent directory
    - Database initialized with publications
"""

import asyncio
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.harvesters.researcher_enricher import enrich_researchers
from app.database import init_db, SessionLocal, Researcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("enrich_researchers.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for researcher enrichment."""

    parser = argparse.ArgumentParser(
        description="Extract and enrich researcher profiles from publication data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enrich all researchers
  python enrich_researchers.py

  # Use custom fuzzy match threshold
  python enrich_researchers.py --threshold 85

  # Save statistics to custom file
  python enrich_researchers.py --output data/researcher_stats.json
        """
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=90,
        help="Fuzzy match threshold for author deduplication (0-100, default: 90)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/researcher_enrichment_stats.json",
        help="Output file for enrichment statistics"
    )

    args = parser.parse_args()

    # Validate threshold
    if not 0 <= args.threshold <= 100:
        logger.error("Threshold must be between 0 and 100")
        return

    # Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # Run enrichment
    logger.info("=" * 80)
    logger.info("RESEARCHER ENRICHMENT STARTING")
    logger.info("=" * 80)
    logger.info(f"Fuzzy match threshold: {args.threshold}%")
    logger.info("=" * 80)

    try:
        stats = enrich_researchers()

        # Save statistics
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2, default=str)

        # Log summary
        logger.info("=" * 80)
        logger.info("RESEARCHER ENRICHMENT COMPLETE")
        logger.info("=" * 80)

        if "researchers_created" in stats:
            logger.info(f"Researchers created: {stats['researchers_created']}")
            logger.info(f"Researchers updated: {stats['researchers_updated']}")
            logger.info(f"Authors processed: {stats['authors_processed']}")
            logger.info(f"Disambiguation merges: {stats['disambiguation_merges']}")
            logger.info(f"Errors: {stats['errors']}")

            # Count total researchers
            db = SessionLocal()
            total = db.query(Researcher).count()
            db.close()
            logger.info(f"Total researchers in database: {total}")

        logger.info(f"Statistics saved to: {output_path}")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Enrichment interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error during enrichment: {e}", exc_info=True)


if __name__ == "__main__":
    main()
