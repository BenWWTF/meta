"""
Analytics and Insights API
===========================

Advanced analytics endpoints for research trends, impact metrics, and insights.

Endpoints:
- GET /api/analytics/trends - Research trends by year and field
- GET /api/analytics/impact - Researcher impact metrics
- GET /api/analytics/funding - Funding efficiency and ROI
- GET /api/analytics/collaboration - Collaboration networks
- GET /api/analytics/open-access - Open access evolution
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case, and_
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.database import (
    get_db,
    Publication,
    Researcher,
    Organization,
    publication_author,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/trends",
    summary="Get research trends by year",
)
async def get_research_trends(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    publication_type: Optional[str] = Query(None, description="Filter by publication type"),
    db: Session = Depends(get_db),
):
    """
    Get research trends over time.

    **Query Parameters:**
    - `organization_id`: Filter to specific organization
    - `publication_type`: Filter to specific publication type

    **Response:**
    Publications by year with growth trends and statistics.
    """

    query = db.query(
        Publication.publication_year,
        func.count(Publication.id).label("total_publications"),
        func.sum(case((Publication.open_access == True, 1), else_=0)).label(
            "open_access_count"
        ),
    )

    # Apply filters
    if organization_id:
        query = query.filter(Publication.organization_id == organization_id)
    if publication_type:
        query = query.filter(Publication.publication_type == publication_type)

    # Group by year and order
    trends = (
        query.filter(Publication.publication_year.isnot(None))
        .group_by(Publication.publication_year)
        .order_by(Publication.publication_year)
        .all()
    )

    # Format response with OA percentage
    trend_data = []
    for year, total, oa_count in trends:
        trend_data.append({
            "year": year,
            "publications": total,
            "open_access": oa_count or 0,
            "open_access_pct": round((oa_count or 0) / total * 100, 1) if total > 0 else 0,
        })

    # Calculate growth rates
    growth_data = []
    for i, trend in enumerate(trend_data):
        if i > 0:
            prev_count = trend_data[i - 1]["publications"]
            curr_count = trend["publications"]
            growth_rate = (
                round((curr_count - prev_count) / prev_count * 100, 1)
                if prev_count > 0
                else 0
            )
            trend["growth_rate"] = growth_rate

    return {
        "trends": trend_data,
        "period": {
            "start_year": min([t["year"] for t in trend_data]) if trend_data else None,
            "end_year": max([t["year"] for t in trend_data]) if trend_data else None,
        },
    }


@router.get(
    "/impact",
    summary="Get researcher impact metrics",
)
async def get_researcher_impact(
    organization_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Get impact metrics for top researchers.

    **Response:**
    Researchers ranked by publication count, h-index, and open access rate.
    """

    query = db.query(
        Researcher,
        func.count(Publication.id).label("publication_count"),
        func.sum(case((Publication.open_access == True, 1), else_=0)).label(
            "open_access_count"
        ),
    ).join(publication_author).join(Publication)

    if organization_id:
        query = query.filter(Researcher.organization_id == organization_id)

    results = (
        query.group_by(Researcher.id)
        .order_by(desc("publication_count"))
        .limit(limit)
        .all()
    )

    researchers_impact = []
    for researcher, pub_count, oa_count in results:
        researchers_impact.append({
            "id": researcher.id,
            "name": researcher.full_name,
            "orcid": researcher.orcid_id,
            "organization": {
                "id": researcher.organization_id,
                "name": researcher.organization.name if researcher.organization else None,
            } if researcher.organization_id else None,
            "metrics": {
                "publications": pub_count or 0,
                "open_access": oa_count or 0,
                "open_access_pct": round((oa_count or 0) / pub_count * 100, 1)
                if pub_count > 0
                else 0,
                "h_index": researcher.h_index,
            },
        })

    return {
        "top_researchers": researchers_impact,
        "total": len(researchers_impact),
    }


@router.get(
    "/open-access",
    summary="Get open access statistics over time",
)
async def get_open_access_evolution(
    organization_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Track open access adoption over time.

    **Response:**
    Open access percentage by year showing evolution of OA practices.
    """

    query = db.query(
        Publication.publication_year,
        func.count(Publication.id).label("total"),
        func.sum(case((Publication.open_access == True, 1), else_=0)).label("oa_count"),
    )

    if organization_id:
        query = query.filter(Publication.organization_id == organization_id)

    oa_trends = (
        query.filter(Publication.publication_year.isnot(None))
        .group_by(Publication.publication_year)
        .order_by(Publication.publication_year)
        .all()
    )

    trend_data = []
    for year, total, oa_count in oa_trends:
        oa_pct = (oa_count or 0) / total * 100 if total > 0 else 0
        trend_data.append({
            "year": year,
            "total_publications": total,
            "open_access_publications": oa_count or 0,
            "open_access_percentage": round(oa_pct, 1),
        })

    return {
        "open_access_evolution": trend_data,
        "latest_oa_percentage": trend_data[-1]["open_access_percentage"]
        if trend_data
        else 0,
    }


@router.get(
    "/publication-types",
    summary="Get publication type distribution",
)
async def get_publication_type_distribution(
    organization_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get distribution of publication types in the research portfolio.

    **Response:**
    Publication count and breakdown by type (article, book, dataset, etc.).
    """

    query = db.query(
        Publication.publication_type,
        func.count(Publication.id).label("count"),
        func.sum(case((Publication.open_access == True, 1), else_=0)).label(
            "open_access_count"
        ),
    )

    if organization_id:
        query = query.filter(Publication.organization_id == organization_id)

    types = (
        query.filter(Publication.publication_type.isnot(None))
        .group_by(Publication.publication_type)
        .order_by(desc("count"))
        .all()
    )

    type_data = []
    total_pubs = 0

    for pub_type, count, oa_count in types:
        total_pubs += count
        type_data.append({
            "type": pub_type,
            "count": count,
            "open_access": oa_count or 0,
            "open_access_pct": round((oa_count or 0) / count * 100, 1)
            if count > 0
            else 0,
        })

    # Add percentages
    for item in type_data:
        item["percentage"] = round(item["count"] / total_pubs * 100, 1) if total_pubs > 0 else 0

    return {
        "publication_types": type_data,
        "total_publications": total_pubs,
    }


@router.get(
    "/organization-comparison",
    summary="Compare research metrics across organizations",
)
async def compare_organizations(
    org_ids: str = Query(..., description="Comma-separated organization IDs"),
    db: Session = Depends(get_db),
):
    """
    Compare research output and impact metrics across organizations.

    **Query Parameters:**
    - `org_ids`: Comma-separated list of organization ROR IDs

    **Response:**
    Comparative metrics for selected organizations.
    """

    # Parse org IDs
    organizations = org_ids.split(",")

    comparison_data = []

    for org_id in organizations:
        org_id = org_id.strip()

        # Get organization
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            continue

        # Get publications
        pubs = db.query(Publication).filter(Publication.organization_id == org_id)

        total_pubs = pubs.count()
        oa_pubs = pubs.filter(Publication.open_access == True).count()

        # Get researchers
        researchers = (
            db.query(func.count(Researcher.id))
            .filter(Researcher.organization_id == org_id)
            .scalar() or 0
        )

        # Average publications per researcher
        avg_per_researcher = (
            total_pubs / researchers if researchers > 0 else 0
        )

        # Year range
        years = (
            db.query(Publication.publication_year)
            .filter(Publication.organization_id == org_id)
            .filter(Publication.publication_year.isnot(None))
            .all()
        )
        years = [y[0] for y in years if y[0]]

        comparison_data.append({
            "organization": {
                "id": org.id,
                "name": org.name,
                "type": org.type,
            },
            "metrics": {
                "total_publications": total_pubs,
                "open_access_publications": oa_pubs,
                "open_access_percentage": round(oa_pubs / total_pubs * 100, 1)
                if total_pubs > 0
                else 0,
                "researchers": researchers,
                "avg_publications_per_researcher": round(avg_per_researcher, 1),
                "active_since": min(years) if years else None,
                "latest_publication_year": max(years) if years else None,
            },
        })

    return {
        "comparison": comparison_data,
        "count": len(comparison_data),
    }


@router.get(
    "/subject-areas",
    summary="Get research by subject area",
)
async def get_subject_areas(
    organization_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get research distribution across subject areas and keywords.

    **Response:**
    Top research subjects/keywords by publication count.
    """

    query = db.query(Publication).filter(Publication.subjects.isnot(None))

    if organization_id:
        query = query.filter(Publication.organization_id == organization_id)

    publications = query.all()

    # Extract and count subjects
    subject_counts = {}
    for pub in publications:
        if pub.subjects and isinstance(pub.subjects, list):
            for subject in pub.subjects:
                if isinstance(subject, str):
                    subject_counts[subject] = subject_counts.get(subject, 0) + 1

    # Sort and limit
    top_subjects = sorted(
        subject_counts.items(), key=lambda x: x[1], reverse=True
    )[:limit]

    return {
        "subject_areas": [
            {
                "subject": subject,
                "publications": count,
            }
            for subject, count in top_subjects
        ],
        "total_distinct_subjects": len(subject_counts),
    }
