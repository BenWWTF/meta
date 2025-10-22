# Austrian Research Metadata Platform - Deployment Checklist

**Status**: Phase 1d - Ready for Production Deployment
**Last Updated**: October 2024
**Estimated Deployment Time**: 30-45 minutes

---

## Pre-Deployment Requirements

### Local Environment Verification

- [ ] Python 3.11+ installed (`python --version`)
- [ ] Git initialized and commits present (`git log`)
- [ ] GitHub account created
- [ ] Railway.app account created (or Render.com)
- [ ] All code committed (`git status` shows clean)
- [ ] Requirements.txt up to date (`pip freeze > requirements.txt`)

### Code Quality Checks

```bash
# Run from /Users/Missbach/Desktop/claude/meta

# Check for syntax errors
python -m py_compile app/*.py app/**/*.py

# Lint check (optional)
flake8 app --max-line-length=120 || true

# Format check (optional)
black --check app || true
```

- [ ] No Python syntax errors
- [ ] No import errors (`python -c "from app.main import app"`)
- [ ] Database initializes without errors (`python -c "from app.database import init_db; init_db()"`)

### File Structure Verification

```bash
# Verify essential files exist
ls -la app/main.py
ls -la app/database.py
ls -la app/schemas.py
ls -la app/api/publications.py
ls -la app/api/organizations.py
ls -la app/api/researchers.py
ls -la app/api/projects.py
ls -la app/api/analytics.py
ls -la Procfile
ls -la runtime.txt
ls -la Dockerfile
ls -la requirements.txt
```

- [ ] All API modules present
- [ ] Procfile exists
- [ ] Dockerfile exists
- [ ] requirements.txt exists

---

## GitHub Preparation

### Step 1: Create GitHub Repository

```bash
# Create repo on github.com: austrian-research-metadata

# In your project directory:
cd /Users/Missbach/Desktop/claude/meta

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/austrian-research-metadata.git

# Verify remote
git remote -v
```

- [ ] GitHub repository created
- [ ] Remote URL set correctly
- [ ] SSH or HTTPS access working (`git push -u origin main`)

### Step 2: Push Code to GitHub

```bash
# Ensure everything is committed
git status  # Should show "nothing to commit"

# Push to main branch
git branch -M main
git push -u origin main

# Verify on GitHub
# Visit: https://github.com/YOUR_USERNAME/austrian-research-metadata
# Should see all files
```

- [ ] Code pushed to GitHub
- [ ] All files visible on GitHub repository
- [ ] Latest commit shows in repo history

---

## Railway Deployment

### Step 1: Connect GitHub to Railway

1. [ ] Go to https://railway.app
2. [ ] Sign in or create account
3. [ ] Click "Create New Project"
4. [ ] Select "Deploy from GitHub"
5. [ ] Click "Authorize" and grant Railway access to GitHub
6. [ ] Select your `austrian-research-metadata` repository

### Step 2: Configure Build Settings

Railway should auto-detect:
- [ ] Python runtime (3.11 from runtime.txt)
- [ ] Build command (pip install -r requirements.txt)
- [ ] Start command (from Procfile)

If not auto-detected, manually set:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Set Environment Variables

In Railway dashboard → Project → Variables:

```
DATABASE_URL=sqlite:///./data/armp.db
ENVIRONMENT=production
LOG_LEVEL=info
PYTHONUNBUFFERED=1
```

- [ ] DATABASE_URL configured
- [ ] ENVIRONMENT set to production
- [ ] LOG_LEVEL set appropriately

### Step 4: Deploy

**Option A: Automatic Deployment**
```bash
# Push to GitHub (Railway automatically deploys)
git push origin main
```

**Option B: Manual Deployment**
- Go to Railway dashboard → Project
- Click "Deploy" button
- Wait for build to complete (2-3 minutes)

- [ ] Deployment triggered
- [ ] Build completes without errors
- [ ] Public URL generated

### Step 5: Verify Deployment

```bash
# Get your public URL from Railway dashboard
# Format: https://your-project-name.up.railway.app

# Test endpoints
curl https://your-project-name.up.railway.app/health
curl https://your-project-name.up.railway.app/
curl https://your-project-name.up.railway.app/api/organizations

# View logs
# Railway Dashboard → Logs tab
```

- [ ] App responds to requests (HTTP 200)
- [ ] Health check endpoint returns status="healthy"
- [ ] API endpoints return JSON responses
- [ ] Web interface loads (visit in browser)
- [ ] No errors in logs

---

## Post-Deployment Verification

### Essential Endpoints

Test each endpoint to verify functionality:

```bash
BASE_URL=https://your-project-name.up.railway.app

# Health & Info
curl $BASE_URL/health
curl $BASE_URL/

# Web Interface
# Visit: $BASE_URL/
# Check: Homepage loads, styling works, responsive

# Organizations
curl "$BASE_URL/api/organizations"
curl "$BASE_URL/api/organizations" | jq '.'

# Publications
curl "$BASE_URL/api/publications?limit=5"
curl "$BASE_URL/api/publications/stats/overview"

# Researchers
curl "$BASE_URL/api/researchers?limit=5"
curl "$BASE_URL/api/researchers/stats/overview"

# Projects
curl "$BASE_URL/api/projects?limit=5"
curl "$BASE_URL/api/projects/stats/overview"

# Analytics
curl "$BASE_URL/api/analytics/trends"
curl "$BASE_URL/api/analytics/impact?limit=5"

# API Docs
# Visit: $BASE_URL/docs
# Check: Swagger UI loads, interactive documentation works
```

### Functionality Checklist

- [ ] Homepage (`/`) loads with styling
- [ ] Search page (`/search`) works
- [ ] Organizations page (`/organizations`) lists institutions
- [ ] Organization detail page loads
- [ ] Analytics page (`/analytics`) shows charts
- [ ] API docs (`/docs`) loads with Swagger UI
- [ ] All API endpoints return 200 status
- [ ] JSON responses are valid and formatted
- [ ] Health check returns healthy status
- [ ] Root endpoint shows version info

### Database Status

Check if database has data or needs initial harvest:

```bash
# Option 1: Via API (check record counts)
curl https://your-project-name.up.railway.app/api/organizations | jq '.results | length'

# Option 2: SSH into Railway container and check
# (From Railway dashboard: click container, open "Shell" tab)
# Then:
# python -c "from app.database import SessionLocal, Publication; db = SessionLocal(); print(f'Publications: {db.query(Publication).count()}')"
```

- [ ] Database initialized (tables exist)
- [ ] Organization records present (at least 15)
- [ ] Sample data loaded (optional for initial deployment)

---

## Load Initial Data (Optional)

If deploying with empty database, you can load sample data:

### Option 1: Via Shell Access

```bash
# In Railway: click container → Shell tab

# Initialize database
python -c "from app.database import init_db; init_db()"

# Load sample data (small harvest)
python scripts/harvest_openaire.py --max-records 100
python scripts/harvest_crossref.py --max-records 100
python scripts/harvest_fwf.py --max-records 50

# This takes ~5-10 minutes
```

- [ ] Database initialized
- [ ] Sample publications loaded
- [ ] Sample organizations configured
- [ ] Sample researchers extracted

### Option 2: Deploy with Data

If you have harvested data locally in `data/armp.db`:
1. Commit database file to Git (not ideal but works for MVP)
2. Or: Deploy with empty DB, harvest in production via shell access

---

## Custom Domain Setup (Optional)

### Railway Custom Domain

1. [ ] Domain purchased (or use free option first)
2. [ ] In Railway dashboard: Project → Domains
3. [ ] Add your domain
4. [ ] Follow Railway instructions for DNS CNAME
5. [ ] Wait for DNS propagation (5-30 minutes)
6. [ ] Test at custom domain

### Example: `research.example.at`

```bash
# After DNS configured:
curl https://research.example.at/health
```

---

## Monitoring & Alerts

### Enable Railway Monitoring

- [ ] Check Railway dashboard for:
  - [ ] Memory usage (should be <500MB)
  - [ ] CPU usage (should be <20% at rest)
  - [ ] Request count
  - [ ] Response times
  - [ ] Error rates

### Set Up Basic Alerts

In Railway dashboard → Settings:
- [ ] Enable deployment notifications
- [ ] Monitor build failures
- [ ] Check logs for errors

### View Logs

```bash
# Railway: Dashboard → Logs tab
# Look for:
# ✓ "Uvicorn running on 0.0.0.0:8000"
# ✗ No "ERROR" or "CRITICAL" messages
# ✗ No "Connection refused" errors
```

---

## Sharing & Stakeholder Access

### Share Public URL

```
📧 Subject: Austrian Research Metadata Platform MVP - Live Demo

Hi Team,

The ARMP MVP is now live! Access it here:

🌐 Public URL: https://your-project-name.up.railway.app

Key Features:
✅ Search 100K+ Austrian research publications
✅ Browse 15+ Austrian universities
✅ Explore researcher profiles with ORCID
✅ Analyze funding impact and ROI
✅ View research trends and analytics

Try It Out:
🔗 Homepage: https://your-project-name.up.railway.app/
🔍 Search: https://your-project-name.up.railway.app/search
📊 Analytics: https://your-project-name.up.railway.app/analytics
📚 API Docs: https://your-project-name.up.railway.app/docs

Questions or feedback? Let me know!

Best regards,
[Your Name]
```

- [ ] Stakeholders have public URL
- [ ] Access is working for all users
- [ ] Initial feedback collected

---

## Rollback Plan

If deployment has issues:

### Quick Rollback

```bash
# Revert last commit (if it broke something)
git revert HEAD
git push origin main

# Railway auto-deploys, reverting to previous version
```

### Manual Rollback

1. [ ] In Railway dashboard, go to Deployments
2. [ ] Find last working deployment
3. [ ] Click "Redeploy"

### Check Logs for Issues

```bash
# Railway Dashboard → Logs
# Look for:
- Import errors (ModuleNotFoundError)
- Database errors (sqlite3.DatabaseError)
- Connection errors (HTTPError, ConnectionError)
- Syntax errors (SyntaxError)
```

---

## Performance Baseline

After deployment, check baseline performance:

```bash
# Response time test (should be <1 second)
time curl https://your-project-name.up.railway.app/api/organizations

# Concurrent requests test (should handle 5-10 concurrent)
for i in {1..5}; do
  curl https://your-project-name.up.railway.app/health &
done
wait

# Database query performance
curl "https://your-project-name.up.railway.app/api/publications?limit=100"
# Should return in <2 seconds
```

- [ ] API responses < 1 second
- [ ] Handles concurrent requests
- [ ] Database queries perform acceptably

---

## Next Steps Post-Deployment

### Immediate (Today)
- [ ] Verify all endpoints working
- [ ] Share URL with stakeholders
- [ ] Collect initial feedback

### This Week (Phase 3c)
- [ ] Migrate to PostgreSQL for scalability
- [ ] Run full data harvest (100K+ publications)
- [ ] Enable caching for performance
- [ ] Set up monitoring/alerting

### Next 2 Weeks (QA & Launch)
- [ ] Security audit
- [ ] Performance optimization
- [ ] Load testing
- [ ] User acceptance testing

---

## Troubleshooting

### App Won't Start

**Symptoms**: Deployment succeeds but app doesn't respond

**Check**:
1. Railway Logs: Look for startup errors
2. Environment variables: Verify DATABASE_URL is set
3. Python version: Must be 3.9+

**Fix**:
```bash
# Check Procfile content
cat Procfile
# Should show: web: uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Check Python dependencies
pip install -r requirements.txt

# Test locally first
python -m uvicorn app.main:app --reload
```

### Import Errors

**Symptoms**: "ModuleNotFoundError: No module named 'app'"

**Check**:
1. Verify `app/__init__.py` exists
2. Check requirements.txt has all dependencies

**Fix**:
```bash
# Ensure __init__.py exists
touch app/__init__.py

# Commit and push
git add app/__init__.py
git commit -m "Add missing __init__.py"
git push origin main
```

### Database Errors

**Symptoms**: "sqlite3.OperationalError: database is locked"

**Check**:
1. Multiple app instances trying to access SQLite
2. Railway auto-scales - SQLite doesn't handle multiple processes

**Fix** (for production):
1. Migrate to PostgreSQL (Phase 3c)
2. Or: Set Railway replicas to 1 (free tier default)

### Slow Performance

**Symptoms**: API calls take >5 seconds

**Check**:
1. Railway logs for error patterns
2. Database query count (N+1 queries?)
3. Memory usage (if high, increase plan)

**Fix**:
```bash
# Temporarily disable analytics (computationally expensive)
# Or: Add indices to frequently queried columns
# Or: Upgrade Railway plan for more resources
```

---

## Success Indicators

### Deployment is Successful When:

✅ Public URL is live and accessible
✅ All endpoints respond with correct data
✅ Web interface loads with styling
✅ API documentation (/docs) works
✅ No errors in logs for 5 minutes
✅ Response times are <2 seconds
✅ Stakeholders can access and use the platform
✅ Health check endpoint returns healthy status

### You're Ready for Next Phase When:

✅ Deployment is stable for 24+ hours
✅ Initial stakeholder feedback is positive
✅ All critical endpoints verified
✅ Database has initial data loaded
✅ Monitoring is configured
✅ Rollback plan is understood

---

## Deployment Summary

| Task | Time | Status |
|------|------|--------|
| Code quality checks | 5 min | ✅ |
| GitHub repository setup | 5 min | ⏳ |
| Push code to GitHub | 3 min | ⏳ |
| Create Railway account | 2 min | ⏳ |
| Connect GitHub to Railway | 3 min | ⏳ |
| Configure environment vars | 2 min | ⏳ |
| Deploy to Railway | 3-5 min | ⏳ |
| Verify endpoints | 5 min | ⏳ |
| Share URL with stakeholders | 2 min | ⏳ |
| **Total** | **~30 min** | ⏳ |

---

**Your MVP is ready to shine! 🚀**

