#!/usr/bin/env python3
"""
ORCID Enrichment CLI Tool
==========================

Enrich researcher profiles with ORCID data.

Usage:
    python enrich_orcid.py                    # Enrich all researchers
    python enrich_orcid.py --max-records 500  # Limit to first 500
    python enrich_orcid.py --output stats.json

Requires:
    - PYTHONPATH includes parent directory
    - Database initialized with researchers (from enrich_researchers.py)
    - No ORCID authentication needed (public API)

Note:
    - Run after scripts/enrich_researchers.py
    - Standard public API: 24 requests/second
    - Enrichment takes ~1-2 hours for 15K+ researchers
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

from app.harvesters.orcid import enrich_researchers_orcid
from app.database import init_db, SessionLocal, Researcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("enrich_orcid.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for ORCID enrichment."""

    parser = argparse.ArgumentParser(
        description="Enrich researcher profiles with ORCID data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enrich all researchers without ORCID
  python enrich_orcid.py

  # Test with limited researchers
  python enrich_orcid.py --max-records 500

  # Save statistics to custom file
  python enrich_orcid.py --output data/orcid_stats.json
        """
    )

    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Maximum researchers to enrich (default: unlimited)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/orcid_enrichment_stats.json",
        help="Output file for enrichment statistics"
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

    # Check available researchers
    db = SessionLocal()
    total_researchers = db.query(Researcher).count()
    without_orcid = db.query(Researcher).filter(Researcher.orcid_id.is_(None)).count()
    db.close()

    logger.info(f"Total researchers in database: {total_researchers}")
    logger.info(f"Researchers without ORCID: {without_orcid}")

    # Run enrichment
    logger.info("=" * 80)
    logger.info("ORCID ENRICHMENT STARTING")
    logger.info("=" * 80)
    logger.info(f"Max records: {args.max_records or 'unlimited'}")
    logger.info("=" * 80)

    try:
        stats = await enrich_researchers_orcid(max_records=args.max_records)

        # Save statistics
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2, default=str)

        # Log summary
        logger.info("=" * 80)
        logger.info("ORCID ENRICHMENT COMPLETE")
        logger.info("=" * 80)

        if "enriched" in stats:
            logger.info(f"Total processed: {stats['total_researchers']}")
            logger.info(f"Enriched: {stats['enriched']}")
            logger.info(f"ORCID found: {stats['orcid_found']}")
            logger.info(f"ORCID profile matched: {stats['orcid_profile_matched']}")
            logger.info(f"Employment updated: {stats['employment_updated']}")
            logger.info(f"Education updated: {stats['education_updated']}")
            logger.info(f"Errors: {stats['errors']}")

            if stats['total_researchers'] > 0:
                enrichment_rate = (stats['enriched'] / stats['total_researchers']) * 100
                logger.info(f"Enrichment rate: {enrichment_rate:.1f}%")

        logger.info(f"Statistics saved to: {output_path}")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Enrichment interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error during enrichment: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
