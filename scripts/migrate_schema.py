#!/usr/bin/env python3
"""
PostgreSQL Schema Migration Script
===================================

Migrates database schema from SQLite to PostgreSQL.
Creates all tables in target PostgreSQL database using SQLAlchemy models.

Usage:
    python scripts/migrate_schema.py

Environment:
    DATABASE_URL: PostgreSQL connection string
    (e.g., postgresql://user:password@localhost:5432/armp)
"""

import sys
import os
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/migration_schema.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


def migrate_schema():
    """
    Create all database tables in PostgreSQL.

    Uses SQLAlchemy Base.metadata.create_all() to generate and execute
    CREATE TABLE statements based on model definitions.

    Returns:
        bool: True if migration successful, False otherwise
    """

    logger.info("=" * 80)
    logger.info("PostgreSQL Schema Migration Starting")
    logger.info("=" * 80)

    # Check database URL
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/armp.db")
    logger.info(f"Target database: {database_url.split('@')[0]}...")

    if "sqlite" in database_url:
        logger.warning("WARNING: DATABASE_URL points to SQLite, not PostgreSQL!")
        logger.warning("Please set DATABASE_URL to PostgreSQL connection string")
        return False

    try:
        # Create all tables
        logger.info("Creating database schema...")
        Base.metadata.create_all(bind=engine)

        # Get table count
        table_count = len(Base.metadata.tables)
        logger.info(f"✓ Schema created successfully ({table_count} tables)")

        # Log created tables
        logger.info("Created tables:")
        for table_name in sorted(Base.metadata.tables.keys()):
            table = Base.metadata.tables[table_name]
            column_count = len(table.columns)
            logger.info(f"  - {table_name} ({column_count} columns)")

        logger.info("=" * 80)
        logger.info("Schema migration complete!")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"Schema migration failed: {e}", exc_info=True)
        logger.error("=" * 80)
        return False


if __name__ == "__main__":
    success = migrate_schema()
    sys.exit(0 if success else 1)
