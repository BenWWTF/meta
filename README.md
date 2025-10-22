# Austrian Research Metadata Platform (ARMP) MVP

A rapid, open-source MVP for aggregating and discovering Austrian research across all major universities and institutions.

## 🎯 Vision

Austria is 10-15 years behind Nordic countries in comprehensive research metadata infrastructure. This MVP demonstrates that **using openly accessible data sources** (OpenAIRE, Crossref, ORCID), we can build a valuable national research discovery platform in **2 weeks** that:

- Aggregates 100,000+ publications from all major Austrian institutions
- Provides researcher-centric discovery and profiling
- Demonstrates technical feasibility for national RIS coordination
- Validates the value of comprehensive research metadata
- Supports the transition from RIS Synergy project infrastructure to sustained operations

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git

### Installation

```bash
# Clone repository
cd /Users/Missbach/Desktop/claude/meta

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run initial data exploration
python scripts/explore_openaire.py
```

### First Demo (2 hours)
```bash
# Explore OpenAIRE data for top 5 Austrian universities
python scripts/explore_openaire.py

# See what data is immediately available
cat data/cache/openaire_sample.json | head -50
```

## 📋 Implementation Phases

### Phase 0: Rapid Proof (4 hours)
- [x] Quick OpenAIRE data exploration
- [x] Confirm Austrian research data is accessible
- [ ] Show statistics from initial harvest

### Phase 1: Functional Web Demo (Days 1-3)
- [ ] FastAPI backend with SQLite
- [ ] OpenAIRE harvester (50K+ publications)
- [ ] HTML/CSS frontend with Tailwind
- [ ] Deploy to Railway/Render (public URL)

### Phase 2: Enrichment & Researcher Features (Days 4-7)
- [ ] Crossref integration + deduplication
- [ ] Researcher profiles & author disambiguation
- [ ] ORCID integration
- [ ] Analytics dashboard

### Phase 3: Advanced Features (Week 2)
- [ ] FWF project data integration
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Database migration to PostgreSQL
- [ ] Performance optimization

## 🏛️ Austrian Universities Included

**Tier 1 (Start)**:
- University of Vienna (WU)
- TU Wien
- University of Innsbruck
- University of Graz
- JKU Linz

**Tier 2 (Add Day 2-3)**:
- Medical University of Vienna
- TU Graz
- University of Salzburg
- Medical University of Graz
- Medical University of Innsbruck

**Tier 3 (Comprehensive)**:
- BOKU Vienna
- WU Vienna
- University of Klagenfurt
- Montanuniversität Leoben
- Austrian Academy of Sciences

## 🔌 Data Sources

1. **OpenAIRE Graph API** - Primary source, pre-aggregated Austrian research
2. **Crossref API** - Publication enrichment and deduplication
3. **ORCID Public API** - Researcher profiles and disambiguation
4. **DataCite API** - Datasets and non-traditional outputs
5. **FWF Research Radar** - Austrian funding data

All sources are **openly accessible without special permissions** for read access.

## 🛠️ Technology Stack

**Backend**:
- FastAPI (high-performance, auto-docs)
- SQLite (initial) → PostgreSQL (production)
- SQLAlchemy ORM
- httpx (async HTTP client)

**Frontend**:
- Jinja2 templates (server-side rendering)
- Tailwind CSS (rapid styling)
- Alpine.js (lightweight interactivity)
- Chart.js (visualizations)

**Deployment**:
- Railway or Render (free tier)
- Docker containerization
- GitHub Actions CI/CD

## 📊 Project Structure

```
/Users/Missbach/Desktop/claude/meta/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
│
├── app/
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration
│   ├── database.py         # Database setup
│   ├── schemas.py          # Pydantic models
│   ├── api/                # API endpoints
│   ├── services/           # Business logic
│   ├── harvesters/         # Data collection
│   └── templates/          # HTML templates
│
├── scripts/
│   ├── explore_openaire.py  # Initial exploration
│   ├── harvest_all.py       # Full harvest
│   └── migrate_db.py        # DB migrations
│
├── tests/                  # Unit tests
└── data/                   # Local data storage
    ├── cache/              # API responses
    └── exports/            # Generated exports
```

## 🔄 API Design

The platform exposes a clean REST API:

```
GET  /api/publications           # Search publications
GET  /api/publications/{id}      # Publication details
GET  /api/organizations          # List universities
GET  /api/organizations/{id}     # University research
GET  /api/researchers            # Researcher directory
GET  /api/researchers/{id}       # Researcher profile
GET  /api/projects               # FWF projects
GET  /api/stats                  # Aggregate statistics
```

## 📈 Success Metrics (After 2 Weeks)

- 100,000+ publications indexed
- All major Austrian universities covered
- <2 second search response time
- Public API with OpenAPI documentation
- Shareable demo link for stakeholders
- Researcher profiles with publication lists
- Analytics dashboard with visualization

## 🎓 Research Value

This MVP demonstrates:

1. **Comprehensive coverage**: 15+ institutions, 100K+ outputs
2. **Researcher utility**: Search publications, build profiles, find collaborators
3. **Institutional value**: Compare research output, identify strengths
4. **Policy support**: Evidence-based research funding decisions
5. **International positioning**: Compare with Nordic systems

## 🤝 Integration with RIS Synergy

This prototype:
- Validates the technical approach recommended by RIS Synergy
- Provides immediate value while institutional APIs mature
- Demonstrates the benefits of coordinated research metadata
- Builds momentum for mandatory participation in standardized interfaces
- Serves as reference implementation for CERIF/OpenAIRE compliance

## 📖 Documentation

- **API Docs**: Available at `/docs` (OpenAPI/Swagger UI)
- **User Guide**: [Coming Week 2]
- **Developer Guide**: See DEVELOPMENT.md [Coming Week 2]
- **Data Dictionary**: See DATA.md [Coming Week 2]

## 📝 License

MIT License - encouraging reuse and contribution

## 🙋 Contributors

- [Your Name] - Concept & Implementation

## 📞 Contact

Questions about the prototype? Open an issue on GitHub.

---

**Status**: Phase 0 - Data Exploration (In Progress)
**Target**: Week 1 - Public MVP Launch
**Full Timeline**: 2 weeks to comprehensive platform
