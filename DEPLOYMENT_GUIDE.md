# Austrian Research Metadata Platform - Deployment Guide

## Quick Start (Local Testing)

### Prerequisites
- Python 3.13+
- pip/venv

### Installation

```bash
cd /Users/Missbach/Desktop/claude/meta
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Locally

```bash
# Start the development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Or for production-like testing
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open: **http://localhost:8000**

### Verify It Works

```bash
# Test homepage (should return HTML)
curl http://localhost:8000/ | grep -i "ARMP\|Austrian"

# Test API health check
curl http://localhost:8000/health

# Test API docs
curl http://localhost:8000/docs
```

## Accessing the Platform

Once running, you'll see:

- **Homepage**: `http://localhost:8000/` - Beautiful Jinja2-rendered homepage
- **Search**: `http://localhost:8000/search` - Publication search interface
- **Organizations**: `http://localhost:8000/organizations` - Organization listing
- **Analytics**: `http://localhost:8000/analytics` - Analytics dashboard
- **About**: `http://localhost:8000/about` - About page with full HTML
- **API Docs**: `http://localhost:8000/docs` - Interactive Swagger UI
- **ReDoc Docs**: `http://localhost:8000/redoc` - Alternative API documentation

## Production Deployment (Railway/Cloud)

### 1. Push to GitHub

```bash
cd /Users/Missbach/Desktop/claude/meta
git push origin main
```

### 2. Connect to Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### 3. Environment Variables

Set in Railway Dashboard:

```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host/armp
CORS_ORIGINS=https://your-domain.railway.app
LOG_LEVEL=INFO
```

### 4. Verify Deployment

```bash
curl https://your-app.railway.app/
curl https://your-app.railway.app/health
curl https://your-app.railway.app/docs
```

## Security Checklist

✅ **CORS Protection**
- Only specific origins allowed (configured via environment variable)
- No `allow_origins=["*"]` wildcard

✅ **Security Headers**
- X-Frame-Options: DENY (prevents clickjacking)
- X-Content-Type-Options: nosniff (prevents MIME sniffing)
- X-XSS-Protection: 1; mode=block (XSS protection)
- Referrer-Policy: strict-origin-when-cross-origin
- Content-Security-Policy: comprehensive policy
- HSTS: Enabled in production

✅ **Input Validation**
- All search filters have max_length constraints
- Year ranges restricted to 1800-2100
- Query strings limited to 500 characters
- Prevents DOS attacks

✅ **Database**
- SQLAlchemy with parameterized queries (SQL injection proof)
- SQLite for development, PostgreSQL for production
- Proper schema initialization

✅ **Routing**
- Web routes separate from API routes
- Jinja2 templates properly initialized at module level
- No template injection vulnerabilities

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Database Issues
```bash
# Reset database
rm -f data/armp.db
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Missing Dependencies
```bash
pip install -r requirements.txt
# If specific package fails, install individually:
pip install sqlalchemy==2.0.23
pip install fastapi==0.104.1
```

### CORS Errors
```bash
# Update CORS_ORIGINS in .env or environment:
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://your-domain.com
```

## Performance Optimization

### Caching (Future Enhancement)
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function():
    # Implementation
    pass
```

### Database Indexing (Already Implemented)
- Organization: `ror_id` indexed
- Publication: `doi` indexed for fast lookup
- Researcher: `orcid_id` indexed

### Query Optimization
- Use `Session.query().filter()` with indexed columns
- Pagination implemented (limit/offset)
- Full-text search ready with `fuzzywuzzy`

## API Endpoints

### Publications
- `GET /api/publications` - List publications
- `GET /api/publications/{id}` - Get publication details
- `POST /api/publications/search` - Search publications

### Organizations
- `GET /api/organizations` - List organizations
- `GET /api/organizations/{id}` - Get organization details

### Researchers
- `GET /api/researchers` - List researchers
- `GET /api/researchers/{id}` - Get researcher profile

### Analytics
- `GET /api/analytics/statistics` - Platform statistics
- `GET /api/analytics/organizations/{id}` - Organization statistics

### Web UI
- `GET /` - Homepage
- `GET /search` - Search page
- `GET /organizations` - Organizations page
- `GET /organizations/{id}` - Organization detail
- `GET /analytics` - Analytics dashboard
- `GET /about` - About page

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "timestamp": "2025-10-23T10:00:00"
}
```

### Logs
```bash
# View logs
tail -f /var/log/armp.log

# Or from stdout if running in foreground
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Support

For issues or questions:
- Check `SECURITY_FIXES_COMPLETE.md` for security details
- Review `FINAL_STATUS.md` for implementation status
- All code is fully documented inline

---

**Status**: Production Ready ✅
**Last Updated**: October 23, 2025
**Version**: 0.1.0
