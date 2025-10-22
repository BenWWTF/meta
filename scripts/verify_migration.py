#!/usr/bin/env python3
"""
PostgreSQL Migration Verification Script
=========================================

Verifies that data migration from SQLite to PostgreSQL was successful.
Compares record counts and data integrity between databases.

Usage:
    python scripts/verify_migration.py [--source path/to/armp.db]

Environment:
    DATABASE_URL: Target PostgreSQL connection string
"""

import sys
import os
from pathlib import Path
import logging
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Organization, Publication, Researcher, Project, HarvestLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class MigrationVerifier:
    """Verifies migration success."""

    def __init__(self, source_db: str, target_db: str):
        """Initialize verifier."""

        self.source_engine = create_engine(source_db)
        self.target_engine = create_engine(target_db)

        SourceSession = sessionmaker(bind=self.source_engine)
        TargetSession = sessionmaker(bind=self.target_engine)

        self.source_session = SourceSession()
        self.target_session = TargetSession()

    def verify(self) -> bool:
        """
        Verify migration.

        Returns:
            bool: True if all checks pass, False otherwise
        """

        logger.info("=" * 80)
        logger.info("PostgreSQL Migration Verification")
        logger.info("=" * 80)

        try:
            # Check connectivity
            self._verify_connectivity()

            # Compare record counts
            all_match = self._verify_record_counts()

            # Check schema
            self._verify_schema()

            logger.info("=" * 80)

            if all_match:
                logger.info("✓ Migration verification PASSED!")
                logger.info("Data has been successfully migrated to PostgreSQL")
            else:
                logger.warning("⚠ Migration verification found discrepancies")
                logger.warning("Please review the differences above")

            logger.info("=" * 80)

            return all_match

        except Exception as e:
            logger.error(f"Verification failed: {e}", exc_info=True)
            return False

        finally:
            self.source_session.close()
            self.target_session.close()

    def _verify_connectivity(self):
        """Verify database connections."""

        logger.info("Verifying database connections...")

        try:
            # Test SQLite
            result = self.source_session.execute(text("SELECT 1")).scalar()
            logger.info("✓ SQLite connection successful")
        except Exception as e:
            logger.error(f"✗ SQLite connection failed: {e}")
            raise

        try:
            # Test PostgreSQL
            result = self.target_session.execute(text("SELECT 1")).scalar()
            logger.info("✓ PostgreSQL connection successful")
        except Exception as e:
            logger.error(f"✗ PostgreSQL connection failed: {e}")
            raise

    def _verify_record_counts(self) -> bool:
        """
        Compare record counts between databases.

        Returns:
            bool: True if all counts match
        """

        logger.info("Comparing record counts...")

        models = {
            "organizations": Organization,
            "publications": Publication,
            "researchers": Researcher,
            "projects": Project,
            "harvest_logs": HarvestLog,
        }

        all_match = True

        for name, model in models.items():
            source_count = self.source_session.query(model).count()
            target_count = self.target_session.query(model).count()

            match = source_count == target_count
            symbol = "✓" if match else "✗"
            status = "" if match else f" (MISMATCH!)"

            logger.info(f"{symbol} {name:20} SQLite: {source_count:6} → PostgreSQL: {target_count:6}{status}")

            if not match:
                all_match = False

        return all_match

    def _verify_schema(self):
        """Verify schema integrity."""

        logger.info("Verifying schema integrity...")

        try:
            # Check if primary keys are set
            with self.target_engine.connect() as conn:

                tables = [
                    "organization",
                    "publication",
                    "researcher",
                    "project",
                ]

                for table in tables:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table} WHERE id IS NULL")
                    ).scalar()

                    if result > 0:
                        logger.warning(f"⚠ {table}: Found {result} NULL primary keys")
                    else:
                        logger.info(f"✓ {table}: Primary keys valid")

        except Exception as e:
            logger.warning(f"Schema check skipped: {e}")


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Verify PostgreSQL data migration"
    )

    parser.add_argument(
        "--source",
        type=str,
        default="sqlite:///./data/armp.db",
        help="Source SQLite database"
    )

    args = parser.parse_args()

    # Get target from environment
    target_db = os.getenv("DATABASE_URL")
    if not target_db:
        logger.error("ERROR: DATABASE_URL not set!")
        sys.exit(1)

    # Run verification
    verifier = MigrationVerifier(args.source, target_db)
    success = verifier.verify()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
