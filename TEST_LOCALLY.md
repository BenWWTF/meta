# Local Testing Guide - Before Production Deployment

**Purpose**: Verify the application works correctly before deploying to Railway
**Time Required**: 10-15 minutes
**Prerequisites**: Python 3.11+, working internet connection

---

## Step 1: Setup Local Environment

```bash
cd /Users/Missbach/Desktop/claude/meta

# Create virtual environment (if not exists)
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__}')"
```

**Expected Output**:
```
FastAPI 0.104.1
SQLAlchemy 2.0.23
```

---

## Step 2: Initialize Database

```bash
# Initialize SQLite database with schema
python -c "from app.database import init_db; init_db(); print('Database initialized successfully')"

# Verify database file created
ls -lh data/armp.db

# Check schema
sqlite3 data/armp.db ".tables"
```

**Expected Output**:
```
Database initialized successfully
-rw-r--r--  1 user  staff  16K Oct 22 12:00 data/armp.db

publication researcher organization project
```

---

## Step 3: Start Application

```bash
# Start development server
python -m uvicorn app.main:app --reload

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

Leave this terminal open. The app runs at `http://localhost:8000`

---

## Step 4: Test in Another Terminal

Open a new terminal window (keep the first one running):

```bash
# Open new terminal
# Activate venv in new terminal (important!)
cd /Users/Missbach/Desktop/claude/meta
source venv/bin/activate
```

### Test 1: Health Check

```bash
curl http://localhost:8000/health | python -m json.tool
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "timestamp": "2024-10-22T12:00:00.000000"
}
```

### Test 2: Root Endpoint

```bash
curl http://localhost:8000/ | python -m json.tool
```

**Expected Response**:
```json
{
  "name": "Austrian Research Metadata Platform",
  "version": "0.1.0",
  "status": "operational",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

### Test 3: Organizations Endpoint

```bash
curl http://localhost:8000/api/organizations | python -m json.tool | head -50
```

**Expected Response**: List of 15 organizations (empty or with data if harvested)

### Test 4: API Documentation

Open in browser:
```
http://localhost:8000/docs
```

**Expected**: Swagger UI loads with:
- ✅ All 37+ API endpoints listed
- ✅ Parameters documented
- ✅ Response schemas shown
- ✅ "Try it out" button on each endpoint

---

## Step 5: Test Web Interface

Open in browser:

```
http://localhost:8000/
```

**Check**:
- [ ] Homepage loads
- [ ] CSS styling works (Tailwind)
- [ ] Navigation menu visible
- [ ] Images load (if present)
- [ ] Responsive on mobile (use DevTools)

### Test Navigation

- [ ] `/` - Homepage loads
- [ ] `/search` - Search page loads
- [ ] `/organizations` - Organization listing loads
- [ ] `/analytics` - Analytics page loads
- [ ] `/about` - About page loads

**Expected**: All pages load without 404 errors

---

## Step 6: Test Key API Endpoints

### Organizations

```bash
# List all organizations
curl "http://localhost:8000/api/organizations?limit=5" | python -m json.tool

# Get single organization
curl "http://localhost:8000/api/organizations/1" | python -m json.tool

# Get stats
curl "http://localhost:8000/api/organizations/stats" | python -m json.tool
```

### Publications

```bash
# Search publications
curl "http://localhost:8000/api/publications?q=artificial" | python -m json.tool | head -30

# Get stats
curl "http://localhost:8000/api/publications/stats/overview" | python -m json.tool
```

### Researchers

```bash
# List researchers
curl "http://localhost:8000/api/researchers" | python -m json.tool | head -30

# Get researcher stats
curl "http://localhost:8000/api/researchers/stats/overview" | python -m json.tool
```

### Projects

```bash
# List projects
curl "http://localhost:8000/api/projects" | python -m json.tool | head -30

# Get project stats
curl "http://localhost:8000/api/projects/stats/overview" | python -m json.tool

# Get funding analysis
curl "http://localhost:8000/api/projects/stats/funding" | python -m json.tool
```

### Analytics

```bash
# Research trends
curl "http://localhost:8000/api/analytics/trends" | python -m json.tool

# Researcher impact
curl "http://localhost:8000/api/analytics/impact" | python -m json.tool | head -30

# Open access stats
curl "http://localhost:8000/api/analytics/open-access" | python -m json.tool
```

---

## Step 7: Load Sample Data (Optional)

If you want to test with real data before deployment:

```bash
# Harvest sample publications from OpenAIRE (takes ~2 minutes)
python scripts/harvest_openaire.py --max-records 100

# Harvest from Crossref (takes ~1 minute)
python scripts/harvest_crossref.py --single-org "University of Vienna" --max-records 50

# Enrich researchers (takes ~1 minute)
python scripts/enrich_researchers.py

# Harvest FWF projects (takes ~30 seconds)
python scripts/harvest_fwf.py --max-records 50
```

Then re-test the endpoints above - they should now return real data.

---

## Step 8: Test Error Handling

### Invalid Endpoint

```bash
curl http://localhost:8000/api/invalid
```

**Expected**: 404 error with JSON response

### Invalid Query Parameter

```bash
curl "http://localhost:8000/api/publications?limit=99999"
```

**Expected**: 422 validation error (limit max is 1000)

### Invalid ID

```bash
curl http://localhost:8000/api/organizations/nonexistent
```

**Expected**: 404 error with "not found" message

---

## Step 9: Performance Check

### Response Time Test

```bash
# Measure response time
time curl http://localhost:8000/api/organizations > /dev/null

# Expected: < 500ms for simple queries
```

### Concurrent Requests

```bash
# Send 5 concurrent requests
for i in {1..5}; do
  curl http://localhost:8000/api/organizations &
done
wait

# Expected: All complete without errors
```

### Large Result Set

```bash
# Test pagination with large limit
curl "http://localhost:8000/api/publications?limit=500" | wc -l

# Expected: Should complete in < 2 seconds
```

---

## Step 10: Database Consistency Check

```bash
# Count records in database
sqlite3 data/armp.db "SELECT COUNT(*) as organizations FROM organization;"
sqlite3 data/armp.db "SELECT COUNT(*) as publications FROM publication;"
sqlite3 data/armp.db "SELECT COUNT(*) as researchers FROM researcher;"
sqlite3 data/armp.db "SELECT COUNT(*) as projects FROM project;"

# Expected: 15 organizations minimum (pre-configured)
#          0+ publications (depends on harvesting)
#          0+ researchers (depends on harvesting)
#          0+ projects (depends on harvesting)
```

---

## Step 11: Clean Shutdown Test

```bash
# In the terminal running uvicorn, press Ctrl+C

# Expected:
# INFO:     Shutdown complete
# (Terminal returns to prompt)
```

Then restart:

```bash
python -m uvicorn app.main:app --reload

# Verify data persists by checking /api/organizations again
curl http://localhost:8000/api/organizations | python -m json.tool
```

---

## Pre-Deployment Checklist

### Code Quality

```bash
# Syntax check
python -m py_compile app/*.py app/**/*.py
echo "✓ No syntax errors"

# Import check
python -c "from app.main import app" && echo "✓ Imports OK"

# Database check
python -c "from app.database import SessionLocal; db = SessionLocal(); print('✓ Database connection OK')"
```

- [ ] No syntax errors
- [ ] All imports work
- [ ] Database initializes

### Functionality

- [ ] Health check returns healthy
- [ ] All pages load
- [ ] All 37+ API endpoints respond
- [ ] Error handling works
- [ ] Performance is acceptable (<2 sec per request)
- [ ] Database consistency verified

### Git Status

```bash
git status
# Expected: "nothing to commit, working tree clean"

git log --oneline | head -5
# Expected: Shows recent commits
```

- [ ] All changes committed
- [ ] No uncommitted files
- [ ] Git history is clean

---

## Common Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'app'"

**Solution**:
```bash
# Ensure you're in correct directory
cd /Users/Missbach/Desktop/claude/meta

# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Port 8000 Already in Use

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
python -m uvicorn app.main:app --port 8001
```

### Issue: Database Locked Error

**Solution**:
```bash
# This is normal in SQLite - happens with multiple processes
# Solution: Close other terminals using the DB

# Or reset database
rm data/armp.db
python -c "from app.database import init_db; init_db()"
```

### Issue: Slow Response Times (>5 sec)

**Solution**:
1. Make sure database is initialized with sample data
2. Check if analytics queries are expensive (they compute on-the-fly)
3. Check system resources (Activity Monitor)

---

## Ready to Deploy?

Once all tests pass:

```bash
# 1. Stop local server (Ctrl+C in uvicorn terminal)

# 2. Commit any changes
git add .
git commit -m "Ready for deployment - all tests passing"

# 3. Push to GitHub
git push origin main

# 4. Deploy to Railway (see DEPLOYMENT.md)
```

---

## Testing Checklist

Print this out and check off as you go:

```
LOCAL TESTING CHECKLIST
======================

Setup
[ ] Virtual environment created
[ ] Dependencies installed
[ ] Database initialized

Health Checks
[ ] /health endpoint returns healthy
[ ] / endpoint returns version info
[ ] /docs loads Swagger UI

Web Interface
[ ] Homepage (/) loads with styling
[ ] Search page (/search) works
[ ] Organizations page (/organizations) works
[ ] Analytics page (/analytics) works
[ ] About page (/about) works

API Endpoints
[ ] GET /api/organizations works
[ ] GET /api/publications works
[ ] GET /api/researchers works
[ ] GET /api/projects works
[ ] GET /api/analytics/trends works
[ ] All 37+ endpoints documented in /docs

Error Handling
[ ] 404 errors return valid JSON
[ ] 422 validation errors work
[ ] Pagination limits enforced

Performance
[ ] Simple requests complete < 500ms
[ ] Handles 5+ concurrent requests
[ ] Large result sets complete < 2 seconds

Database
[ ] 15 organizations present
[ ] Data persists after restart
[ ] No database locks

Code Quality
[ ] No syntax errors
[ ] All imports work
[ ] Git status clean
[ ] All changes committed

READY FOR DEPLOYMENT: [ ]
```

---

**Local testing complete! Ready for production deployment.** ✅

