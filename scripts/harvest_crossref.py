#!/usr/bin/env python3
"""
Crossref Harvester CLI Tool
============================

Harvest publication metadata from Crossref API for Austrian institutions.

Usage:
    python harvest_crossref.py                           # All organizations
    python harvest_crossref.py --max-records 100         # Limited test
    python harvest_crossref.py --single "03prydq77"      # Single organization
    python harvest_crossref.py --single "03prydq77" --max-records 500

Requires:
    - PYTHONPATH includes parent directory
    - Database initialized (via app.database.init_db)
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

from app.harvesters.crossref import harvest_crossref_async
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("harvest_crossref.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

# Crossref organization ROR IDs
AUSTRIAN_RORS = {
    "03prydq77": "University of Vienna",
    "05qghxh33": "TU Wien",
    "03ak46v85": "University of Innsbruck",
    "035xkbk20": "University of Graz",
    "00rbhpj83": "JKU Linz",
    "03ktj6r74": "Medical University of Vienna",
    "0534sfd39": "TU Graz",
    "02kgz0p91": "University of Salzburg",
    "0285gxx56": "Medical University of Graz",
    "04rbhpj83": "Medical University of Innsbruck",
    "00h7cqc46": "BOKU Vienna",
    "013tf3c58": "WU Vienna",
    "03kfx5e42": "University of Klagenfurt",
    "04r3pxg27": "Montanuniversität Leoben",
    "03anc3s24": "Austrian Academy of Sciences",
}


async def main():
    """Main entry point for Crossref harvesting."""

    parser = argparse.ArgumentParser(
        description="Harvest publications from Crossref API for Austrian institutions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Harvest all organizations
  python harvest_crossref.py

  # Test with limited records
  python harvest_crossref.py --max-records 100

  # Harvest single organization
  python harvest_crossref.py --single "03prydq77"

  # Single org with record limit
  python harvest_crossref.py --single "03prydq77" --max-records 500
        """
    )

    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Maximum records to harvest per organization (default: unlimited)"
    )

    parser.add_argument(
        "--single",
        type=str,
        default=None,
        help="Harvest single organization by ROR ID"
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout in seconds (default: 30.0)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/harvest_crossref_stats.json",
        help="Output file for harvest statistics (default: data/harvest_crossref_stats.json)"
    )

    args = parser.parse_args()

    # Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # Validate single org if specified
    if args.single and args.single not in AUSTRIAN_RORS:
        logger.error(f"Unknown ROR ID: {args.single}")
        logger.info(f"Valid ROR IDs: {', '.join(AUSTRIAN_RORS.keys())}")
        return

    # Log harvest parameters
    logger.info("=" * 80)
    logger.info("CROSSREF HARVEST STARTING")
    logger.info("=" * 80)
    logger.info(f"Max records per org: {args.max_records or 'unlimited'}")
    logger.info(f"HTTP timeout: {args.timeout}s")
    if args.single:
        logger.info(f"Single org mode: {AUSTRIAN_RORS[args.single]} ({args.single})")
    else:
        logger.info(f"Multi-org mode: {len(AUSTRIAN_RORS)} Austrian organizations")
    logger.info("=" * 80)

    # Run harvest
    try:
        stats = await harvest_crossref_async(max_records=args.max_records)

        # Log summary
        logger.info("=" * 80)
        logger.info("CROSSREF HARVEST COMPLETE")
        logger.info("=" * 80)

        if "total_fetched" in stats:
            logger.info(f"Total fetched: {stats['total_fetched']}")
            logger.info(f"Total stored: {stats['total_stored']}")
            logger.info(f"Duplicates: {stats['total_duplicates']}")
            logger.info(f"Errors: {stats['total_errors']}")

            if stats['total_fetched'] > 0:
                duplicate_pct = (stats['total_duplicates'] / stats['total_fetched']) * 100
                logger.info(f"Duplicate rate: {duplicate_pct:.1f}%")

        # Save statistics
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2, default=str)

        logger.info(f"Statistics saved to: {output_path}")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Harvest interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error during harvest: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
