"""
Pydantic Schemas for API Request/Response Validation
=====================================================
Used by FastAPI for request/response validation and automatic API documentation.

These schemas define the contract between frontend and backend.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Organization Schemas
# ============================================================================


class OrganizationBase(BaseModel):
    """Base organization schema"""

    name: str = Field(..., description="Organization name")
    ror_id: str = Field(..., description="ROR identifier")
    country: Optional[str] = Field(default="AT")
    website: Optional[str] = None
    type: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Schema for creating organization"""

    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating organization"""

    name: Optional[str] = None
    website: Optional[str] = None
    type: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""

    id: str
    publication_count: int = 0
    researcher_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Publication Schemas
# ============================================================================


class PublicationAuthor(BaseModel):
    """Author information in publication"""

    name: str
    orcid: Optional[str] = None
    affiliation: Optional[str] = None


class PublicationFunder(BaseModel):
    """Funding information"""

    name: str
    id: Optional[str] = None
    project_id: Optional[str] = None


class PublicationBase(BaseModel):
    """Base publication schema"""

    title: str = Field(..., description="Publication title")
    abstract: Optional[str] = None
    publication_date: Optional[datetime] = None
    publication_year: Optional[int] = None
    publication_type: Optional[str] = None
    journal: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None


class PublicationCreate(PublicationBase):
    """Schema for creating publication"""

    organization_id: Optional[str] = None
    source_system: Optional[str] = None
    authors: Optional[List[PublicationAuthor]] = None
    funders: Optional[List[PublicationFunder]] = None


class PublicationResponse(PublicationBase):
    """Schema for publication response"""

    id: str
    openaire_id: Optional[str] = None
    doi: Optional[str] = None
    open_access: Optional[bool] = None
    license: Optional[str] = None
    authors: Optional[List[dict]] = None
    source_system: Optional[str] = None
    created_at: datetime
    harvested_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublicationSearchResponse(PublicationResponse):
    """Publication response with search context"""

    relevance_score: Optional[float] = None
    matching_fields: Optional[List[str]] = None


class PublicationWithAuthorsResponse(PublicationResponse):
    """Publication with full author information"""

    researcher_authors: Optional[List["ResearcherBasicResponse"]] = None


# ============================================================================
# Researcher Schemas
# ============================================================================


class ResearcherBase(BaseModel):
    """Base researcher schema"""

    full_name: str = Field(..., description="Full name")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    orcid_id: Optional[str] = None


class ResearcherBasicResponse(ResearcherBase):
    """Minimal researcher response"""

    id: str
    organization_id: Optional[str] = None


class ResearcherCreate(ResearcherBase):
    """Schema for creating researcher"""

    organization_id: Optional[str] = None


class ResearcherResponse(ResearcherBase):
    """Full researcher response"""

    id: str
    organization_id: Optional[str] = None
    orcid_profile_url: Optional[str] = None
    biography: Optional[str] = None
    publication_count: int = 0
    h_index: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResearcherProfileResponse(ResearcherResponse):
    """Researcher profile with publication summary"""

    publications: Optional[List[PublicationResponse]] = None
    publications_by_year: Optional[dict] = None  # {year: count}
    recent_publications: Optional[List[PublicationResponse]] = None


# ============================================================================
# Project Schemas
# ============================================================================


class ProjectInvestigator(BaseModel):
    """Project investigator information"""

    name: str
    orcid: Optional[str] = None
    role: Optional[str] = None


class ProjectBase(BaseModel):
    """Base project schema"""

    title: str = Field(..., description="Project title")
    grant_number: str = Field(..., description="Grant/project number")
    abstract: Optional[str] = None
    funder: Optional[str] = None
    funding_amount: Optional[float] = None
    currency: Optional[str] = "EUR"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    """Schema for creating project"""

    investigators: Optional[List[ProjectInvestigator]] = None
    principal_investigator: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Full project response"""

    id: str
    funder_id: Optional[str] = None
    principal_investigator: Optional[str] = None
    keywords: Optional[List[str]] = None
    external_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectWithPublicationsResponse(ProjectResponse):
    """Project with linked publications"""

    publication_count: int = 0
    publications: Optional[List[PublicationResponse]] = None


# ============================================================================
# Search & Filter Schemas
# ============================================================================


class SearchFilters(BaseModel):
    """Filters for search operations"""

    query: Optional[str] = Field(None, description="Free text search query")
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    organization_id: Optional[str] = None
    publication_type: Optional[str] = None
    open_access_only: Optional[bool] = False
    funder: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class PublicationSearchRequest(SearchFilters):
    """Request schema for publication search"""

    pass


class ResearcherSearchRequest(SearchFilters):
    """Request schema for researcher search"""

    pass


# ============================================================================
# Statistics Schemas
# ============================================================================


class StatisticsResponse(BaseModel):
    """Overall platform statistics"""

    total_publications: int
    total_researchers: int
    total_organizations: int
    total_projects: int
    publications_by_year: dict = {}
    publications_by_type: dict = {}
    publications_by_organization: dict = {}
    open_access_percentage: float = 0.0
    last_updated: datetime


class OrganizationStatisticsResponse(BaseModel):
    """Statistics for specific organization"""

    organization: OrganizationResponse
    publication_count: int
    researcher_count: int
    publications_by_year: dict = {}
    publications_by_type: dict = {}
    top_researchers: List[ResearcherResponse] = []


# ============================================================================
# Error Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str
    message: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Health Check
# ============================================================================


class HealthCheckResponse(BaseModel):
    """API health check response"""

    status: str = "healthy"
    version: str = "0.1.0"
    database: str = "connected"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Update forward references
PublicationWithAuthorsResponse.model_rebuild()
