#!/usr/bin/env python3
"""
Harvest OpenAIRE Data Script
=============================
Main script to harvest Austrian research publications from OpenAIRE.

Usage:
    python scripts/harvest_openaire.py                    # Harvest all organizations
    python scripts/harvest_openaire.py --max-records 100  # Limit to 100 per org
    python scripts/harvest_openaire.py --single UNIVIE    # Single organization

This script:
1. Initializes the database
2. Queries OpenAIRE for Austrian research
3. Stores publications in SQLite
4. Prints statistics and progress
"""

import asyncio
import logging
import argparse
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db
from app.harvesters.openaire import OpenAIREHarvester, AUSTRIAN_UNIVERSITIES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("harvest.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    """Main harvest function."""

    parser = argparse.ArgumentParser(
        description="Harvest Austrian research publications from OpenAIRE"
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=1000,
        help="Maximum records per organization (default: 1000)",
    )
    parser.add_argument(
        "--single",
        type=str,
        help="Harvest single organization by ROR ID or name",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size per API request (default: 100)",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Austrian Research Metadata Platform - OpenAIRE Harvester")
    logger.info("=" * 70)

    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info("✓ Database ready")

    # Create harvester
    harvester = OpenAIREHarvester(
        batch_size=args.batch_size,
        timeout=args.timeout,
    )

    # Determine what to harvest
    if args.single:
        # Harvest single organization
        ror_id = None
        org_name = None

        # Check if it's a ROR ID
        if args.single in AUSTRIAN_UNIVERSITIES:
            ror_id = args.single
            org_name = AUSTRIAN_UNIVERSITIES[args.single]
        else:
            # Search by name
            for rid, rname in AUSTRIAN_UNIVERSITIES.items():
                if args.single.lower() in rname.lower():
                    ror_id = rid
                    org_name = rname
                    break

        if not ror_id:
            logger.error(f"Organization not found: {args.single}")
            logger.info("Available organizations:")
            for rid, rname in AUSTRIAN_UNIVERSITIES.items():
                logger.info(f"  {rid}: {rname}")
            return

        logger.info(f"Harvesting single organization: {org_name}")
        stats = await harvester.harvest_organization(ror_id, org_name, args.max_records)

        # Print summary
        print("\n" + "=" * 70)
        print("HARVEST SUMMARY")
        print("=" * 70)
        print(json.dumps(stats, default=str, indent=2))

    else:
        # Harvest all organizations
        logger.info(f"Harvesting all {len(AUSTRIAN_UNIVERSITIES)} Austrian universities")
        logger.info(f"Max records per organization: {args.max_records}")

        stats = await harvester.harvest_all(args.max_records)

        # Print summary
        print("\n" + "=" * 70)
        print("HARVEST SUMMARY - ALL ORGANIZATIONS")
        print("=" * 70)
        print(
            f"Total Fetched: {stats['total_fetched']}\n"
            f"Total Stored:  {stats['total_stored']}\n"
            f"Duplicates:    {stats['total_duplicates']}\n"
            f"Errors:        {stats['total_errors']}\n"
        )

        print("Per Organization:")
        for org_name, org_stats in stats["organizations"].items():
            if "error" in org_stats:
                print(f"  {org_name}: ERROR - {org_stats['error']}")
            else:
                print(
                    f"  {org_name}: "
                    f"Fetched {org_stats['total_fetched']}, "
                    f"Stored {org_stats['total_stored']}, "
                    f"Duplicates {org_stats['duplicates']}"
                )

        print("=" * 70)

        # Save statistics
        stats_file = Path("data/harvest_stats.json")
        with open(stats_file, "w") as f:
            json.dump(stats, f, default=str, indent=2)
        logger.info(f"Statistics saved to {stats_file}")

    logger.info("Harvest complete!")


if __name__ == "__main__":
    asyncio.run(main())
