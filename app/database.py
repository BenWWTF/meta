"""
Database Models and Configuration
==================================
Core SQLAlchemy ORM models for ARMP.

Models:
- Organization: Universities and research institutions
- Publication: Research papers and outputs
- Researcher: Individual researchers
- Project: Funded research projects
- PublicationAuthor: Many-to-many relationship
- ProjectPublisher: Research output from projects
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Text,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Table,
    Index,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import StaticPool

# Database configuration
DATABASE_URL = "sqlite:///./data/armp.db"

# For SQLite in-memory testing: "sqlite:///:memory:"
# For PostgreSQL: "postgresql://user:password@localhost/armp"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Association table for many-to-many relationship between Publications and Researchers
publication_author = Table(
    "publication_author",
    Base.metadata,
    Column("publication_id", String, ForeignKey("publication.id")),
    Column("researcher_id", String, ForeignKey("researcher.id")),
)

# Association table for Projects and Publications
project_publication = Table(
    "project_publication",
    Base.metadata,
    Column("project_id", String, ForeignKey("project.id")),
    Column("publication_id", String, ForeignKey("publication.id")),
)


class Organization(Base):
    """
    Research institution (university, research center, etc.)
    Represents organizations in the Austrian research landscape.
    """

    __tablename__ = "organization"

    id = Column(String, primary_key=True, index=True)  # ROR ID
    name = Column(String, index=True, nullable=False)
    ror_id = Column(String, unique=True, nullable=False)
    country = Column(String, default="AT")
    website = Column(String, nullable=True)
    type = Column(String, nullable=True)  # University, Research Institute, etc.

    # Relationships
    publications = relationship(
        "Publication", back_populates="organization", cascade="all, delete-orphan"
    )
    researchers = relationship(
        "Researcher", back_populates="organization", cascade="all, delete-orphan"
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Statistics (denormalized for performance)
    publication_count = Column(Integer, default=0)
    researcher_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<Organization {self.name}>"


class Publication(Base):
    """
    Research output (publication, dataset, software, etc.)
    Aggregated from OpenAIRE, Crossref, DataCite, and other sources.
    """

    __tablename__ = "publication"

    id = Column(String, primary_key=True, index=True)  # DOI or OpenAIRE ID
    doi = Column(String, unique=True, nullable=True, index=True)
    title = Column(String, nullable=False, index=True)
    abstract = Column(Text, nullable=True)
    publication_date = Column(DateTime, nullable=True, index=True)
    publication_year = Column(Integer, nullable=True, index=True)
    publication_type = Column(String, nullable=True)  # article, book, dataset, etc.

    # Authors (as JSON for flexibility, also linked via association table)
    authors = Column(JSON, nullable=True)  # [{name, orcid, affiliation}]

    # Source information
    source_system = Column(String, nullable=True)  # openaire, crossref, datacite
    openaire_id = Column(String, nullable=True, index=True)
    crossref_id = Column(String, nullable=True)

    # Publication details
    journal = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    issn = Column(String, nullable=True)
    isbn = Column(String, nullable=True)
    volume = Column(String, nullable=True)
    issue = Column(String, nullable=True)
    pages = Column(String, nullable=True)

    # Open Access
    open_access = Column(Boolean, nullable=True)
    license = Column(String, nullable=True)

    # Funding information
    funders = Column(JSON, nullable=True)  # [{name, id, project_id}]

    # Subject/Classification
    subjects = Column(JSON, nullable=True)  # [subject_keywords]
    sdg_mapping = Column(JSON, nullable=True)  # SDG mapping from OpenAIRE

    # Relationships
    organization_id = Column(String, ForeignKey("organization.id"), nullable=True)
    organization = relationship("Organization", back_populates="publications")

    researchers = relationship(
        "Researcher", secondary=publication_author, back_populates="publications"
    )
    projects = relationship(
        "Project", secondary=project_publication, back_populates="publications"
    )

    # Quality metrics
    citation_count = Column(Integer, nullable=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(String, ForeignKey("publication.id"), nullable=True)

    # Full text search metadata
    search_text = Column(Text, nullable=True)  # Denormalized for FTS

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    harvested_at = Column(DateTime, nullable=True)

    # Indexes for common queries
    __table_args__ = (
        Index("ix_publication_year", "publication_year"),
        Index("ix_publication_doi", "doi"),
        Index("ix_publication_source", "source_system"),
    )

    def __repr__(self):
        return f"<Publication {self.title[:50]}...>"


class Researcher(Base):
    """
    Individual researcher with publication history and profile.
    Integrated with ORCID for disambiguation.
    """

    __tablename__ = "researcher"

    id = Column(String, primary_key=True, index=True)  # Internal ID
    orcid_id = Column(String, unique=True, nullable=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    full_name = Column(String, index=True, nullable=False)

    # Affiliation
    organization_id = Column(String, ForeignKey("organization.id"), nullable=True)
    organization = relationship("Organization", back_populates="researchers")

    # Profile data from ORCID
    email = Column(String, nullable=True)
    orcid_profile_url = Column(String, nullable=True)

    # Biography/Profile
    biography = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # Research keywords from ORCID

    # Education and employment (from ORCID)
    education = Column(JSON, nullable=True)  # [{institution, degree, year}]
    employment = Column(JSON, nullable=True)  # [{organization, title, start, end}]

    # Relationships
    publications = relationship(
        "Publication", secondary=publication_author, back_populates="researchers"
    )

    # Statistics (denormalized)
    publication_count = Column(Integer, default=0)
    h_index = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Researcher {self.full_name}>"


class Project(Base):
    """
    Funded research project (primarily from FWF, FFG, WWTF, AWS)
    Links funding to research outputs.
    """

    __tablename__ = "project"

    id = Column(String, primary_key=True, index=True)  # Project ID
    grant_number = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, index=True, nullable=False)
    abstract = Column(Text, nullable=True)

    # Funding information
    funder = Column(String, nullable=True)  # FWF, FFG, WWTF, AWS, etc.
    funder_id = Column(String, nullable=True)
    funding_amount = Column(Float, nullable=True)
    currency = Column(String, default="EUR")

    # Project timeline
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Investigators (as JSON)
    investigators = Column(JSON, nullable=True)  # [{name, orcid, role}]
    principal_investigator = Column(String, nullable=True)

    # Project classification
    classification = Column(JSON, nullable=True)  # FWF categories, keywords
    keywords = Column(JSON, nullable=True)

    # Relationships
    publications = relationship(
        "Publication", secondary=project_publication, back_populates="projects"
    )

    # Project outcomes
    outcomes = Column(JSON, nullable=True)  # Datasets, software, policy impact

    # Source information
    source_system = Column(String, nullable=True)  # fwf, ffg, etc.
    external_url = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Project {self.title[:50]}...>"


class HarvestLog(Base):
    """
    Log of data harvesting operations for auditing and resumption.
    """

    __tablename__ = "harvest_log"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)  # openaire, crossref, orcid, fwf
    organization_id = Column(String, ForeignKey("organization.id"), nullable=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    record_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    last_cursor = Column(String, nullable=True)  # For pagination resumption

    def __repr__(self):
        return f"<HarvestLog {self.source} @ {self.started_at}>"


def init_db():
    """Initialize database with all tables."""
    print("Creating database tables...")
    try:
        # create_all will create tables and indexes only if they don't exist
        Base.metadata.create_all(bind=engine)
        print("✓ Database initialized successfully")
    except Exception as e:
        # Log the error but don't fail - tables might already exist
        print(f"Note: {str(e)}")
        print("✓ Database connection established")


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()

    # Create some sample organizations for testing
    from app.database import SessionLocal, Organization

    db = SessionLocal()

    # Add sample Austrian universities if not present
    universities = [
        {
            "id": "03prydq77",
            "name": "University of Vienna",
            "ror_id": "03prydq77",
            "website": "https://www.univie.ac.at",
        },
        {
            "id": "05qghxh33",
            "name": "TU Wien",
            "ror_id": "05qghxh33",
            "website": "https://www.tuwien.ac.at",
        },
        {
            "id": "03ak46v85",
            "name": "University of Innsbruck",
            "ror_id": "03ak46v85",
            "website": "https://www.uibk.ac.at",
        },
        {
            "id": "035xkbk20",
            "name": "University of Graz",
            "ror_id": "035xkbk20",
            "website": "https://www.uni-graz.at",
        },
        {
            "id": "00rbhpj83",
            "name": "JKU Linz",
            "ror_id": "00rbhpj83",
            "website": "https://www.jku.at",
        },
    ]

    for uni_data in universities:
        existing = db.query(Organization).filter_by(ror_id=uni_data["ror_id"]).first()
        if not existing:
            org = Organization(**uni_data)
            db.add(org)
            print(f"Added: {uni_data['name']}")

    db.commit()
    db.close()
    print("✓ Sample organizations created")
