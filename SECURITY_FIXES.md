# Security Issues - Detailed Fixes

This document provides step-by-step remediation for all security findings identified in SECURITY_AUDIT.md

---

## FIX 1: CORS Wildcard Configuration (HIGH PRIORITY)

**File**: `app/main.py`
**Lines**: 52-58
**Severity**: HIGH

### Step 1: Update CORS Configuration

**BEFORE** (Current - Insecure):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ INSECURE
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**AFTER** (Fixed - Secure):
```python
from fastapi.middleware.cors import CORSMiddleware
import os

# Get allowed origins from environment variable
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8000"
).split(",")

# PRODUCTION: Only allow specific trusted domains
# DEVELOPMENT: Allow localhost for testing
CORS_ORIGINS_LIST = [origin.strip() for origin in ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_LIST,  # ✅ SECURE: Specific origins only
    allow_credentials=False,  # ✅ SECURE: Disabled unless auth implemented
    allow_methods=["GET", "POST"],  # ✅ SECURE: Only needed methods
    allow_headers=["Content-Type"],  # ✅ SECURE: Only needed headers
)
```

### Step 2: Update Environment Configuration

**File**: `.env.example`

**BEFORE**:
```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

**AFTER**:
```env
# CORS Configuration - Comma-separated list of allowed origins
# LOCAL: http://localhost:3000,http://localhost:8000
# PRODUCTION: https://your-domain.com
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Step 3: Update Railway Environment

1. Go to Railway Dashboard
2. Navigate to: Project → Settings → Environment
3. Add variable:
   ```
   CORS_ORIGINS=https://austrian-research-metadata.railway.app
   ```

### Step 4: Test CORS Configuration

```bash
# Test from allowed origin (should work)
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     http://localhost:8000/api/publications

# Test from disallowed origin (should fail)
curl -H "Origin: https://evil.com" \
     http://localhost:8000/api/publications
```

### Validation
```python
# In tests/test_cors.py
def test_cors_allowed_origins():
    from app.main import CORS_ORIGINS_LIST
    # Should NOT contain "*"
    assert "*" not in CORS_ORIGINS_LIST
    assert len(CORS_ORIGINS_LIST) > 0

def test_cors_credentials_disabled():
    # Credentials should only be enabled with proper auth
    # See app.main.py CORSMiddleware config
    pass
```

---

## FIX 2: Jinja2 Template Rendering (MEDIUM PRIORITY)

**File**: `app/api/web.py`
**Lines**: 29-79 (multiple routes)
**Severity**: MEDIUM

### Current Problem (Insecure)

```python
# ❌ PROBLEM: Creates new Environment every request
env = Environment(loader=FileSystemLoader("app/templates"))
template = env.get_template("index.html")
return template.render(request=request)
```

### Step 1: Update Imports

**File**: `app/api/web.py`

```python
# ❌ OLD IMPORTS
from jinja2 import Environment, FileSystemLoader

# ✅ NEW IMPORTS - FastAPI integration
from fastapi.templating import Jinja2Templates
```

### Step 2: Initialize Templates at Module Level

```python
# Add at the top of app/api/web.py, after imports
from fastapi.templating import Jinja2Templates

# Initialize once (not in every route)
templates = Jinja2Templates(directory="app/templates")
```

### Step 3: Update All Route Handlers

**BEFORE**:
```python
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage with statistics and featured organizations."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("index.html")
    return template.render(request=request)
```

**AFTER**:
```python
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage with statistics and featured organizations."""
    return templates.TemplateResponse("index.html", {"request": request})
```

### Step 4: Update All 4 Affected Routes

Apply the same pattern to:
- Line 26: `@router.get("/")`
- Line 36: `@router.get("/search")`
- Line 46: `@router.get("/analytics")`
- Line 56: `@router.get("/organizations")`

**Complete Fixed File Pattern**:

```python
"""
Web UI Endpoints
================
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, Organization, Publication

# Initialize templates once at module level
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Web UI"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage with statistics and featured organizations."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request):
    """Publication search page."""
    return templates.TemplateResponse("search.html", {"request": request})


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request):
    """Analytics and insights dashboard."""
    return templates.TemplateResponse("analytics.html", {"request": request})


@router.get("/organizations", response_class=HTMLResponse)
async def organizations_list(request: Request):
    """Organization listing page."""
    return templates.TemplateResponse("organizations.html", {"request": request})


@router.get("/organizations/{org_id}", response_class=HTMLResponse)
async def organization_detail(
    org_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Organization detail page."""
    org = db.query(Organization).filter(Organization.id == org_id).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return templates.TemplateResponse(
        "organization_detail.html",
        {"request": request, "organization": org}
    )
```

### Step 5: Test Template Rendering

```bash
# Start server
python -m uvicorn app.main:app --reload

# Test routes
curl http://localhost:8000/
curl http://localhost:8000/search
curl http://localhost:8000/analytics
curl http://localhost:8000/organizations
```

---

## FIX 3: Add Security Headers (MEDIUM PRIORITY)

**File**: `app/main.py`
**Location**: Add middleware configuration
**Severity**: MEDIUM

### Step 1: Add Security Headers Middleware

```python
# Add after CORS middleware in app/main.py

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Prevent browsers from guessing MIME type
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Enable browser XSS filters
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content Security Policy (CSP)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdn.plot.ly; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' https: data:; "
        "font-src 'self' https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # HSTS (only in production)
    if os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response
```

### Step 2: Add Required Import

```python
from fastapi import Request  # Already imported
from starlette.middleware.base import BaseHTTPMiddleware
import os
```

### Step 3: Test Headers

```bash
# Check headers are present
curl -i http://localhost:8000/

# Expected output:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Referrer-Policy: strict-origin-when-cross-origin
# Content-Security-Policy: ...
```

---

## FIX 4: Environment Variables Security (LOW PRIORITY)

**File**: `.env.example`
**Severity**: LOW

### Update File

```env
# ⚠️ SECURITY WARNING: Never commit actual secrets to version control
# These are examples only. Real values should be set in production environment.

# Application Configuration
APP_ENV=development
DEBUG=false
SECRET_KEY=CHANGE_IN_PRODUCTION_USE_STRONG_RANDOM_VALUE

# Database
DATABASE_URL=sqlite:///./data/armp.db
# For PostgreSQL (production):
# DATABASE_URL=postgresql://user:password@hostname:5432/armp

# API Settings
API_TITLE="Austrian Research Metadata Platform"
API_VERSION="0.1.0"
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# External APIs
OPENAIRE_API_URL=https://api.openaire.eu/graph
CROSSREF_API_URL=https://api.crossref.org
ORCID_API_URL=https://pub.orcid.org/v3.0
DATACITE_API_URL=https://api.datacite.org

# Email Configuration (for future use)
# Set these values in Railway Environment, not in .env file
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@example.com
# SMTP_PASSWORD=your-password

# Harvesting Settings
HARVEST_BATCH_SIZE=1000
HARVEST_TIMEOUT_SECONDS=30
HARVEST_WORKERS=5

# Redis (optional - for caching)
# REDIS_URL=redis://localhost:6379/0

# Sentry (optional - for error tracking)
# SENTRY_DSN=

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Add Documentation

Create `SECURITY.md` with:

```markdown
# Security Configuration

## Environment Variables

### Development
Set values in `.env` file (never commit real secrets)

### Production (Railway)
Set values in Railway Dashboard:
1. Go to Project → Settings → Environment
2. Add the following variables:
   - DATABASE_URL (PostgreSQL URL)
   - SECRET_KEY (random 32+ character string)
   - CORS_ORIGINS (production domain)
   - API_KEY (if implementing authentication)

### Secret Generation
```python
import secrets
# Generate a secure SECRET_KEY
secret = secrets.token_urlsafe(32)
print(secret)
```

---

## FIX 5: Add Input Validation Constraints (MEDIUM PRIORITY)

**File**: `app/schemas.py`
**Severity**: MEDIUM (Defense in depth)

### Update SearchFilters Schema

**BEFORE**:
```python
class SearchFilters(BaseModel):
    """Filters for search operations"""
    query: Optional[str] = Field(None, description="Free text search query")
```

**AFTER**:
```python
from pydantic import Field, validator

class SearchFilters(BaseModel):
    """Filters for search operations"""
    query: Optional[str] = Field(
        None,
        description="Free text search query",
        max_length=500,  # Prevent DOS from huge searches
        min_length=1,
    )
    year_from: Optional[int] = Field(None, ge=1800, le=2100)
    year_to: Optional[int] = Field(None, ge=1800, le=2100)
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    @validator('year_to')
    def year_to_after_year_from(cls, v, values):
        if v and 'year_from' in values and values['year_from']:
            if v < values['year_from']:
                raise ValueError('year_to must be >= year_from')
        return v
```

---

## Implementation Checklist

- [ ] Fix 1: Update CORS configuration (15 min)
- [ ] Fix 1: Update .env.example (5 min)
- [ ] Fix 1: Test CORS behavior (10 min)
- [ ] Fix 2: Update web.py imports (5 min)
- [ ] Fix 2: Initialize templates at module level (5 min)
- [ ] Fix 2: Update all 4 route handlers (20 min)
- [ ] Fix 2: Test template rendering (10 min)
- [ ] Fix 3: Add security headers middleware (15 min)
- [ ] Fix 3: Test headers with curl (5 min)
- [ ] Fix 4: Update .env.example documentation (5 min)
- [ ] Fix 5: Add input validation constraints (10 min)
- [ ] Run tests: `pytest tests/ -v` (10 min)
- [ ] Run linter: `flake8 app/` (5 min)
- [ ] Deploy to Railway (5 min)
- [ ] Verify in production (10 min)

**Total Time**: ~3 hours

---

## Testing Security Fixes

### Unit Tests

```python
# tests/test_security.py

def test_cors_no_wildcard():
    """Verify CORS doesn't allow wildcard."""
    from app.main import CORS_ORIGINS_LIST
    assert "*" not in CORS_ORIGINS_LIST

def test_security_headers_present(client):
    """Verify security headers are added."""
    response = client.get("/")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers

def test_templates_render(client):
    """Verify templates render without errors."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Austrian" in response.text

def test_input_validation():
    """Verify input constraints work."""
    from app.schemas import SearchFilters

    # Valid
    filters = SearchFilters(query="test", limit=50)

    # Invalid - query too long
    with pytest.raises(ValidationError):
        SearchFilters(query="x" * 501)

    # Invalid - limit too high
    with pytest.raises(ValidationError):
        SearchFilters(limit=2000)
```

### Manual Testing

```bash
# Test CORS
curl -H "Origin: https://evil.com" http://localhost:8000/

# Test security headers
curl -i http://localhost:8000/ | grep -E "X-Frame|X-Content|CSP"

# Test XSS attempt
curl "http://localhost:8000/api/publications?q=<script>alert('xss')</script>"

# Test SQL injection attempt
curl "http://localhost:8000/api/publications?q=' OR '1'='1"

# Test input validation
curl "http://localhost:8000/api/publications?limit=999999"
```

---

## Deployment Steps

1. **Local Testing**:
   ```bash
   git pull origin main
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pytest tests/ -v
   python -m uvicorn app.main:app --reload
   ```

2. **Commit Changes**:
   ```bash
   git add app/main.py app/api/web.py .env.example
   git commit -m "Security: Fix CORS, template rendering, and add security headers"
   ```

3. **Deploy to Railway**:
   ```bash
   git push origin main
   # Railway auto-deploys
   ```

4. **Verify in Production**:
   ```bash
   curl -i https://your-app.railway.app/
   curl -i https://your-app.railway.app/api/publications
   ```

---

## Post-Remediation

After applying all fixes:

1. ✅ Run security audit again
2. ✅ Update SECURITY_AUDIT.md with status
3. ✅ Add security testing to CI/CD
4. ✅ Document changes in CHANGELOG
5. ✅ Inform stakeholders of improvements

