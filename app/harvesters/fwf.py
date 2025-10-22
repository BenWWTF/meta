"""
FWF Project Data Harvester
===========================

Harvests funded research projects from FWF (Austrian Science Fund).

Features:
- Query FWF Research Radar API
- Extract project metadata (title, abstract, funding, duration)
- Link projects to publications via DOI/title matching
- Calculate funding efficiency metrics
- Track funding by research area

FWF: Fonds zur Förderung der Wissenschaftlichen Forschung
- Austrian national science funding body
- Funds ~4000 projects across all disciplines
- Research Radar API: Open access to project data
- ~€200M annual funding
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from app.database import SessionLocal, Project, Publication, Organization, HarvestLog

logger = logging.getLogger(__name__)

# FWF API configuration
FWF_API_BASE = "https://elise.fwf.ac.at/api"
FWF_TIMEOUT = 30.0
FWF_PAGE_SIZE = 100


class FWFHarvester:
    """
    Harvester for FWF (Austrian Science Fund) project data.
    Integrates funding information with publications for impact assessment.
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize FWF harvester.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.user_agent = "ARMP/1.0 (FWF Project Harvester)"

    async def harvest_all(self, max_records: Optional[int] = None) -> Dict[str, Any]:
        """
        Harvest all FWF projects.

        Args:
            max_records: Maximum projects to harvest

        Returns:
            Harvest statistics
        """
        logger.info("Starting FWF project harvest")

        db = SessionLocal()
        stats = {
            "started_at": datetime.utcnow(),
            "total_fetched": 0,
            "total_stored": 0,
            "duplicates": 0,
            "linked_to_publications": 0,
            "errors": 0,
        }

        try:
            # Create harvest log
            harvest_log = HarvestLog(
                source="fwf",
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

                    # Query FWF API
                    try:
                        projects = await self._query_fwf(
                            client, offset, FWF_PAGE_SIZE
                        )

                        if not projects:
                            logger.info("No more projects from FWF")
                            break

                        stats["total_fetched"] += len(projects)

                        # Store projects
                        for proj_data in projects:
                            try:
                                stored = await self._store_project(db, proj_data)
                                if stored:
                                    stats["total_stored"] += 1

                                    # Try to link to publications
                                    linked = self._link_to_publications(
                                        db, proj_data
                                    )
                                    stats["linked_to_publications"] += linked
                                else:
                                    stats["duplicates"] += 1

                            except Exception as e:
                                logger.warning(f"Error storing project: {e}")
                                stats["errors"] += 1

                        logger.info(
                            f"FWF: Fetched {stats['total_fetched']}, "
                            f"Stored {stats['total_stored']}"
                        )

                        offset += FWF_PAGE_SIZE

                        # Rate limiting
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(f"Error querying FWF: {e}")
                        stats["errors"] += 1
                        break

            # Update harvest log
            harvest_log.status = "completed"
            harvest_log.record_count = stats["total_stored"]
            harvest_log.error_count = stats["errors"]
            harvest_log.completed_at = datetime.utcnow()
            db.commit()

            stats["completed_at"] = datetime.utcnow()
            logger.info(f"FWF harvest complete: {json.dumps(stats, default=str)}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error during FWF harvest: {e}")
            stats["errors"] += 1
            return stats
        finally:
            db.close()

    async def _query_fwf(
        self, client: httpx.AsyncClient, offset: int, limit: int
    ) -> List[Dict[str, Any]]:
        """
        Query FWF Research Radar API for projects.

        Args:
            client: Async HTTP client
            offset: Pagination offset
            limit: Number of records to fetch

        Returns:
            List of project dictionaries
        """

        try:
            # FWF Research Radar API endpoint
            url = f"{FWF_API_BASE}/projects"

            params = {
                "offset": offset,
                "limit": limit,
            }

            headers = {"User-Agent": self.user_agent}

            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Extract projects
            projects = data.get("data", [])

            # Transform to internal format
            result = []
            for item in projects:
                try:
                    proj = self._normalize_project(item)
                    result.append(proj)
                except Exception as e:
                    logger.warning(f"Error normalizing project: {e}")

            return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error querying FWF: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return []

    def _normalize_project(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize FWF project data to internal schema.

        Args:
            item: FWF project item dictionary

        Returns:
            Normalized project dictionary
        """

        # Extract fields
        project_id = item.get("projectNumber")
        title = item.get("titleEnglish") or item.get("titleGerman", "Untitled")
        abstract = item.get("abstractEnglish") or item.get("abstractGerman")

        # Funding info
        funding_amount = item.get("fundingAmount")
        currency = item.get("currency", "EUR")

        # Project timeline
        start_date = item.get("startDate")
        end_date = item.get("endDate")

        # Investigators
        principal_investigator = None
        investigators = []

        if item.get("pi"):
            pi_data = item["pi"]
            principal_investigator = pi_data.get("name")
            investigators.append({
                "name": pi_data.get("name"),
                "orcid": pi_data.get("orcid"),
                "role": "Principal Investigator",
            })

        # Classification
        classification = {}
        if item.get("specialResearchProgram"):
            classification["srp"] = item["specialResearchProgram"]
        if item.get("researchArea"):
            classification["area"] = item["researchArea"]

        keywords = item.get("keywords", [])
        if isinstance(keywords, str):
            keywords = keywords.split(";")

        return {
            "id": project_id or f"fwf:{title[:50]}",
            "grant_number": project_id,
            "title": title,
            "abstract": abstract,
            "funder": "FWF",
            "funder_id": "fwf",
            "funding_amount": funding_amount,
            "currency": currency,
            "start_date": start_date,
            "end_date": end_date,
            "principal_investigator": principal_investigator,
            "investigators": investigators,
            "classification": classification if classification else None,
            "keywords": keywords if keywords else None,
            "source_system": "fwf",
            "external_url": f"https://www.fwf.ac.at/en/research-radar/projects/{project_id}",
            "metadata": item,
        }

    async def _store_project(self, db, proj_data: Dict[str, Any]) -> bool:
        """
        Store normalized project in database.

        Args:
            db: Database session
            proj_data: Normalized project data

        Returns:
            True if stored, False if duplicate
        """

        # Check for duplicates by grant number
        if proj_data.get("grant_number"):
            existing = db.query(Project).filter_by(
                grant_number=proj_data["grant_number"]
            ).first()
            if existing:
                return False

        # Create new project
        project = Project(
            id=proj_data.get("id"),
            grant_number=proj_data.get("grant_number"),
            title=proj_data.get("title"),
            abstract=proj_data.get("abstract"),
            funder="FWF",
            funder_id="fwf",
            funding_amount=proj_data.get("funding_amount"),
            currency=proj_data.get("currency", "EUR"),
            start_date=proj_data.get("start_date"),
            end_date=proj_data.get("end_date"),
            principal_investigator=proj_data.get("principal_investigator"),
            investigators=proj_data.get("investigators"),
            classification=proj_data.get("classification"),
            keywords=proj_data.get("keywords"),
            source_system="fwf",
            external_url=proj_data.get("external_url"),
        )

        db.add(project)
        db.commit()

        return True

    def _link_to_publications(self, db, proj_data: Dict[str, Any]) -> int:
        """
        Link project to publications by title and funder keywords matching.

        Args:
            db: Database session
            proj_data: Project data

        Returns:
            Number of publications linked
        """

        linked = 0
        project_id = proj_data.get("id")
        title_keywords = proj_data.get("title", "").lower().split()

        # Find publications with matching keywords
        # This is a simple heuristic - in production would use more sophisticated matching
        for keyword in title_keywords:
            if len(keyword) > 4:  # Skip short words
                publications = db.query(Publication).filter(
                    Publication.title.ilike(f"%{keyword}%")
                ).limit(5).all()  # Limit matches to avoid false positives

                for pub in publications:
                    # Check if already linked
                    existing = db.query(Project).filter(
                        Project.id == project_id
                    ).first()
                    if existing and pub in existing.publications:
                        continue

                    # Link project to publication
                    existing.publications.append(pub)
                    linked += 1

        db.commit()
        return linked


async def harvest_fwf(max_records: Optional[int] = None):
    """
    Async wrapper for FWF harvesting.

    Args:
        max_records: Maximum projects to harvest
    """
    harvester = FWFHarvester()
    return await harvester.harvest_all(max_records)


def harvest_fwf_sync(max_records: Optional[int] = None):
    """
    Synchronous wrapper for FWF harvesting.

    Args:
        max_records: Maximum projects to harvest
    """
    return asyncio.run(harvest_fwf(max_records))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run harvest
    asyncio.run(harvest_fwf())
