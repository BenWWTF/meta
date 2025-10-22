"""
Publications API Endpoints
==========================
Endpoints for searching, listing, and retrieving publication data.

Endpoints:
- GET /api/publications - Search and list publications
- GET /api/publications/{id} - Get publication details
- GET /api/publications/by-doi/{doi} - Get publication by DOI
- GET /api/publications/stats - Publication statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from datetime import datetime
from typing import List, Optional

from app.database import get_db, Publication, Organization
from app.schemas import (
    PublicationResponse,
    PublicationSearchRequest,
    PublicationSearchResponse,
)

router = APIRouter(prefix="/api/publications", tags=["Publications"])


@router.get(
    "",
    response_model=dict,
    summary="Search publications",
    description="Search publications across all organizations with optional filters",
)
async def search_publications(
    q: Optional[str] = Query(None, description="Search query (title, abstract, keywords)"),
    year_from: Optional[int] = Query(None, description="Starting year (inclusive)"),
    year_to: Optional[int] = Query(None, description="Ending year (inclusive)"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ROR ID"),
    pub_type: Optional[str] = Query(None, description="Publication type filter"),
    open_access: Optional[bool] = Query(None, description="Only open access publications"),
    limit: int = Query(50, ge=1, le=1000, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    Search publications with flexible filtering.

    **Query Parameters:**
    - `q`: Free text search in title and abstract
    - `year_from` / `year_to`: Filter by publication year range
    - `organization_id`: Filter by organization ROR ID
    - `pub_type`: Filter by publication type (article, book, dataset, etc.)
    - `open_access`: Only return open access publications
    - `limit`: Number of results (default: 50, max: 1000)
    - `offset`: Pagination offset (default: 0)

    **Response:**
    Returns paginated list of publications matching criteria with total count.
    """

    query = db.query(Publication)

    # Text search
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (Publication.title.ilike(search_term))
            | (Publication.abstract.ilike(search_term))
        )

    # Year range filter
    if year_from:
        query = query.filter(Publication.publication_year >= year_from)
    if year_to:
        query = query.filter(Publication.publication_year <= year_to)

    # Organization filter
    if organization_id:
        query = query.filter(Publication.organization_id == organization_id)

    # Publication type filter
    if pub_type:
        query = query.filter(Publication.publication_type == pub_type)

    # Open access filter
    if open_access:
        query = query.filter(Publication.open_access == True)

    # Get total count before pagination
    total = query.count()

    # Sort by most recent first
    query = query.order_by(desc(Publication.publication_date))

    # Pagination
    publications = query.limit(limit).offset(offset).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            PublicationResponse.model_validate(pub).__dict__ for pub in publications
        ],
    }


@router.get(
    "/{publication_id}",
    response_model=PublicationResponse,
    summary="Get publication details",
)
async def get_publication(
    publication_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific publication by ID.

    **Parameters:**
    - `publication_id`: Publication ID (DOI or OpenAIRE ID)

    **Response:**
    Complete publication metadata including authors, abstract, funding info.
    """

    publication = db.query(Publication).filter(Publication.id == publication_id).first()

    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")

    return PublicationResponse.model_validate(publication)


@router.get(
    "/doi/{doi}",
    response_model=PublicationResponse,
    summary="Get publication by DOI",
)
async def get_publication_by_doi(
    doi: str,
    db: Session = Depends(get_db),
):
    """
    Get publication details by DOI (Digital Object Identifier).

    **Parameters:**
    - `doi`: DOI without the https://doi.org/ prefix

    **Response:**
    Complete publication metadata.
    """

    # Normalize DOI (remove common prefixes if present)
    normalized_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

    publication = (
        db.query(Publication).filter(Publication.doi == normalized_doi).first()
    )

    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")

    return PublicationResponse.model_validate(publication)


@router.get(
    "/stats/overview",
    summary="Get publication statistics",
)
async def get_publication_stats(
    db: Session = Depends(get_db),
):
    """
    Get aggregate statistics about publications in the system.

    **Response:**
    - Total publications
    - Publications by year
    - Publications by type
    - Open access percentage
    """

    total = db.query(func.count(Publication.id)).scalar() or 0

    # By year
    by_year = (
        db.query(Publication.publication_year, func.count(Publication.id))
        .filter(Publication.publication_year.isnot(None))
        .group_by(Publication.publication_year)
        .order_by(Publication.publication_year)
        .all()
    )

    # By type
    by_type = (
        db.query(Publication.publication_type, func.count(Publication.id))
        .filter(Publication.publication_type.isnot(None))
        .group_by(Publication.publication_type)
        .all()
    )

    # Open access count
    open_access_count = (
        db.query(func.count(Publication.id))
        .filter(Publication.open_access == True)
        .scalar() or 0
    )

    oa_percentage = (open_access_count / total * 100) if total > 0 else 0

    return {
        "total_publications": total,
        "open_access_count": open_access_count,
        "open_access_percentage": round(oa_percentage, 2),
        "by_year": {str(year): count for year, count in by_year},
        "by_type": {pub_type: count for pub_type, count in by_type},
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get(
    "/by-organization/{org_id}",
    response_model=dict,
    summary="Get publications by organization",
)
async def get_organization_publications(
    org_id: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all publications from a specific organization.

    **Parameters:**
    - `org_id`: Organization ROR ID
    - `limit`: Results per page
    - `offset`: Pagination offset

    **Response:**
    Paginated list of publications with organization details.
    """

    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get publications
    query = db.query(Publication).filter(Publication.organization_id == org_id)
    total = query.count()

    publications = (
        query.order_by(desc(Publication.publication_date))
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "organization": {
            "id": org.id,
            "name": org.name,
            "ror_id": org.ror_id,
        },
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            PublicationResponse.model_validate(pub).__dict__ for pub in publications
        ],
    }


@router.get(
    "/recent",
    response_model=dict,
    summary="Get recent publications",
)
async def get_recent_publications(
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get the most recently added or updated publications.

    **Parameters:**
    - `limit`: Number of results to return (default: 50)

    **Response:**
    List of recently added publications.
    """

    publications = (
        db.query(Publication)
        .order_by(desc(Publication.harvested_at))
        .limit(limit)
        .all()
    )

    return {
        "total": len(publications),
        "results": [
            PublicationResponse.model_validate(pub).__dict__ for pub in publications
        ],
    }


@router.get(
    "/stats/by-source",
    summary="Get statistics by publication source",
)
async def get_publications_by_source(db: Session = Depends(get_db)):
    """
    Get publication statistics by data source (OpenAIRE, Crossref, etc.).

    **Response:**
    - Total publications per source
    - Open access count per source
    - Open access percentage per source
    """

    sources = (
        db.query(
            Publication.source_system,
            func.count(Publication.id).label("count"),
            func.sum(case((Publication.open_access == True, 1), else_=0)).label(
                "open_access_count"
            ),
        )
        .group_by(Publication.source_system)
        .all()
    )

    source_stats = {}
    for source, count, oa_count in sources:
        source_name = source or "unknown"
        source_stats[source_name] = {
            "total": count,
            "open_access": oa_count or 0,
            "open_access_pct": (
                round((oa_count or 0) / count * 100, 1) if count > 0 else 0
            ),
        }

    return source_stats
