"""
Researcher Profile Enrichment
=============================

Extract and consolidate researcher profiles from publication author data.
Implements author disambiguation using fuzzy matching and ORCID linking.

Features:
- Extract authors from publications
- Author name disambiguation (deduplication)
- Fuzzy matching for name variations
- Publication count tracking
- Basic H-index calculation (placeholder for advanced metrics)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from fuzzywuzzy import fuzz
from collections import defaultdict
import json

from app.database import SessionLocal, Publication, Researcher, Organization, publication_author

logger = logging.getLogger(__name__)


class ResearcherEnricher:
    """
    Extract and consolidate researcher information from publications.
    Handles author disambiguation and profile enrichment.
    """

    def __init__(self, fuzzy_threshold: int = 90):
        """
        Initialize enricher.

        Args:
            fuzzy_threshold: Minimum fuzzy match score (0-100) for deduplication
        """
        self.fuzzy_threshold = fuzzy_threshold

    def enrich_all(self) -> Dict[str, Any]:
        """
        Enrich researchers from all publications in database.

        Returns:
            Statistics dictionary with enrichment results
        """
        logger.info("Starting researcher enrichment from publications")

        db = SessionLocal()
        stats = {
            "started_at": datetime.utcnow(),
            "researchers_created": 0,
            "researchers_updated": 0,
            "authors_processed": 0,
            "disambiguation_merges": 0,
            "errors": 0,
        }

        try:
            # Get all publications with author data
            publications = db.query(Publication).filter(
                Publication.authors.isnot(None)
            ).all()

            logger.info(f"Processing {len(publications)} publications")

            # Collect all authors with organization hints
            authors_by_org = defaultdict(list)

            for pub in publications:
                try:
                    if not pub.authors or not isinstance(pub.authors, list):
                        continue

                    org_id = pub.organization_id

                    for author_data in pub.authors:
                        if isinstance(author_data, dict):
                            author_name = author_data.get("name", "").strip()
                            orcid = author_data.get("orcid")
                            affiliation = author_data.get("affiliation")

                            if author_name:
                                authors_by_org[org_id].append({
                                    "name": author_name,
                                    "orcid": orcid,
                                    "affiliation": affiliation,
                                    "publication_id": pub.id,
                                })
                                stats["authors_processed"] += 1

                except Exception as e:
                    logger.warning(f"Error processing authors in {pub.id}: {e}")
                    stats["errors"] += 1

            logger.info(f"Collected {stats['authors_processed']} author records")

            # Deduplicate and create researcher profiles per organization
            for org_id, authors in authors_by_org.items():
                try:
                    merged_authors = self._deduplicate_authors(
                        authors, org_id, db
                    )
                    stats["disambiguation_merges"] += len(authors) - len(merged_authors)

                    # Create or update researchers
                    for merged_author in merged_authors:
                        created = self._create_or_update_researcher(
                            db, org_id, merged_author
                        )
                        if created:
                            stats["researchers_created"] += 1
                        else:
                            stats["researchers_updated"] += 1

                except Exception as e:
                    logger.error(
                        f"Error enriching researchers for org {org_id}: {e}"
                    )
                    stats["errors"] += 1

            # Link researchers to publications
            logger.info("Linking researchers to publications...")
            self._link_researchers_to_publications(db, stats)

            db.commit()
            stats["completed_at"] = datetime.utcnow()

            logger.info(f"Researcher enrichment complete: {json.dumps(stats, default=str)}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error during enrichment: {e}")
            stats["errors"] += 1
            return stats
        finally:
            db.close()

    def _deduplicate_authors(
        self, authors: List[Dict[str, Any]], org_id: str, db
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate author names using fuzzy matching.
        Authors with same/similar names are merged.

        Args:
            authors: List of author data dicts
            org_id: Organization ID for context
            db: Database session

        Returns:
            Deduplicated list of author data
        """
        if not authors:
            return []

        # Remove obvious duplicates first (exact name + ORCID match)
        seen = {}
        deduplicated = []

        for author in authors:
            name = author["name"].lower().strip()
            orcid = author["orcid"]

            # ORCID match is definitive
            if orcid:
                if orcid not in seen:
                    seen[orcid] = author
                    deduplicated.append(author)
                else:
                    # Merge additional affiliations
                    if author["affiliation"] and not seen[orcid]["affiliation"]:
                        seen[orcid]["affiliation"] = author["affiliation"]
                continue

            # For non-ORCID authors, check fuzzy match against existing names
            found_match = False
            for existing_author in deduplicated:
                if not existing_author["orcid"]:  # Only match against non-ORCID
                    existing_name = existing_author["name"].lower().strip()
                    match_score = fuzz.token_sort_ratio(name, existing_name)

                    if match_score >= self.fuzzy_threshold:
                        # Merge authors (keep more complete info)
                        if author["affiliation"] and not existing_author["affiliation"]:
                            existing_author["affiliation"] = author["affiliation"]
                        found_match = True
                        break

            if not found_match:
                deduplicated.append(author)

        return deduplicated

    def _create_or_update_researcher(
        self, db, org_id: str, author_data: Dict[str, Any]
    ) -> bool:
        """
        Create or update researcher record.

        Args:
            db: Database session
            org_id: Organization ID
            author_data: Author information dict

        Returns:
            True if created, False if updated
        """
        name = author_data["name"].strip()
        orcid = author_data["orcid"]

        # Try to find existing researcher by ORCID
        if orcid:
            researcher = db.query(Researcher).filter(
                Researcher.orcid_id == orcid
            ).first()
            if researcher:
                # Update existing
                researcher.updated_at = datetime.utcnow()
                return False

        # Try to find by name + org (for non-ORCID researchers)
        researcher = db.query(Researcher).filter(
            Researcher.full_name.ilike(f"%{name}%"),
            Researcher.organization_id == org_id,
        ).first()

        if researcher:
            # Update existing
            if orcid and not researcher.orcid_id:
                researcher.orcid_id = orcid
            researcher.updated_at = datetime.utcnow()
            return False

        # Create new researcher
        researcher_id = f"{org_id}:{name.replace(' ', '_').lower()}"
        if orcid:
            researcher_id = orcid

        researcher = Researcher(
            id=researcher_id,
            full_name=name,
            orcid_id=orcid,
            organization_id=org_id,
            publication_count=0,
            created_at=datetime.utcnow(),
        )

        db.add(researcher)
        db.flush()  # Get the ID

        return True

    def _link_researchers_to_publications(self, db, stats: Dict[str, Any]):
        """
        Link Researcher records to Publication author entries.
        Updates publication_author association table.

        Args:
            db: Database session
            stats: Statistics dictionary to update
        """
        linked = 0
        errors = 0

        # Get all publications with author data
        publications = db.query(Publication).filter(
            Publication.authors.isnot(None)
        ).all()

        for pub in publications:
            try:
                if not pub.authors or not isinstance(pub.authors, list):
                    continue

                for author_data in pub.authors:
                    if isinstance(author_data, dict):
                        author_name = author_data.get("name", "").strip()
                        orcid = author_data.get("orcid")

                        # Try to find researcher by ORCID first
                        researcher = None
                        if orcid:
                            researcher = db.query(Researcher).filter(
                                Researcher.orcid_id == orcid
                            ).first()

                        # Fall back to name + org match
                        if not researcher and pub.organization_id:
                            researcher = db.query(Researcher).filter(
                                Researcher.full_name.ilike(f"%{author_name}%"),
                                Researcher.organization_id == pub.organization_id,
                            ).first()

                        # Create link if researcher found
                        if researcher:
                            # Check if link already exists
                            existing = db.query(publication_author).filter(
                                publication_author.c.publication_id == pub.id,
                                publication_author.c.researcher_id == researcher.id,
                            ).first()

                            if not existing:
                                # Create link
                                stmt = publication_author.insert().values(
                                    publication_id=pub.id,
                                    researcher_id=researcher.id,
                                )
                                db.execute(stmt)
                                linked += 1

            except Exception as e:
                logger.warning(f"Error linking researchers for {pub.id}: {e}")
                errors += 1

        db.commit()
        stats["researchers_linked"] = linked
        logger.info(f"Linked {linked} researcher-publication relationships")


def enrich_researchers():
    """
    Synchronous wrapper for researcher enrichment.

    Returns:
        Enrichment statistics
    """
    enricher = ResearcherEnricher(fuzzy_threshold=90)
    return enricher.enrich_all()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run enrichment
    stats = enrich_researchers()
    print(json.dumps(stats, indent=2, default=str))
