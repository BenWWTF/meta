#!/usr/bin/env python3
"""
FWF Project Harvesting CLI Tool
================================

Harvest funded research projects from FWF (Austrian Science Fund).

Usage:
    python harvest_fwf.py                    # Harvest all projects
    python harvest_fwf.py --max-records 500  # Limited test
    python harvest_fwf.py --output stats.json

Requires:
    - PYTHONPATH includes parent directory
    - Database initialized (via app.database.init_db)
    - Internet connection to FWF Research Radar API

Note:
    - FWF funds ~4000 projects across all research areas
    - Project links to publications enable funding ROI assessment
    - Run after publication harvesting for better linking
"""

import asyncio
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.harvesters.fwf import harvest_fwf
from app.database import init_db, SessionLocal, Project

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("harvest_fwf.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for FWF project harvesting."""

    parser = argparse.ArgumentParser(
        description="Harvest funded research projects from FWF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Harvest all FWF projects
  python harvest_fwf.py

  # Test with limited projects
  python harvest_fwf.py --max-records 500

  # Save statistics to custom file
  python harvest_fwf.py --output data/fwf_stats.json
        """
    )

    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Maximum projects to harvest (default: unlimited)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/fwf_harvest_stats.json",
        help="Output file for harvest statistics"
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

    # Run harvest
    logger.info("=" * 80)
    logger.info("FWF PROJECT HARVEST STARTING")
    logger.info("=" * 80)
    logger.info(f"Max records: {args.max_records or 'unlimited'}")
    logger.info("=" * 80)

    try:
        stats = await harvest_fwf(max_records=args.max_records)

        # Save statistics
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2, default=str)

        # Log summary
        logger.info("=" * 80)
        logger.info("FWF PROJECT HARVEST COMPLETE")
        logger.info("=" * 80)

        if "total_fetched" in stats:
            logger.info(f"Total fetched: {stats['total_fetched']}")
            logger.info(f"Total stored: {stats['total_stored']}")
            logger.info(f"Duplicates: {stats['duplicates']}")
            logger.info(f"Linked to publications: {stats['linked_to_publications']}")
            logger.info(f"Errors: {stats['errors']}")

            if stats['total_fetched'] > 0:
                duplicate_pct = (stats['duplicates'] / stats['total_fetched']) * 100
                logger.info(f"Duplicate rate: {duplicate_pct:.1f}%")

        # Count total projects
        db = SessionLocal()
        total = db.query(Project).count()
        db.close()
        logger.info(f"Total projects in database: {total}")

        logger.info(f"Statistics saved to: {output_path}")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Harvest interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error during harvest: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
