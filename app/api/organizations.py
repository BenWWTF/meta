"""
Organizations API Endpoints
=============================
Endpoints for listing and exploring research institutions.

Endpoints:
- GET /api/organizations - List all organizations
- GET /api/organizations/{id} - Get organization details
- GET /api/organizations/{id}/stats - Get organization statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List

from app.database import get_db, Organization, Publication
from app.schemas import OrganizationResponse

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


@router.get(
    "",
    response_model=dict,
    summary="List all organizations",
    description="Get list of all Austrian universities and research institutions",
)
async def list_organizations(
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List all organizations in the system.

    **Query Parameters:**
    - `search`: Optional text search by organization name
    - `limit`: Results per page (default: 100)
    - `offset`: Pagination offset (default: 0)

    **Response:**
    List of organizations with publication and researcher counts.
    """

    query = db.query(Organization)

    if search:
        search_term = f"%{search}%"
        query = query.filter(Organization.name.ilike(search_term))

    total = query.count()

    # Sort by publication count (descending)
    organizations = (
        query.order_by(desc(Organization.publication_count))
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            {
                "id": org.id,
                "name": org.name,
                "ror_id": org.ror_id,
                "website": org.website,
                "type": org.type,
                "publication_count": org.publication_count,
                "researcher_count": org.researcher_count,
            }
            for org in organizations
        ],
    }


@router.get(
    "/{org_id}",
    response_model=dict,
    summary="Get organization details",
)
async def get_organization(
    org_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific organization.

    **Parameters:**
    - `org_id`: Organization ROR ID or internal ID

    **Response:**
    Organization metadata including website, type, and statistics.
    """

    org = db.query(Organization).filter(Organization.id == org_id).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get publication statistics
    pub_count = (
        db.query(func.count(Publication.id))
        .filter(Publication.organization_id == org_id)
        .scalar() or 0
    )

    return {
        "id": org.id,
        "name": org.name,
        "ror_id": org.ror_id,
        "country": org.country,
        "website": org.website,
        "type": org.type,
        "publication_count": pub_count,
        "researcher_count": org.researcher_count,
        "created_at": org.created_at.isoformat(),
        "updated_at": org.updated_at.isoformat(),
    }


@router.get(
    "/{org_id}/stats",
    summary="Get organization statistics",
)
async def get_organization_stats(
    org_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed statistics for a specific organization.

    **Parameters:**
    - `org_id`: Organization ROR ID or internal ID

    **Response:**
    Publication trends, types, and other research metrics.
    """

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Publications by year
    by_year = (
        db.query(Publication.publication_year, func.count(Publication.id))
        .filter(Publication.organization_id == org_id)
        .filter(Publication.publication_year.isnot(None))
        .group_by(Publication.publication_year)
        .order_by(Publication.publication_year)
        .all()
    )

    # Publications by type
    by_type = (
        db.query(Publication.publication_type, func.count(Publication.id))
        .filter(Publication.organization_id == org_id)
        .filter(Publication.publication_type.isnot(None))
        .group_by(Publication.publication_type)
        .all()
    )

    # Open access percentage
    total_pubs = (
        db.query(func.count(Publication.id))
        .filter(Publication.organization_id == org_id)
        .scalar() or 0
    )

    oa_pubs = (
        db.query(func.count(Publication.id))
        .filter(Publication.organization_id == org_id, Publication.open_access == True)
        .scalar() or 0
    )

    oa_percentage = (oa_pubs / total_pubs * 100) if total_pubs > 0 else 0

    return {
        "organization": {
            "id": org.id,
            "name": org.name,
            "ror_id": org.ror_id,
        },
        "statistics": {
            "total_publications": total_pubs,
            "open_access_publications": oa_pubs,
            "open_access_percentage": round(oa_percentage, 2),
            "publications_by_year": {str(year): count for year, count in by_year},
            "publications_by_type": {pub_type: count for pub_type, count in by_type},
        },
    }


@router.get(
    "/ror/{ror_id}",
    response_model=dict,
    summary="Get organization by ROR ID",
)
async def get_organization_by_ror(
    ror_id: str,
    db: Session = Depends(get_db),
):
    """
    Get organization by its ROR (Research Organization Registry) identifier.

    **Parameters:**
    - `ror_id`: ROR identifier (e.g., 03prydq77)

    **Response:**
    Organization details.
    """

    org = db.query(Organization).filter(Organization.ror_id == ror_id).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "id": org.id,
        "name": org.name,
        "ror_id": org.ror_id,
        "country": org.country,
        "website": org.website,
        "type": org.type,
        "publication_count": org.publication_count,
    }


@router.get(
    "/compare",
    summary="Compare organizations",
)
async def compare_organizations(
    org_ids: str = Query(..., description="Comma-separated organization IDs"),
    db: Session = Depends(get_db),
):
    """
    Compare statistics across multiple organizations.

    **Query Parameters:**
    - `org_ids`: Comma-separated list of organization ROR IDs (e.g., "03prydq77,05qghxh33")

    **Response:**
    Comparative statistics for selected organizations.
    """

    org_id_list = [oid.strip() for oid in org_ids.split(",")]

    organizations = db.query(Organization).filter(Organization.id.in_(org_id_list)).all()

    if not organizations:
        raise HTTPException(status_code=404, detail="Organizations not found")

    comparison = []
    for org in organizations:
        total_pubs = (
            db.query(func.count(Publication.id))
            .filter(Publication.organization_id == org.id)
            .scalar() or 0
        )

        oa_pubs = (
            db.query(func.count(Publication.id))
            .filter(Publication.organization_id == org.id, Publication.open_access == True)
            .scalar() or 0
        )

        oa_percentage = (oa_pubs / total_pubs * 100) if total_pubs > 0 else 0

        comparison.append(
            {
                "id": org.id,
                "name": org.name,
                "total_publications": total_pubs,
                "open_access_publications": oa_pubs,
                "open_access_percentage": round(oa_percentage, 2),
            }
        )

    return {"organizations": comparison}
