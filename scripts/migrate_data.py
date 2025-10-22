#!/usr/bin/env python3
"""
PostgreSQL Data Migration Script
=================================

Migrates data from SQLite to PostgreSQL.
Exports all records from source SQLite database and imports into target PostgreSQL.

Usage:
    python scripts/migrate_data.py [--source path/to/armp.db]

Environment:
    DATABASE_URL: Target PostgreSQL connection string
    (e.g., postgresql://user:password@localhost:5432/armp)

Prerequisites:
    - PostgreSQL database schema created (run migrate_schema.py first)
    - Source SQLite database exists (data/armp.db by default)
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
from app.database import (
    Base, Organization, Publication, Researcher, Project,
    HarvestLog, publication_author, project_publication
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/migration_data.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


class DataMigrator:
    """Handles data migration from SQLite to PostgreSQL."""

    def __init__(self, source_db: str, target_db: str):
        """
        Initialize migrator with source and target databases.

        Args:
            source_db: SQLite connection string (e.g., sqlite:///./data/armp.db)
            target_db: PostgreSQL connection string
        """
        self.source_db_url = source_db
        self.target_db_url = target_db

        # Create engines
        self.source_engine = create_engine(source_db)
        self.target_engine = create_engine(target_db, echo=False)

        # Create sessions
        SourceSession = sessionmaker(bind=self.source_engine)
        TargetSession = sessionmaker(bind=self.target_engine)

        self.source_session = SourceSession()
        self.target_session = TargetSession()

        self.stats = {
            "organizations": 0,
            "publications": 0,
            "researchers": 0,
            "projects": 0,
            "harvest_logs": 0,
            "pub_authors": 0,
            "proj_pubs": 0,
        }

    def migrate(self) -> bool:
        """
        Execute full data migration.

        Returns:
            bool: True if migration successful, False otherwise
        """

        try:
            logger.info("=" * 80)
            logger.info("PostgreSQL Data Migration Starting")
            logger.info("=" * 80)

            # Count source records
            self._count_source_records()

            # Migrate each table
            logger.info("Starting table migrations...")
            self._migrate_organizations()
            self._migrate_publications()
            self._migrate_researchers()
            self._migrate_projects()
            self._migrate_harvest_logs()
            self._migrate_associations()

            # Verify migration
            self._verify_migration()

            logger.info("=" * 80)
            logger.info("✓ Data migration complete!")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"Data migration failed: {e}", exc_info=True)
            logger.error("=" * 80)
            self.target_session.rollback()
            return False

        finally:
            self.source_session.close()
            self.target_session.close()

    def _count_source_records(self):
        """Count and log records in source database."""

        logger.info("Source database contains:")

        org_count = self.source_session.query(Organization).count()
        pub_count = self.source_session.query(Publication).count()
        res_count = self.source_session.query(Researcher).count()
        proj_count = self.source_session.query(Project).count()
        log_count = self.source_session.query(HarvestLog).count()

        logger.info(f"  - {org_count} organizations")
        logger.info(f"  - {pub_count} publications")
        logger.info(f"  - {res_count} researchers")
        logger.info(f"  - {proj_count} projects")
        logger.info(f"  - {log_count} harvest logs")

        self.stats["organizations"] = org_count
        self.stats["publications"] = pub_count
        self.stats["researchers"] = res_count
        self.stats["projects"] = proj_count
        self.stats["harvest_logs"] = log_count

    def _migrate_organizations(self):
        """Migrate organizations (no dependencies)."""

        logger.info("Migrating organizations...")

        try:
            organizations = self.source_session.query(Organization).all()

            for org in organizations:
                # Create new organization in target
                org_dict = {c.name: getattr(org, c.name) for c in Organization.__table__.columns}
                new_org = Organization(**org_dict)
                self.target_session.add(new_org)

            self.target_session.commit()
            logger.info(f"✓ Migrated {len(organizations)} organizations")

        except Exception as e:
            logger.error(f"Organization migration failed: {e}")
            self.target_session.rollback()
            raise

    def _migrate_publications(self):
        """Migrate publications (depends on organization)."""

        logger.info("Migrating publications...")

        try:
            publications = self.source_session.query(Publication).all()

            for pub in publications:
                pub_dict = {c.name: getattr(pub, c.name) for c in Publication.__table__.columns}
                new_pub = Publication(**pub_dict)
                self.target_session.add(new_pub)

            self.target_session.commit()
            logger.info(f"✓ Migrated {len(publications)} publications")

        except Exception as e:
            logger.error(f"Publication migration failed: {e}")
            self.target_session.rollback()
            raise

    def _migrate_researchers(self):
        """Migrate researchers."""

        logger.info("Migrating researchers...")

        try:
            researchers = self.source_session.query(Researcher).all()

            for res in researchers:
                res_dict = {c.name: getattr(res, c.name) for c in Researcher.__table__.columns}
                new_res = Researcher(**res_dict)
                self.target_session.add(new_res)

            self.target_session.commit()
            logger.info(f"✓ Migrated {len(researchers)} researchers")

        except Exception as e:
            logger.error(f"Researcher migration failed: {e}")
            self.target_session.rollback()
            raise

    def _migrate_projects(self):
        """Migrate projects."""

        logger.info("Migrating projects...")

        try:
            projects = self.source_session.query(Project).all()

            for proj in projects:
                proj_dict = {c.name: getattr(proj, c.name) for c in Project.__table__.columns}
                new_proj = Project(**proj_dict)
                self.target_session.add(new_proj)

            self.target_session.commit()
            logger.info(f"✓ Migrated {len(projects)} projects")

        except Exception as e:
            logger.error(f"Project migration failed: {e}")
            self.target_session.rollback()
            raise

    def _migrate_harvest_logs(self):
        """Migrate harvest logs."""

        logger.info("Migrating harvest logs...")

        try:
            logs = self.source_session.query(HarvestLog).all()

            for log in logs:
                log_dict = {c.name: getattr(log, c.name) for c in HarvestLog.__table__.columns}
                new_log = HarvestLog(**log_dict)
                self.target_session.add(new_log)

            self.target_session.commit()
            logger.info(f"✓ Migrated {len(logs)} harvest logs")

        except Exception as e:
            logger.error(f"Harvest log migration failed: {e}")
            self.target_session.rollback()
            raise

    def _migrate_associations(self):
        """Migrate association tables (publication_author, project_publication)."""

        logger.info("Migrating relationships...")

        try:
            # Migration requires raw SQL for association tables
            with self.source_engine.connect() as source_conn:
                with self.target_engine.connect() as target_conn:

                    # publication_author
                    try:
                        pub_author_records = source_conn.execute(
                            text("SELECT publication_id, researcher_id FROM publication_author")
                        ).fetchall()

                        for record in pub_author_records:
                            target_conn.execute(
                                publication_author.insert().values(
                                    publication_id=record[0],
                                    researcher_id=record[1]
                                )
                            )

                        target_conn.commit()
                        logger.info(f"✓ Migrated {len(pub_author_records)} publication-author links")
                        self.stats["pub_authors"] = len(pub_author_records)

                    except Exception as e:
                        logger.warning(f"publication_author migration skipped: {e}")

                    # project_publication
                    try:
                        proj_pub_records = source_conn.execute(
                            text("SELECT project_id, publication_id FROM project_publication")
                        ).fetchall()

                        for record in proj_pub_records:
                            target_conn.execute(
                                project_publication.insert().values(
                                    project_id=record[0],
                                    publication_id=record[1]
                                )
                            )

                        target_conn.commit()
                        logger.info(f"✓ Migrated {len(proj_pub_records)} project-publication links")
                        self.stats["proj_pubs"] = len(proj_pub_records)

                    except Exception as e:
                        logger.warning(f"project_publication migration skipped: {e}")

        except Exception as e:
            logger.error(f"Association migration failed: {e}")
            raise

    def _verify_migration(self):
        """Verify migration by comparing record counts."""

        logger.info("Verifying migration...")

        checks = {
            "organizations": Organization,
            "publications": Publication,
            "researchers": Researcher,
            "projects": Project,
        }

        all_match = True

        for name, model in checks.items():
            source_count = self.source_session.query(model).count()
            target_count = self.target_session.query(model).count()

            match = source_count == target_count
            symbol = "✓" if match else "✗"

            logger.info(f"{symbol} {name}: {source_count} → {target_count}")

            if not match:
                all_match = False

        if all_match:
            logger.info("✓ All tables verified!")
        else:
            logger.warning("⚠ Some tables have mismatches!")
            return False

        return True


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate from default SQLite to PostgreSQL
  python migrate_data.py

  # Migrate from specific SQLite file
  python migrate_data.py --source /path/to/database.db
        """
    )

    parser.add_argument(
        "--source",
        type=str,
        default="sqlite:///./data/armp.db",
        help="Source SQLite database URL (default: sqlite:///./data/armp.db)"
    )

    args = parser.parse_args()

    # Get target database URL from environment
    target_db = os.getenv("DATABASE_URL")
    if not target_db:
        logger.error("ERROR: DATABASE_URL environment variable not set!")
        logger.error("Please set DATABASE_URL to PostgreSQL connection string")
        logger.error("Example: postgresql://user:password@localhost:5432/armp")
        sys.exit(1)

    if "sqlite" in target_db:
        logger.error("ERROR: DATABASE_URL points to SQLite, not PostgreSQL!")
        logger.error("Please set DATABASE_URL to a PostgreSQL connection string")
        sys.exit(1)

    # Run migration
    migrator = DataMigrator(args.source, target_db)
    success = migrator.migrate()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
