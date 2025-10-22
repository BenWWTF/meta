# Quick Start Guide (15 minutes to working demo)

Get the Austrian Research Metadata Platform running in just **15 minutes**.

## Prerequisites

- Python 3.11 or later
- `pip` (Python package manager)
- Terminal/Command line access

## Step 1: Setup (3 minutes)

```bash
# Navigate to project directory
cd /Users/Missbach/Desktop/claude/meta

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install all dependencies (2-3 minutes)
pip install -r requirements.txt
```

## Step 2: Initialize Database (1 minute)

```bash
# Create SQLite database with tables
python -c "from app.database import init_db; init_db()"

# Verify it worked
ls -lh data/armp.db
```

## Step 3: Harvest Sample Data (5 minutes)

```bash
# Harvest 500 publications from University of Vienna as a demo
python scripts/harvest_openaire.py --max-records 500 --single "03prydq77"

# Watch it work! You should see:
# - "Starting harvest for University of Vienna"
# - Periodic progress updates
# - "Harvest completed" message at the end
```

That's it! Your database now contains **real Austrian research publications** from OpenAIRE.

## Step 4: Start the API Server (1 minute)

```bash
# In the same terminal, start the API
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
Uvicorn running on http://0.0.0.0:8000
Press CTRL+C to quit
```

## Step 5: Explore the Results (5 minutes)

### Option A: Interactive API Documentation

Open your browser to:
```
http://localhost:8000/docs
```

Click on any endpoint and press "Try it out" to see live results!

### Option B: Command Line (curl)

```bash
# Open new terminal (keep API running in first one!)
# Don't activate venv, just use regular terminal

# Search publications
curl "http://localhost:8000/api/publications?q=artificial+intelligence&limit=5"

# Get University of Vienna info
curl "http://localhost:8000/api/organizations/03prydq77"

# Get statistics
curl "http://localhost:8000/api/publications/stats/overview"

# Compare universities
curl "http://localhost:8000/api/organizations/compare?org_ids=03prydq77,05qghxh33"
```

### Option C: Browser

Visit these URLs directly in your browser:

- **Organization List**: http://localhost:8000/api/organizations
- **Search Publications**: http://localhost:8000/api/publications?q=machine%20learning&limit=10
- **Publication Stats**: http://localhost:8000/api/publications/stats/overview
- **API Docs**: http://localhost:8000/docs

## What You Now Have

✅ **Working API** with full-text search across Austrian research
✅ **Real Data** from OpenAIRE (University of Vienna publications)
✅ **Organization Browsing** - explore research by institution
✅ **Statistics** - see publication trends by year and type
✅ **REST API** - machine-readable access to all data
✅ **Auto Documentation** - interactive Swagger UI at `/docs`

## Next Steps

### Show Stakeholders (Demo Mode)

```bash
# Keep API running and share the link
# http://localhost:8000/docs

# They can:
# 1. Explore endpoints by clicking them
# 2. Click "Try it out"
# 3. See real Austrian research data
# 4. Download results
```

### Harvest More Data

```bash
# Harvest all 15 Austrian universities (30 minutes, ~100K+ publications)
python scripts/harvest_openaire.py

# Or specific organizations
python scripts/harvest_openaire.py --single "05qghxh33"  # TU Wien
python scripts/harvest_openaire.py --single "00rbhpj83"  # JKU Linz
```

### Build Web Interface (Phase 1c)

```bash
# Coming soon: web UI for non-technical users
# For now, use the API documentation at /docs
```

## Troubleshooting

### "Python not found"
Make sure Python 3.11+ is installed:
```bash
python --version  # Should be 3.11 or higher
```

### "ModuleNotFoundError"
Ensure virtual environment is active:
```bash
source venv/bin/activate
```

### "API won't start"
Port 8000 might be in use. Try different port:
```bash
python -m uvicorn app.main:app --reload --port 8001
```

### Harvest taking too long
Reduce records or disable logs:
```bash
python scripts/harvest_openaire.py --max-records 100 > /dev/null 2>&1
```

## Data Included

After harvesting 500 records from University of Vienna:

- **Publications**: ~500 research outputs
- **Years covered**: 1995 - 2024
- **Types**: Articles, books, datasets, software, etc.
- **Data sources**: OpenAIRE aggregated repositories
- **Fields**: Title, abstract, authors, DOI, publication date, open access status

## System Information

- **Database**: SQLite (located at `data/armp.db`)
- **API Framework**: FastAPI (auto-documentation at `/docs`)
- **Language**: Python 3.11+
- **Storage**: ~50 MB per 100,000 publications

## What's Next

This is **Phase 1** of the implementation. The roadmap includes:

| Phase | Timeline | Features |
|-------|----------|----------|
| **Phase 1** | ✅ Complete | OpenAIRE harvesting, basic API, search |
| **Phase 1c** | Next | Web UI with Tailwind CSS |
| **Phase 1d** | Week 1-2 | Deploy to Railway/Render (public URL) |
| **Phase 2** | Week 2-3 | Crossref enrichment, researcher profiles |
| **Phase 3** | Week 3-4 | FWF projects, advanced analytics |

## Tips for Demo

1. **Narrow searches** for impressive results:
   - `?q=quantum+computing` - Show cutting-edge research
   - `?year_from=2023` - Show recent publications
   - `?open_access=true` - Highlight open science

2. **Compare organizations** to show research diversity:
   - University of Vienna vs TU Wien
   - Technical universities vs medical universities

3. **Share the API endpoint** with others:
   - `/docs` link works from any browser
   - Colleagues can explore without installing anything

## Key Points to Mention

- ✅ Uses **open APIs only** (no special permissions needed)
- ✅ **Real Austrian research** from OpenAIRE
- ✅ **No proprietary data** - all publicly accessible
- ✅ **Scalable architecture** - ready for PostgreSQL and production
- ✅ **Week 1 MVP** - shows technical feasibility rapidly
- ✅ **Open source** - code on GitHub, MIT license

## Questions?

- Check logs: `cat harvest.log`
- API docs: http://localhost:8000/docs
- Developer guide: Read `DEVELOPMENT.md`

---

**You now have a working Austrian Research Metadata Platform!** 🎉

Estimated total time: 15 minutes
Data sources: OpenAIRE (pre-aggregated Austrian research)
Next: Deploy to web (Phase 1c)
