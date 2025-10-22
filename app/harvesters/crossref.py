"""
Crossref API Harvester
======================
Harvests scholarly publication metadata from Crossref.

Crossref is the official DOI registration agency and provides access to
150+ million publication records from publishers worldwide.

Features:
- Query by author affiliation (Austrian institutions)
- Bulk harvesting with cursor pagination
- Deduplication against existing OpenAIRE data
- Metadata enrichment (authors, funding, references)
- Rate limiting respect (50 requests/second polite pool)
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from app.database import SessionLocal, Publication, Organization, HarvestLog

logger = logging.getLogger(__name__)

# Crossref API configuration
CROSSREF_API_BASE = "https://api.crossref.org/v1"
CROSSREF_TIMEOUT = 30.0
CROSSREF_PAGE_SIZE = 1000

# Austrian institution ROR identifiers for Crossref queries
AUSTRIAN_RORS = [
    "03prydq77",   # University of Vienna
    "05qghxh33",   # TU Wien
    "03ak46v85",   # University of Innsbruck
    "035xkbk20",   # University of Graz
    "00rbhpj83",   # JKU Linz
    "03ktj6r74",   # Medical University of Vienna
    "0534sfd39",   # TU Graz
    "02kgz0p91",   # University of Salzburg
    "0285gxx56",   # Medical University of Graz
    "04rbhpj83",   # Medical University of Innsbruck
    "00h7cqc46",   # BOKU Vienna
    "013tf3c58",   # WU Vienna
    "03kfx5e42",   # University of Klagenfurt
    "04r3pxg27",   # Montanuniversität Leoben
    "03anc3s24",   # Austrian Academy of Sciences
]


class CrossrefHarvester:
    """
    Harvester for Crossref publication metadata.
    Enriches existing OpenAIRE data with Crossref publications.
    """

    def __init__(self, mailto: str = "research@example.at", timeout: float = 30.0):
        """
        Initialize harvester.

        Args:
            mailto: Email for polite pool access
            timeout: HTTP request timeout in seconds
        """
        self.mailto = mailto
        self.timeout = timeout
        self.user_agent = f"ARMP/1.0 (mailto:{mailto})"

    async def harvest_all(self, max_records_per_org: Optional[int] = None) -> Dict[str, Any]:
        """
        Harvest publications for all Austrian organizations.

        Args:
            max_records_per_org: Maximum records per organization

        Returns:
            Harvest statistics
        """
        logger.info("Starting Crossref harvest for Austrian institutions")

        db = SessionLocal()
        all_stats = {
            "started_at": datetime.utcnow(),
            "organizations": {},
            "total_fetched": 0,
            "total_stored": 0,
            "total_duplicates": 0,
            "total_errors": 0,
        }

        try:
            # Get all organizations
            organizations = db.query(Organization).filter(
                Organization.id.in_(AUSTRIAN_RORS)
            ).all()

            logger.info(f"Found {len(organizations)} organizations to harvest")

            for org in organizations:
                try:
                    logger.info(f"Harvesting Crossref for {org.name}")
                    stats = await self._harvest_organization(
                        db, org.id, org.name, max_records_per_org
                    )
                    all_stats["organizations"][org.name] = stats

                    # Accumulate totals
                    all_stats["total_fetched"] += stats.get("total_fetched", 0)
                    all_stats["total_stored"] += stats.get("total_stored", 0)
                    all_stats["total_duplicates"] += stats.get("duplicates", 0)
                    all_stats["total_errors"] += stats.get("errors", 0)

                except Exception as e:
                    logger.error(f"Error harvesting {org.name}: {e}", exc_info=True)
                    all_stats["organizations"][org.name] = {
                        "error": str(e),
                        "status": "failed",
                        "total_fetched": 0,
                        "total_stored": 0,
                        "duplicates": 0,
                        "errors": 1,
                    }

                # Rate limiting
                await asyncio.sleep(1.0)

            all_stats["completed_at"] = datetime.utcnow()

            logger.info(f"Crossref harvest complete: {json.dumps(all_stats, default=str)}")

            return all_stats

        finally:
            db.close()

    async def _harvest_organization(
        self, db, org_id: str, org_name: str, max_records: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Harvest Crossref publications for a specific organization.

        Args:
            db: Database session
            org_id: Organization ROR ID
            org_name: Organization name for display
            max_records: Maximum records to fetch

        Returns:
            Harvest statistics
        """

        stats = {
            "organization": org_name,
            "ror_id": org_id,
            "total_fetched": 0,
            "total_stored": 0,
            "duplicates": 0,
            "errors": 0,
            "started_at": datetime.utcnow(),
        }

        try:
            # Create harvest log
            harvest_log = HarvestLog(
                source="crossref",
                organization_id=org_id,
                status="running",
            )
            db.add(harvest_log)
            db.commit()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                offset = 0

                while True:
                    # Check record limit
                    if max_records and offset >= max_records:
                        break

                    # Query Crossref
                    try:
                        publications = await self._query_crossref(
                            client, org_name, offset, CROSSREF_PAGE_SIZE
                        )

                        if not publications:
                            logger.info(f"No more publications for {org_name}")
                            break

                        stats["total_fetched"] += len(publications)

                        # Store publications
                        for pub_data in publications:
                            try:
                                stored = await self._store_publication(db, org_id, pub_data)
                                if stored:
                                    stats["total_stored"] += 1
                                else:
                                    stats["duplicates"] += 1

                            except Exception as e:
                                logger.warning(f"Error storing publication: {e}")
                                stats["errors"] += 1

                        logger.info(
                            f"{org_name}: Fetched {stats['total_fetched']}, "
                            f"Stored {stats['total_stored']}, "
                            f"Duplicates {stats['duplicates']}"
                        )

                        offset += CROSSREF_PAGE_SIZE

                        # Rate limiting (Crossref: 50 req/sec in polite pool)
                        await asyncio.sleep(0.02)

                    except Exception as e:
                        logger.error(f"Error querying Crossref: {e}")
                        stats["errors"] += 1
                        break

            # Update harvest log
            harvest_log.status = "completed"
            harvest_log.record_count = stats["total_stored"]
            harvest_log.error_count = stats["errors"]
            harvest_log.completed_at = datetime.utcnow()
            db.commit()

            stats["completed_at"] = datetime.utcnow()
            return stats

        except Exception as e:
            logger.error(f"Fatal error harvesting {org_name}: {e}")
            stats["errors"] += 1
            return stats

    async def _query_crossref(
        self, client: httpx.AsyncClient, org_name: str, offset: int, limit: int
    ) -> List[Dict[str, Any]]:
        """
        Query Crossref API for publications.

        Args:
            client: Async HTTP client
            org_name: Organization name to search
            offset: Pagination offset
            limit: Number of records to fetch

        Returns:
            List of publication dictionaries
        """

        url = f"{CROSSREF_API_BASE}/works"

        # Query parameters
        params = {
            "query": org_name,
            "rows": limit,
            "offset": offset,
            "sort": "published",
            "order": "desc",
            "mailto": self.mailto,
        }

        headers = {
            "User-Agent": self.user_agent
        }

        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Extract items
            items = data.get("message", {}).get("items", [])

            # Transform to internal format
            publications = []
            for item in items:
                try:
                    pub = self._normalize_publication(item)
                    publications.append(pub)
                except Exception as e:
                    logger.warning(f"Error normalizing publication: {e}")

            return publications

        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying Crossref: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return []

    def _normalize_publication(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Crossref publication data to internal schema.

        Args:
            item: Crossref item dictionary

        Returns:
            Normalized publication dictionary
        """

        # Basic fields
        title = item.get("title", ["Untitled"])[0] if item.get("title") else "Untitled"
        doi = item.get("DOI")
        abstract = item.get("abstract")

        # Authors
        authors = []
        for author in item.get("author", []):
            authors.append({
                "name": f"{author.get('given', '')} {author.get('family', '')}".strip(),
                "orcid": author.get("ORCID"),
                "affiliation": None,
            })

        # Publication date
        pub_date = None
        pub_year = None

        if item.get("published-online"):
            date_parts = item["published-online"].get("date-parts", [[]])[0]
            if date_parts:
                pub_year = date_parts[0]
                try:
                    pub_date = datetime(pub_year, date_parts[1] if len(date_parts) > 1 else 1, 1)
                except:
                    pub_date = None

        if not pub_year and item.get("published-print"):
            date_parts = item["published-print"].get("date-parts", [[]])[0]
            if date_parts:
                pub_year = date_parts[0]

        # Publication details
        journal = None
        if item.get("container-title"):
            journal = item["container-title"][0]

        pub_type = item.get("type", "journal-article")

        # Funding information
        funders = []
        for funder in item.get("funder", []):
            funders.append({
                "name": funder.get("name"),
                "id": funder.get("DOI"),
                "project_id": None,
            })

        # Open Access status (based on license)
        open_access = False
        license_val = None
        for lic in item.get("license", []):
            license_val = lic.get("URL")
            if "open" in license_val.lower() or "cc-by" in license_val.lower():
                open_access = True

        return {
            "id": doi if doi else f"crossref:{item.get('title', ['untitled'])[0][:50]}",
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "publication_date": pub_date,
            "publication_year": pub_year,
            "publication_type": pub_type,
            "authors": authors,
            "journal": journal,
            "publisher": item.get("publisher"),
            "issn": item.get("ISSN", [None])[0] if item.get("ISSN") else None,
            "open_access": open_access,
            "license": license_val,
            "source_system": "crossref",
            "crossref_id": doi,
            "funders": funders,
            "metadata": item,
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

        # Create new publication
        pub = Publication(
            id=pub_data.get("id"),
            doi=pub_data.get("doi"),
            title=pub_data.get("title"),
            abstract=pub_data.get("abstract"),
            publication_date=pub_data.get("publication_date"),
            publication_year=pub_data.get("publication_year"),
            publication_type=pub_data.get("publication_type"),
            authors=pub_data.get("authors"),
            journal=pub_data.get("journal"),
            publisher=pub_data.get("publisher"),
            issn=pub_data.get("issn"),
            open_access=pub_data.get("open_access"),
            license=pub_data.get("license"),
            source_system="crossref",
            crossref_id=pub_data.get("crossref_id"),
            organization_id=org_id,
            harvested_at=datetime.utcnow(),
        )

        db.add(pub)
        db.commit()

        return True


async def harvest_crossref_async(max_records: Optional[int] = None):
    """
    Async wrapper for Crossref harvesting.

    Args:
        max_records: Maximum records per organization
    """
    harvester = CrossrefHarvester()
    return await harvester.harvest_all(max_records)


def harvest_crossref(max_records: Optional[int] = None):
    """
    Synchronous wrapper for Crossref harvesting.

    Args:
        max_records: Maximum records per organization (None = unlimited)
    """
    return asyncio.run(harvest_crossref_async(max_records))


if __name__ == "__main__":
    """Run harvest directly."""
    import sys

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
    asyncio.run(harvest_crossref_async(max_records))
