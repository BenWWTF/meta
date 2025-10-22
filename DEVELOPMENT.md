# Development Guide - Austrian Research Metadata Platform

## Quick Start (5 minutes)

### 1. Setup Environment

```bash
# Clone/navigate to project
cd /Users/Missbach/Desktop/claude/meta

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# Create database and tables
python -c "from app.database import init_db; init_db()"

# Or directly:
python app/database.py
```

### 3. Harvest Data (First Demo!)

```bash
# Quick harvest: 100 publications from University of Vienna
python scripts/harvest_openaire.py --max-records 100 --single "03prydq77"

# Full harvest: All Austrian universities (slower, ~30 min first time)
python scripts/harvest_openaire.py

# Watch progress in real-time
tail -f harvest.log
```

### 4. Run API Server

```bash
# Start development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or simpler:
cd /Users/Missbach/Desktop/claude/meta
uvicorn app.main:app --reload
```

### 5. Explore API

Open browser and visit:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints (Fully Working)

### Organizations
```bash
# List all organizations
curl "http://localhost:8000/api/organizations"

# Get specific organization
curl "http://localhost:8000/api/organizations/03prydq77"

# Get organization statistics
curl "http://localhost:8000/api/organizations/03prydq77/stats"

# Compare organizations
curl "http://localhost:8000/api/organizations/compare?org_ids=03prydq77,05qghxh33"
```

### Publications
```bash
# Search publications
curl "http://localhost:8000/api/publications?q=machine+learning&limit=10"

# Get publications by year range
curl "http://localhost:8000/api/publications?year_from=2020&year_to=2024&limit=20"

# Get publication details by DOI
curl "http://localhost:8000/api/publications/doi/10.1234/example"

# Get organization publications
curl "http://localhost:8000/api/publications/by-organization/03prydq77"

# Get publication statistics
curl "http://localhost:8000/api/publications/stats/overview"

# Get recent publications
curl "http://localhost:8000/api/publications/recent?limit=10"
```

## Project Structure

```
meta/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── database.py          # SQLAlchemy models (Publications, Researchers, etc.)
│   ├── schemas.py           # Pydantic schemas (request/response validation)
│   ├── config.py            # Configuration management
│   ├── api/
│   │   ├── publications.py  # Publication endpoints
│   │   └── organizations.py # Organization endpoints
│   ├── services/            # Business logic (search, deduplication, etc.)
│   ├── harvesters/
│   │   ├── openaire.py      # OpenAIRE API harvester
│   │   ├── crossref.py      # [Coming] Crossref enrichment
│   │   ├── orcid.py         # [Coming] ORCID integration
│   │   └── fwf.py           # [Coming] FWF project data
│   └── templates/           # HTML templates [Phase 1c]
│
├── scripts/
│   ├── harvest_openaire.py  # Main harvesting script
│   ├── harvest_crossref.py  # [Coming] Crossref harvester script
│   └── migrate_db.py        # [Coming] Database migration helper
│
├── tests/                   # Unit tests [Coming]
├── data/
│   ├── armp.db             # SQLite database (auto-created)
│   ├── cache/              # API response caching
│   ├── exports/            # Data exports
│   └── harvest_stats.json  # Latest harvest statistics
│
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── README.md               # Project overview
├── DEVELOPMENT.md          # This file
└── .gitignore
```

## Database Schema

### Core Tables

**organizations**
- id (String, primary key) - ROR ID
- name (String) - Organization name
- ror_id (String, unique) - ROR identifier
- country (String) - Country code
- website (String)
- type (String) - University, Research Institute, etc.
- publication_count (Integer)
- researcher_count (Integer)
- created_at, updated_at (DateTime)

**publications**
- id (String, primary key) - DOI or OpenAIRE ID
- doi (String, unique) - Digital Object Identifier
- title (String) - Publication title
- abstract (Text) - Publication abstract
- publication_date (DateTime)
- publication_year (Integer)
- publication_type (String) - article, book, dataset, etc.
- authors (JSON) - Author list
- journal (String)
- publisher (String)
- open_access (Boolean)
- license (String)
- source_system (String) - openaire, crossref, datacite
- organization_id (Foreign Key)
- harvested_at (DateTime)

**researchers** (Coming)
- id (String, primary key)
- orcid_id (String, unique)
- full_name (String)
- organization_id (Foreign Key)
- publication_count (Integer)

**projects** (Coming)
- id (String, primary key)
- grant_number (String)
- title (String)
- funder (String)
- funding_amount (Float)
- start_date, end_date (DateTime)

## Key Technologies

**Backend**
- **FastAPI** - Modern Python API framework with auto-documentation
- **SQLAlchemy** - ORM for database operations
- **SQLite** - Initial database (upgradeable to PostgreSQL)
- **Pydantic** - Data validation and serialization
- **httpx** - Async HTTP client for API calls

**Data Sources**
- **OpenAIRE** - Primary source, pre-aggregated Austrian research
- **Crossref** - Publication enrichment (Phase 2)
- **ORCID** - Researcher profiles (Phase 2)
- **DataCite** - Research datasets (Phase 2)
- **FWF** - Austrian funding data (Phase 3)

## Development Workflow

### Adding a New API Endpoint

1. **Create endpoint in api module** (e.g., `app/api/publications.py`)
   ```python
   from fastapi import APIRouter, Depends
   from app.database import get_db

   router = APIRouter(prefix="/api/endpoint", tags=["Endpoint"])

   @router.get("")
   async def my_endpoint(db: Session = Depends(get_db)):
       # Implementation
       return {"data": "..."}
   ```

2. **Include router in main.py**
   ```python
   from app.api import my_module
   app.include_router(my_module.router)
   ```

3. **Test with**
   ```bash
   curl "http://localhost:8000/api/endpoint"
   ```

### Adding a New Data Harvester

1. **Create harvester in app/harvesters/** (e.g., `crossref.py`)
2. **Implement async methods for API calls**
3. **Create CLI script in scripts/** (e.g., `harvest_crossref.py`)
4. **Test with sample data first**

## Performance Optimization

### Current
- SQLite with full-text search
- <2 second response times for typical queries
- 100 records per API call limit

### Future (Phase 3)
- PostgreSQL for production
- Elasticsearch for advanced full-text search
- Redis caching for frequently accessed data
- Database indexing optimization

## Troubleshooting

### Issue: Import errors when running harvester

**Solution:**
```bash
# Make sure you're in the project root
cd /Users/Missbach/Desktop/claude/meta

# And using the virtual environment
source venv/bin/activate

# Then run
python scripts/harvest_openaire.py
```

### Issue: "Database is locked" error

**Solution:**
```bash
# Close any other processes accessing the database
# If using SQLite, only one writer at a time

# Remove old database to start fresh
rm data/armp.db

# Reinitialize
python -c "from app.database import init_db; init_db()"
```

### Issue: OpenAIRE API timeout

**Solution:**
```bash
# Increase timeout
python scripts/harvest_openaire.py --timeout 60

# Or reduce batch size
python scripts/harvest_openaire.py --batch-size 50
```

### Issue: Module not found errors

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Testing

### Manual API Testing

```bash
# Start server in one terminal
uvicorn app.main:app --reload

# In another terminal, test endpoints
python -m pytest tests/  # [Coming]

# Or use curl
curl "http://localhost:8000/api/publications?q=quantum"
```

### Load Testing (Coming Phase 3)

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load_tests.py
```

## Database Inspection

### View SQLite database

```bash
# Install sqlite3 CLI if needed
brew install sqlite3  # macOS
# apt-get install sqlite3  # Linux

# Connect to database
sqlite3 data/armp.db

# Useful commands
.tables                          # List all tables
.schema publications             # View table structure
SELECT COUNT(*) FROM publications;  # Count records
SELECT * FROM publications LIMIT 5;  # View sample data
.exit                            # Exit
```

## Deployment Preparation

### Phase 1c: Web Interface
- [ ] Create HTML templates with Tailwind CSS
- [ ] Implement search interface
- [ ] Add organization browsing
- [ ] Create researcher profiles
- [ ] Deploy to Railway or Render

### Phase 2: Enrichment
- [ ] Add Crossref integration
- [ ] Implement researcher disambiguation
- [ ] Add ORCID integration
- [ ] Create analytics dashboard

### Phase 3: Production Ready
- [ ] Migrate to PostgreSQL
- [ ] Set up caching (Redis)
- [ ] Implement full-text search (Elasticsearch)
- [ ] Add comprehensive API documentation
- [ ] Set up monitoring and alerting

## Contributing

### Code Style
- Use Black for formatting: `black app/`
- Use Flake8 for linting: `flake8 app/`
- Follow PEP 8 naming conventions

### Adding Tests
```python
# tests/test_publications.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_publications():
    response = client.get("/api/publications?limit=10")
    assert response.status_code == 200
    assert "results" in response.json()
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [OpenAIRE Graph API](https://graph.openaire.eu/)
- [Crossref API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [ORCID Public API](https://orcid.org/organizations/integrators/API)

## Support

Questions? Issues?
- Check the logs: `tail -f harvest.log`
- Review API docs: http://localhost:8000/docs
- Check git history: `git log --oneline`

---

**Last Updated**: October 2024
**Phase**: 1b - OpenAIRE Harvesting Complete
**Next Phase**: 1c - Web Interface
