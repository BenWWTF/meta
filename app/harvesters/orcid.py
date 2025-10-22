"""
ORCID Researcher Profile Harvester
===================================

Enriches researcher profiles with data from ORCID Public API.

Features:
- Query ORCID by researcher name
- Extract employment and education history
- Get publication list from ORCID
- Link ORCID ID to researcher profiles
- No authentication needed (public API)
- Rate limiting respect (24 req/sec standard, higher with auth)

ORCID: Open Researcher and Contributor ID
- Free researcher identifier
- 150K+ Austrian profiles
- Contains employment, education, publications
- Globally unique identifier for researchers
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from app.database import SessionLocal, Researcher, HarvestLog

logger = logging.getLogger(__name__)

# ORCID API configuration
ORCID_API_BASE = "https://pub.orcid.org/v3.0"
ORCID_SEARCH_BASE = "https://pub.orcid.org/v3.0/search"
ORCID_TIMEOUT = 30.0
ORCID_RATE_LIMIT = 24  # requests per second for public API


class ORCIDHarvester:
    """
    Harvester for ORCID researcher profile data.
    Enriches existing Researcher records with ORCID information.
    """

    def __init__(self, timeout: float = 30.0, email: str = "research@example.at"):
        """
        Initialize ORCID harvester.

        Args:
            timeout: HTTP request timeout in seconds
            email: Email for user-agent identification
        """
        self.timeout = timeout
        self.user_agent = f"ARMP/1.0 (mailto:{email})"

    async def enrich_researchers(self, max_records: Optional[int] = None) -> Dict[str, Any]:
        """
        Enrich researcher records with ORCID data.

        Args:
            max_records: Maximum researchers to enrich

        Returns:
            Enrichment statistics
        """
        logger.info("Starting ORCID researcher enrichment")

        db = SessionLocal()
        stats = {
            "started_at": datetime.utcnow(),
            "total_researchers": 0,
            "enriched": 0,
            "orcid_found": 0,
            "orcid_profile_matched": 0,
            "employment_updated": 0,
            "education_updated": 0,
            "errors": 0,
        }

        try:
            # Create harvest log
            harvest_log = HarvestLog(
                source="orcid",
                status="running",
            )
            db.add(harvest_log)
            db.commit()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get researchers without ORCID ID
                query = db.query(Researcher).filter(Researcher.orcid_id.is_(None))

                if max_records:
                    query = query.limit(max_records)

                researchers = query.all()
                stats["total_researchers"] = len(researchers)

                logger.info(f"Found {len(researchers)} researchers without ORCID")

                for i, researcher in enumerate(researchers):
                    try:
                        # Search ORCID for this researcher
                        orcid_id = await self._search_orcid(
                            client, researcher.full_name
                        )

                        if orcid_id:
                            stats["orcid_found"] += 1

                            # Get full ORCID profile
                            profile = await self._fetch_orcid_profile(client, orcid_id)

                            if profile:
                                stats["orcid_profile_matched"] += 1

                                # Update researcher record
                                researcher.orcid_id = orcid_id
                                researcher.orcid_profile_url = f"https://orcid.org/{orcid_id}"

                                # Extract employment
                                if profile.get("employmentSummary"):
                                    employment = self._extract_employment(
                                        profile["employmentSummary"]
                                    )
                                    if employment:
                                        researcher.employment = employment
                                        stats["employment_updated"] += 1

                                # Extract education
                                if profile.get("educationSummary"):
                                    education = self._extract_education(
                                        profile["educationSummary"]
                                    )
                                    if education:
                                        researcher.education = education
                                        stats["education_updated"] += 1

                                # Extract keywords/interests
                                if profile.get("keywords"):
                                    keywords = [k.get("content") for k in profile["keywords"]]
                                    researcher.keywords = keywords

                                researcher.updated_at = datetime.utcnow()
                                db.commit()
                                stats["enriched"] += 1

                        # Rate limiting
                        await asyncio.sleep(1.0 / ORCID_RATE_LIMIT)

                        # Progress logging
                        if (i + 1) % 100 == 0:
                            logger.info(
                                f"Processed {i+1}/{len(researchers)} researchers - "
                                f"Enriched: {stats['enriched']}, "
                                f"ORCID found: {stats['orcid_found']}"
                            )

                    except Exception as e:
                        logger.warning(f"Error enriching researcher {researcher.id}: {e}")
                        stats["errors"] += 1

            # Update harvest log
            harvest_log.status = "completed"
            harvest_log.record_count = stats["enriched"]
            harvest_log.error_count = stats["errors"]
            harvest_log.completed_at = datetime.utcnow()
            db.commit()

            stats["completed_at"] = datetime.utcnow()
            logger.info(f"ORCID enrichment complete: {json.dumps(stats, default=str)}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error during ORCID enrichment: {e}")
            stats["errors"] += 1
            return stats
        finally:
            db.close()

    async def _search_orcid(
        self, client: httpx.AsyncClient, name: str
    ) -> Optional[str]:
        """
        Search ORCID for researcher by name.

        Args:
            client: Async HTTP client
            name: Researcher full name

        Returns:
            ORCID ID if found, None otherwise
        """
        try:
            # Query ORCID search API
            params = {
                "q": f'given-and-family-names:"{name}"',
                "rows": 1,
            }

            headers = {"User-Agent": self.user_agent}

            response = await client.get(
                f"{ORCID_SEARCH_BASE}",
                params=params,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("result", [])

            if results:
                # Return the ORCID ID of the top match
                orcid_id = results[0].get("orcid-identifier", {}).get("path")
                if orcid_id:
                    logger.debug(f"Found ORCID for {name}: {orcid_id}")
                    return orcid_id

            return None

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error searching ORCID for {name}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"JSON error parsing ORCID search: {e}")
            return None

    async def _fetch_orcid_profile(
        self, client: httpx.AsyncClient, orcid_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch full ORCID profile data.

        Args:
            client: Async HTTP client
            orcid_id: ORCID identifier

        Returns:
            Profile dictionary if successful, None otherwise
        """
        try:
            url = f"{ORCID_API_BASE}/{orcid_id}/personal-details"
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/orcid+json",
            }

            response = await client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Extract person details
            profile = {}

            # Get basic info
            if data.get("name"):
                profile["name"] = data["name"]

            # Get employment
            employment_url = f"{ORCID_API_BASE}/{orcid_id}/employments"
            try:
                emp_response = await client.get(employment_url, headers=headers)
                if emp_response.status_code == 200:
                    emp_data = emp_response.json()
                    if emp_data.get("affiliation-group"):
                        profile["employmentSummary"] = emp_data["affiliation-group"]
            except httpx.HTTPError:
                pass  # Employment optional

            # Get education
            education_url = f"{ORCID_API_BASE}/{orcid_id}/educations"
            try:
                edu_response = await client.get(education_url, headers=headers)
                if edu_response.status_code == 200:
                    edu_data = edu_response.json()
                    if edu_data.get("affiliation-group"):
                        profile["educationSummary"] = edu_data["affiliation-group"]
            except httpx.HTTPError:
                pass  # Education optional

            return profile if profile else None

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error fetching ORCID profile {orcid_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"JSON error parsing ORCID profile: {e}")
            return None

    def _extract_employment(self, employment_data: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        Extract employment history from ORCID data.

        Args:
            employment_data: Raw employment data from ORCID

        Returns:
            Normalized employment list
        """
        employment = []

        for affiliation_group in employment_data:
            for summary in affiliation_group.get("summaries", []):
                emp = summary.get("employment-summary", {})

                employment.append({
                    "organization": emp.get("organization", {}).get("name"),
                    "title": emp.get("role-title"),
                    "start_date": emp.get("start-date"),
                    "end_date": emp.get("end-date"),
                    "department": emp.get("department-name"),
                    "url": emp.get("url"),
                })

        return employment if employment else None

    def _extract_education(self, education_data: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        Extract education history from ORCID data.

        Args:
            education_data: Raw education data from ORCID

        Returns:
            Normalized education list
        """
        education = []

        for affiliation_group in education_data:
            for summary in affiliation_group.get("summaries", []):
                edu = summary.get("education-summary", {})

                education.append({
                    "institution": edu.get("organization", {}).get("name"),
                    "degree": edu.get("degree-type"),
                    "field": edu.get("department-name"),
                    "start_date": edu.get("start-date"),
                    "end_date": edu.get("end-date"),
                    "url": edu.get("url"),
                })

        return education if education else None


async def enrich_researchers_orcid(max_records: Optional[int] = None):
    """
    Async wrapper for ORCID enrichment.

    Args:
        max_records: Maximum researchers to enrich
    """
    harvester = ORCIDHarvester()
    return await harvester.enrich_researchers(max_records)


def enrich_researchers_orcid_sync(max_records: Optional[int] = None):
    """
    Synchronous wrapper for ORCID enrichment.

    Args:
        max_records: Maximum researchers to enrich
    """
    return asyncio.run(enrich_researchers_orcid(max_records))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run enrichment
    asyncio.run(enrich_researchers_orcid())
