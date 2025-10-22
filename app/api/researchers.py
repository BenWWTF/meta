"""
Researchers API Endpoints
==========================
Endpoints for researcher profiles, publication history, and collaboration networks.

Endpoints:
- GET /api/researchers - Search and list researchers
- GET /api/researchers/{id} - Get researcher profile
- GET /api/researchers/{id}/publications - Get researcher's publications
- GET /api/researchers/{id}/collaborators - Get collaborators
- GET /api/researchers/search/by-name - Find researchers by name
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime
from typing import List, Optional
from fuzzywuzzy import fuzz

from app.database import get_db, Researcher, Publication, publication_author
from app.schemas import (
    ResearcherResponse,
    ResearcherProfileResponse,
)

router = APIRouter(prefix="/api/researchers", tags=["Researchers"])


@router.get(
    "",
    response_model=dict,
    summary="Search researchers",
    description="Search researchers across all organizations",
)
async def search_researchers(
    q: Optional[str] = Query(None, description="Search by name or ORCID"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ROR ID"),
    min_publications: Optional[int] = Query(None, description="Minimum publication count"),
    limit: int = Query(50, ge=1, le=1000, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    Search researchers with flexible filtering.

    **Query Parameters:**
    - `q`: Search by name or ORCID
    - `organization_id`: Filter by organization ROR ID
    - `min_publications`: Filter by minimum publication count
    - `limit`: Number of results (default: 50, max: 1000)
    - `offset`: Pagination offset (default: 0)

    **Response:**
    Returns paginated list of researchers matching criteria.
    """

    query = db.query(Researcher)

    # Search by name or ORCID
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (Researcher.full_name.ilike(search_term))
            | (Researcher.orcid_id.ilike(search_term))
        )

    # Organization filter
    if organization_id:
        query = query.filter(Researcher.organization_id == organization_id)

    # Minimum publications filter
    if min_publications is not None:
        query = query.filter(Researcher.publication_count >= min_publications)

    # Get total count before pagination
    total = query.count()

    # Sort by publication count (most published first)
    query = query.order_by(desc(Researcher.publication_count))

    # Pagination
    researchers = query.limit(limit).offset(offset).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            ResearcherResponse.model_validate(r).__dict__ for r in researchers
        ],
    }


@router.get(
    "/{researcher_id}",
    response_model=ResearcherProfileResponse,
    summary="Get researcher profile",
)
async def get_researcher(
    researcher_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed profile information about a specific researcher.

    **Parameters:**
    - `researcher_id`: Researcher ID (internal ID or ORCID)

    **Response:**
    Complete researcher profile with education, employment, and statistics.
    """

    # Try to find by internal ID first
    researcher = db.query(Researcher).filter(Researcher.id == researcher_id).first()

    # Try by ORCID if not found
    if not researcher:
        researcher = db.query(Researcher).filter(
            Researcher.orcid_id == researcher_id
        ).first()

    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    return ResearcherProfileResponse.model_validate(researcher)


@router.get(
    "/{researcher_id}/publications",
    response_model=dict,
    summary="Get researcher's publications",
)
async def get_researcher_publications(
    researcher_id: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all publications authored by a specific researcher.

    **Parameters:**
    - `researcher_id`: Researcher ID
    - `limit`: Results per page
    - `offset`: Pagination offset

    **Response:**
    List of publications authored by researcher with metadata.
    """

    # Verify researcher exists
    researcher = db.query(Researcher).filter(Researcher.id == researcher_id).first()
    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    # Get publications
    from app.schemas import PublicationResponse

    query = db.query(Publication).join(
        publication_author, Publication.id == publication_author.c.publication_id
    ).filter(publication_author.c.researcher_id == researcher_id)

    total = query.count()

    publications = (
        query.order_by(desc(Publication.publication_date))
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "researcher": {
            "id": researcher.id,
            "name": researcher.full_name,
            "orcid": researcher.orcid_id,
        },
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            PublicationResponse.model_validate(pub).__dict__ for pub in publications
        ],
    }


@router.get(
    "/{researcher_id}/collaborators",
    response_model=dict,
    summary="Get researcher's collaborators",
)
async def get_researcher_collaborators(
    researcher_id: str,
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get list of collaborators (co-authors) of a specific researcher.

    **Parameters:**
    - `researcher_id`: Researcher ID
    - `limit`: Maximum number of collaborators to return

    **Response:**
    List of collaborators with collaboration frequency.
    """

    # Verify researcher exists
    researcher = db.query(Researcher).filter(Researcher.id == researcher_id).first()
    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    # Find all publications by this researcher
    researcher_pubs = db.query(publication_author).filter(
        publication_author.c.researcher_id == researcher_id
    ).all()

    pub_ids = [pub.publication_id for pub in researcher_pubs]

    if not pub_ids:
        return {
            "researcher": {
                "id": researcher.id,
                "name": researcher.full_name,
            },
            "total_collaborators": 0,
            "collaborators": [],
        }

    # Find all co-authors on those publications
    collaborators_query = (
        db.query(
            Researcher,
            func.count(publication_author.c.publication_id).label("collaboration_count"),
        )
        .join(publication_author)
        .filter(
            and_(
                publication_author.c.publication_id.in_(pub_ids),
                publication_author.c.researcher_id != researcher_id,
            )
        )
        .group_by(Researcher.id)
        .order_by(desc("collaboration_count"))
        .limit(limit)
    )

    collaborators = []
    for collab, count in collaborators_query.all():
        collaborators.append({
            "id": collab.id,
            "name": collab.full_name,
            "orcid": collab.orcid_id,
            "publications_together": count,
            "organization": {
                "id": collab.organization_id,
                "name": collab.organization.name if collab.organization else None,
            } if collab.organization_id else None,
        })

    return {
        "researcher": {
            "id": researcher.id,
            "name": researcher.full_name,
        },
        "total_collaborators": len(collaborators),
        "collaborators": collaborators,
    }


@router.get(
    "/search/by-name",
    response_model=dict,
    summary="Find researchers by name with fuzzy matching",
)
async def search_researchers_by_name(
    q: str = Query(..., description="Researcher name to search for"),
    threshold: int = Query(80, ge=0, le=100, description="Fuzzy match threshold (0-100)"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Find researchers by name with fuzzy string matching.
    Useful for disambiguation and typo tolerance.

    **Query Parameters:**
    - `q`: Name to search for
    - `threshold`: Fuzzy match threshold (0-100, default 80)
    - `limit`: Maximum results to return

    **Response:**
    List of researchers ranked by match score.
    """

    if not q or len(q) < 2:
        raise HTTPException(
            status_code=400, detail="Search query must be at least 2 characters"
        )

    # Get all researchers (limited set for matching)
    all_researchers = db.query(Researcher).limit(10000).all()

    # Fuzzy match
    matches = []
    for researcher in all_researchers:
        # Match against full name and individual names
        name_score = fuzz.token_sort_ratio(q.lower(), researcher.full_name.lower())
        partial_score = fuzz.partial_token_set_ratio(
            q.lower(), researcher.full_name.lower()
        )

        # Use the higher score
        score = max(name_score, partial_score)

        if score >= threshold:
            matches.append({
                "researcher": {
                    "id": researcher.id,
                    "name": researcher.full_name,
                    "orcid": researcher.orcid_id,
                    "publication_count": researcher.publication_count,
                },
                "match_score": score,
            })

    # Sort by match score
    matches.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "query": q,
        "threshold": threshold,
        "total_matches": len(matches),
        "results": matches[:limit],
    }


@router.get(
    "/stats/overview",
    summary="Get researcher statistics",
)
async def get_researcher_stats(db: Session = Depends(get_db)):
    """
    Get aggregate statistics about researchers in the system.

    **Response:**
    - Total researchers
    - Researchers by organization
    - H-index distribution
    - Active researchers (with recent publications)
    """

    total_researchers = db.query(func.count(Researcher.id)).scalar() or 0

    # By organization
    by_org = (
        db.query(
            func.count(Researcher.id).label("count"),
        )
        .filter(Researcher.organization_id.isnot(None))
        .scalar() or 0
    )

    # H-index statistics
    h_indices = (
        db.query(Researcher.h_index)
        .filter(Researcher.h_index.isnot(None))
        .all()
    )
    h_indices = [h[0] for h in h_indices if h[0] is not None]

    avg_h_index = (sum(h_indices) / len(h_indices)) if h_indices else 0
    max_h_index = max(h_indices) if h_indices else 0

    # Most published researchers
    top_researchers = (
        db.query(
            Researcher.full_name,
            Researcher.publication_count,
            Researcher.h_index,
        )
        .order_by(desc(Researcher.publication_count))
        .limit(10)
        .all()
    )

    return {
        "total_researchers": total_researchers,
        "researchers_with_org": by_org,
        "researchers_with_orcid": (
            db.query(func.count(Researcher.id))
            .filter(Researcher.orcid_id.isnot(None))
            .scalar() or 0
        ),
        "average_publications": (
            db.query(func.avg(Researcher.publication_count)).scalar() or 0
        ),
        "h_index_statistics": {
            "average": round(avg_h_index, 2),
            "maximum": max_h_index,
            "tracked": len(h_indices),
        },
        "top_researchers": [
            {
                "name": name,
                "publications": pub_count,
                "h_index": h_idx,
            }
            for name, pub_count, h_idx in top_researchers
        ],
        "last_updated": datetime.utcnow().isoformat(),
    }
