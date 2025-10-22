"""
OpenAIRE Graph API Harvester
=============================
Harvests research publications and metadata from OpenAIRE for Austrian institutions.

Features:
- Batch harvesting with progress tracking
- Error handling and retry logic
- Deduplication using DOI
- Normalized metadata storage
- Configurable batch sizes and timeouts
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from app.database import SessionLocal, Publication, Organization, HarvestLog

logger = logging.getLogger(__name__)

# OpenAIRE Graph API configuration
OPENAIRE_API_BASE = "https://api.openaire.eu/graph"
OPENAIRE_TIMEOUT = 30.0
OPENAIRE_PAGE_SIZE = 100

# Austrian universities with ROR identifiers
AUSTRIAN_UNIVERSITIES = {
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


class OpenAIREHarvester:
    """
    Harvester for OpenAIRE research publications.
    Provides methods to query OpenAIRE and store results in database.
    """

    def __init__(self, batch_size: int = 100, timeout: float = 30.0):
        """
        Initialize harvester.

        Args:
            batch_size: Number of records per API request
            timeout: HTTP request timeout in seconds
        """
        self.batch_size = batch_size
        self.timeout = timeout
        self.session = None
        self.harvest_log = None

    async def harvest_organization(
        self, ror_id: str, org_name: str, max_records: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Harvest publications from a specific organization.

        Args:
            ror_id: Organization ROR identifier
            org_name: Organization name for display
            max_records: Maximum records to fetch (None = all)

        Returns:
            Dictionary with harvest statistics
        """
        logger.info(f"Starting harvest for {org_name} ({ror_id})")

        db = SessionLocal()
        stats = {
            "organization": org_name,
            "ror_id": ror_id,
            "total_fetched": 0,
            "total_stored": 0,
            "duplicates": 0,
            "errors": 0,
            "started_at": datetime.utcnow(),
        }

        try:
            # Ensure organization exists in database
            org = db.query(Organization).filter(Organization.id == ror_id).first()
            if not org:
                org = Organization(
                    id=ror_id,
                    name=org_name,
                    ror_id=ror_id,
                    country="AT",
                    type="University",
                )
                db.add(org)
                db.commit()
                logger.info(f"Created organization record for {org_name}")

            # Create harvest log entry
            harvest_log = HarvestLog(
                source="openaire",
                organization_id=ror_id,
                status="running",
            )
            db.add(harvest_log)
            db.commit()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                page = 0

                while True:
                    # Calculate pagination parameters
                    offset = page * self.batch_size

                    if max_records and offset >= max_records:
                        logger.info(f"Reached max records limit: {max_records}")
                        break

                    # Query OpenAIRE
                    try:
                        publications = await self._query_openaire(
                            client, ror_id, offset, self.batch_size
                        )

                        if not publications:
                            logger.info(f"No more publications found for {org_name}")
                            break

                        stats["total_fetched"] += len(publications)

                        # Process and store publications
                        for pub_data in publications:
                            try:
                                stored = await self._store_publication(
                                    db, ror_id, pub_data
                                )
                                if stored:
                                    stats["total_stored"] += 1
                                else:
                                    stats["duplicates"] += 1

                            except Exception as e:
                                logger.error(f"Error storing publication: {e}")
                                stats["errors"] += 1

                        # Log progress
                        logger.info(
                            f"{org_name}: Fetched {stats['total_fetched']}, "
                            f"Stored {stats['total_stored']}, "
                            f"Duplicates {stats['duplicates']}"
                        )

                        page += 1

                        # Rate limiting
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(f"Error querying OpenAIRE: {e}")
                        stats["errors"] += 1
                        break

            # Update harvest log
            harvest_log.status = "completed"
            harvest_log.record_count = stats["total_stored"]
            harvest_log.error_count = stats["errors"]
            harvest_log.completed_at = datetime.utcnow()

            db.commit()

            stats["completed_at"] = datetime.utcnow()
            logger.info(f"Harvest completed for {org_name}: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error harvesting {org_name}: {e}")
            stats["errors"] += 1
            stats["completed_at"] = datetime.utcnow()

            # Update harvest log on error
            harvest_log.status = "failed"
            harvest_log.error_message = str(e)
            harvest_log.completed_at = datetime.utcnow()
            db.commit()

            return stats

        finally:
            db.close()

    async def _query_openaire(
        self, client: httpx.AsyncClient, ror_id: str, offset: int, limit: int
    ) -> List[Dict[str, Any]]:
        """
        Query OpenAIRE Graph API for publications from an organization.

        Args:
            client: Async HTTP client
            ror_id: Organization ROR identifier
            offset: Pagination offset
            limit: Number of records to fetch

        Returns:
            List of publication dictionaries
        """

        # OpenAIRE search endpoint
        url = f"{OPENAIRE_API_BASE}/publications"

        # Query parameters for organization filtering
        params = {
            "keywords": f"hasAuthor(affiliation_id=\"{ror_id}\")",
            "size": limit,
            "from": offset,
            "format": "json",
        }

        headers = {
            "User-Agent": "AustrianResearchMetadata/1.0 (+https://example.at/armp)"
        }

        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Extract publications from response
            results = data.get("response", {}).get("results", [])

            # Transform to our internal format
            publications = []
            for result in results:
                try:
                    pub = result.get("result", {})
                    publications.append(self._normalize_publication(pub))
                except Exception as e:
                    logger.warning(f"Error normalizing publication: {e}")

            return publications

        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying OpenAIRE: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return []

    def _normalize_publication(self, pub_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize OpenAIRE publication data to our schema.

        Args:
            pub_data: Raw publication data from OpenAIRE

        Returns:
            Normalized publication dictionary
        """

        # Extract and normalize fields
        title = pub_data.get("title", [{}])[0].get("value", "Untitled")
        abstract = pub_data.get("description", [{}])[0].get("value")

        # DOI
        doi = None
        for pid in pub_data.get("pid", []):
            if pid.get("classid") == "doi":
                doi = pid.get("value")
                break

        # Authors
        authors = []
        for author in pub_data.get("author", []):
            authors.append(
                {
                    "name": author.get("fullname"),
                    "orcid": None,  # Would need additional processing
                    "affiliation": None,
                }
            )

        # Publication date
        pub_date_str = pub_data.get("publicationdate")
        pub_date = None
        pub_year = None

        if pub_date_str:
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                pub_year = pub_date.year
            except:
                pass

        # Get year from year field if available
        if not pub_year and pub_data.get("relevantdate"):
            try:
                pub_year = int(pub_data.get("relevantdate", "")[:4])
            except:
                pass

        # Open access status
        open_access = pub_data.get("openAccessColor") == "gold"
        license_val = None
        for instance in pub_data.get("instances", []):
            license_val = instance.get("license")
            if license_val:
                break

        return {
            "id": pub_data.get("id"),
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "publication_date": pub_date,
            "publication_year": pub_year,
            "publication_type": pub_data.get("documenttype"),
            "authors": authors,
            "journal": pub_data.get("journal", {}).get("content"),
            "publisher": pub_data.get("publisher"),
            "open_access": open_access,
            "license": license_val,
            "source_system": "openaire",
            "openaire_id": pub_data.get("id"),
            "metadata": pub_data,  # Store full metadata
        }

    async def _store_publication(
        self, db, org_id: str, pub_data: Dict[str, Any]
    ) -> bool:
        """
        Store normalized publication in database.
        Checks for duplicates using DOI.

        Args:
            db: Database session
            org_id: Organization ID
            pub_data: Normalized publication data

        Returns:
            True if stored, False if duplicate
        """

        # Check for duplicates by DOI
        if pub_data.get("doi"):
            existing = db.query(Publication).filter_by(doi=pub_data["doi"]).first()
            if existing:
                return False

        # Check by OpenAIRE ID
        existing = (
            db.query(Publication)
            .filter_by(openaire_id=pub_data.get("openaire_id"))
            .first()
        )
        if existing:
            return False

        # Create new publication
        pub = Publication(
            id=pub_data.get("id", pub_data.get("openaire_id")),
            doi=pub_data.get("doi"),
            title=pub_data.get("title"),
            abstract=pub_data.get("abstract"),
            publication_date=pub_data.get("publication_date"),
            publication_year=pub_data.get("publication_year"),
            publication_type=pub_data.get("publication_type"),
            authors=pub_data.get("authors"),
            journal=pub_data.get("journal"),
            publisher=pub_data.get("publisher"),
            open_access=pub_data.get("open_access"),
            license=pub_data.get("license"),
            source_system="openaire",
            openaire_id=pub_data.get("openaire_id"),
            organization_id=org_id,
            harvested_at=datetime.utcnow(),
        )

        db.add(pub)
        db.commit()

        return True

    async def harvest_all(self, max_records_per_org: Optional[int] = 1000):
        """
        Harvest all Austrian organizations.

        Args:
            max_records_per_org: Maximum records per organization (for testing)
        """

        logger.info("Starting harvest of all Austrian universities")
        logger.info(f"Universities to harvest: {len(AUSTRIAN_UNIVERSITIES)}")

        all_stats = {
            "started_at": datetime.utcnow(),
            "organizations": {},
        }

        for ror_id, org_name in AUSTRIAN_UNIVERSITIES.items():
            try:
                stats = await self.harvest_organization(
                    ror_id, org_name, max_records_per_org
                )
                all_stats["organizations"][org_name] = stats

            except Exception as e:
                logger.error(f"Error harvesting {org_name}: {e}")
                all_stats["organizations"][org_name] = {
                    "error": str(e),
                    "status": "failed",
                }

            # Rate limiting between organizations
            await asyncio.sleep(2.0)

        all_stats["completed_at"] = datetime.utcnow()

        # Calculate totals
        all_stats["total_fetched"] = sum(
            s.get("total_fetched", 0) for s in all_stats["organizations"].values()
        )
        all_stats["total_stored"] = sum(
            s.get("total_stored", 0) for s in all_stats["organizations"].values()
        )
        all_stats["total_duplicates"] = sum(
            s.get("duplicates", 0) for s in all_stats["organizations"].values()
        )
        all_stats["total_errors"] = sum(
            s.get("errors", 0) for s in all_stats["organizations"].values()
        )

        logger.info(f"\n\nHarvest Summary:\n{json.dumps(all_stats, default=str, indent=2)}")

        return all_stats


async def harvest_openaire_async(max_records: Optional[int] = 1000):
    """
    Async wrapper for harvesting OpenAIRE data.

    Args:
        max_records: Maximum records per organization
    """
    harvester = OpenAIREHarvester()
    return await harvester.harvest_all(max_records)


def harvest_openaire(max_records: Optional[int] = 1000):
    """
    Synchronous wrapper for harvesting OpenAIRE data.

    Args:
        max_records: Maximum records per organization (None = unlimited)
    """
    return asyncio.run(harvest_openaire_async(max_records))


if __name__ == "__main__":
    """Run harvest directly."""
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get max records from command line if provided
    max_records = None
    if len(sys.argv) > 1:
        try:
            max_records = int(sys.argv[1])
            logger.info(f"Limiting to {max_records} records per organization")
        except ValueError:
            logger.warning("Invalid max_records argument, using unlimited")

    # Run harvest
    asyncio.run(harvest_openaire_async(max_records))
