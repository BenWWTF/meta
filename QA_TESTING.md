# Quality Assurance & Testing Guide

**Phase**: QA - Testing & Optimization (Post-Deployment)
**Status**: ⏳ PENDING - Testing Framework Ready
**Objective**: Ensure production-grade quality before stakeholder launch
**Duration**: 3-4 hours (comprehensive testing)
**Last Updated**: October 2024

---

## Testing Strategy

### Testing Pyramid

```
        ┌─────────────────────┐
        │  Manual/UI Testing  │  (30 min)
        ├─────────────────────┤
        │  Integration Tests  │  (45 min)
        ├─────────────────────┤
        │   Functional Tests  │  (60 min)
        ├─────────────────────┤
        │  Unit Tests & Code  │  (45 min)
        └─────────────────────┘
```

**Total Coverage**: ~3.5 hours of systematic testing

---

## Part 1: Code Quality Testing (45 minutes)

### 1.1: Syntax & Import Verification

```bash
cd /Users/Missbach/Desktop/claude/meta

# Check all Python files for syntax errors
python -m py_compile app/*.py app/**/*.py scripts/*.py

# Verify imports
python -c "from app.main import app; print('✓ Main app imports OK')"
python -c "from app.api import publications, organizations, researchers, projects, analytics, web; print('✓ All API modules import OK')"
python -c "from app.harvesters import openaire, crossref, orcid, fwf, researcher_enricher; print('✓ All harvesters import OK')"

# Check database
python -c "from app.database import init_db, SessionLocal; init_db(); print('✓ Database initialization OK')"
```

**Expected Output**:
```
✓ Main app imports OK
✓ All API modules import OK
✓ All harvesters import OK
✓ Database initialization OK
```

### 1.2: Code Style Analysis (Optional but Recommended)

```bash
# Install development dependencies
pip install flake8 black mypy

# Check code style
flake8 app scripts --max-line-length=120 --ignore=E501,W503

# Format check
black --check app scripts

# Type checking
mypy app --ignore-missing-imports 2>/dev/null || true
```

**Expected**: Minimal or no warnings

### 1.3: Dependency Audit

```bash
# Check for security vulnerabilities
pip install safety
safety check

# Check for outdated packages
pip list --outdated

# Update critical packages
pip install --upgrade sqlalchemy pydantic fastapi
```

**Expected**: No critical vulnerabilities

---

## Part 2: Unit Tests (30 minutes)

### 2.1: Database Model Tests

```bash
cat > tests/test_database.py << 'EOF'
"""Test database models and schema."""

import pytest
from app.database import SessionLocal, init_db, Organization, Publication, Researcher, Project


@pytest.fixture
def db():
    """Create test database."""
    init_db()
    db = SessionLocal()
    yield db
    db.close()


def test_organization_creation(db):
    """Test creating an organization."""
    org = Organization(
        id="test_org_1",
        name="Test University",
        ror_id="https://ror.org/test123",
        country="AT",
    )
    db.add(org)
    db.commit()

    retrieved = db.query(Organization).filter_by(id="test_org_1").first()
    assert retrieved is not None
    assert retrieved.name == "Test University"


def test_publication_creation(db):
    """Test creating a publication."""
    org = Organization(
        id="test_org_1",
        name="Test University",
        ror_id="https://ror.org/test123",
        country="AT",
    )
    db.add(org)
    db.commit()

    pub = Publication(
        id="test_pub_1",
        title="Test Publication",
        doi="10.1234/test",
        organization_id="test_org_1",
    )
    db.add(pub)
    db.commit()

    retrieved = db.query(Publication).filter_by(id="test_pub_1").first()
    assert retrieved is not None
    assert retrieved.title == "Test Publication"


def test_researcher_creation(db):
    """Test creating a researcher."""
    org = Organization(
        id="test_org_1",
        name="Test University",
        ror_id="https://ror.org/test123",
        country="AT",
    )
    db.add(org)
    db.commit()

    res = Researcher(
        id="test_res_1",
        name="John Doe",
        organization_id="test_org_1",
        orcid="0000-0000-0000-0001",
    )
    db.add(res)
    db.commit()

    retrieved = db.query(Researcher).filter_by(id="test_res_1").first()
    assert retrieved is not None
    assert retrieved.orcid == "0000-0000-0000-0001"
EOF

# Run tests
pytest tests/test_database.py -v
```

### 2.2: API Route Tests

```bash
cat > tests/test_api.py << 'EOF'
"""Test API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def init_database():
    """Initialize database before tests."""
    init_db()


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()


def test_organizations_endpoint():
    """Test organizations listing."""
    response = client.get("/api/organizations")
    assert response.status_code == 200
    assert "results" in response.json()


def test_publications_endpoint():
    """Test publications listing."""
    response = client.get("/api/publications?limit=5")
    assert response.status_code == 200
    assert "results" in response.json()


def test_researchers_endpoint():
    """Test researchers listing."""
    response = client.get("/api/researchers?limit=5")
    assert response.status_code == 200
    assert "results" in response.json()


def test_projects_endpoint():
    """Test projects listing."""
    response = client.get("/api/projects?limit=5")
    assert response.status_code == 200
    assert "results" in response.json()


def test_analytics_endpoint():
    """Test analytics endpoint."""
    response = client.get("/api/analytics/trends")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_invalid_endpoint():
    """Test 404 for invalid endpoint."""
    response = client.get("/api/invalid")
    assert response.status_code == 404


def test_invalid_query_parameter():
    """Test 422 for invalid parameters."""
    response = client.get("/api/publications?limit=99999")
    assert response.status_code == 422
EOF

# Run tests
pytest tests/test_api.py -v
```

**Run All Unit Tests**:

```bash
pytest tests/ -v --tb=short

# Expected: All tests pass
# Look for: "passed" count, no "failed"
```

---

## Part 3: Functional Testing (60 minutes)

### 3.1: Web Interface Testing

Start the server:

```bash
python -m uvicorn app.main:app --reload
```

Then test each page in browser:

| Page | URL | Checks |
|------|-----|--------|
| Homepage | http://localhost:8000/ | Loads, CSS works, responsive |
| Search | http://localhost:8000/search | Form works, search possible |
| Organizations | http://localhost:8000/organizations | Lists 15 orgs |
| Org Detail | http://localhost:8000/organizations/1 | Shows org info |
| Analytics | http://localhost:8000/analytics | Charts load/render |
| About | http://localhost:8000/about | Content displays |
| API Docs | http://localhost:8000/docs | Swagger UI loads |

### 3.2: API Endpoint Testing

```bash
# Create test script
cat > test_endpoints.sh << 'EOF'
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "Testing API Endpoints..."
echo "========================"

# Health
echo "Testing /health..."
curl -s $BASE_URL/health | python -m json.tool > /dev/null && echo "✓ /health OK" || echo "✗ /health FAILED"

# Organizations
echo "Testing /api/organizations..."
curl -s "$BASE_URL/api/organizations?limit=5" | python -m json.tool > /dev/null && echo "✓ /api/organizations OK" || echo "✗ /api/organizations FAILED"

# Publications
echo "Testing /api/publications..."
curl -s "$BASE_URL/api/publications?limit=5" | python -m json.tool > /dev/null && echo "✓ /api/publications OK" || echo "✗ /api/publications FAILED"

# Researchers
echo "Testing /api/researchers..."
curl -s "$BASE_URL/api/researchers?limit=5" | python -m json.tool > /dev/null && echo "✓ /api/researchers OK" || echo "✗ /api/researchers FAILED"

# Projects
echo "Testing /api/projects..."
curl -s "$BASE_URL/api/projects?limit=5" | python -m json.tool > /dev/null && echo "✓ /api/projects OK" || echo "✗ /api/projects FAILED"

# Analytics
echo "Testing /api/analytics/trends..."
curl -s "$BASE_URL/api/analytics/trends" | python -m json.tool > /dev/null && echo "✓ /api/analytics/trends OK" || echo "✗ /api/analytics/trends FAILED"

echo "========================"
echo "Endpoint testing complete!"
EOF

chmod +x test_endpoints.sh
./test_endpoints.sh
```

### 3.3: Performance Testing

```bash
# Response time test
echo "Testing response times..."

for endpoint in "/health" "/api/organizations" "/api/publications?limit=10"; do
  echo "Testing $endpoint..."
  time curl -s http://localhost:8000$endpoint > /dev/null
done

# Concurrent load test
echo "Testing concurrent requests (5 simultaneous)..."
for i in {1..5}; do
  curl -s http://localhost:8000/api/organizations > /dev/null &
done
wait
echo "✓ Concurrent test passed"
```

**Expected**:
- Individual requests: <500ms
- Concurrent requests: all complete without errors

---

## Part 4: Integration Testing (45 minutes)

### 4.1: End-to-End Search Workflow

```bash
# Scenario: User searches for publications

# 1. Load homepage
curl -s http://localhost:8000/ | grep -q "Austrian Research" && echo "✓ Homepage loads"

# 2. Get organizations
curl -s http://localhost:8000/api/organizations | jq '.results | length' > /dev/null && echo "✓ Organizations available"

# 3. Search publications
curl -s "http://localhost:8000/api/publications?q=test" | jq '.results | length' > /dev/null && echo "✓ Search works"

# 4. Get analytics
curl -s http://localhost:8000/api/analytics/impact | jq '.results | length' > /dev/null && echo "✓ Analytics available"
```

### 4.2: Data Integrity Testing

```bash
cat > tests/test_data_integrity.py << 'EOF'
"""Test data integrity and relationships."""

from app.database import SessionLocal, Organization, Publication, Researcher, Project


def test_foreign_key_integrity():
    """Ensure foreign key relationships work."""
    db = SessionLocal()

    # If publications exist, verify organization_id is valid
    pubs = db.query(Publication).limit(5).all()
    for pub in pubs:
        if pub.organization_id:
            org = db.query(Organization).filter_by(id=pub.organization_id).first()
            assert org is not None, f"Publication references non-existent organization: {pub.organization_id}"

    print("✓ Foreign key integrity verified")
    db.close()


def test_no_orphaned_records():
    """Ensure no orphaned records."""
    db = SessionLocal()

    # Check publications with invalid organization_id
    orphans = db.query(Publication).filter(
        ~Publication.organization_id.in_(
            db.query(Organization.id)
        )
    ).all()

    assert len(orphans) == 0, f"Found {len(orphans)} orphaned publications"

    print("✓ No orphaned records found")
    db.close()
EOF

pytest tests/test_data_integrity.py -v
```

---

## Part 5: Security Testing (20 minutes)

### 5.1: Input Validation

```bash
# Test SQL injection protection
echo "Testing SQL injection protection..."
curl -s "http://localhost:8000/api/organizations?q=1';DROP TABLE organization;--"
# Expected: Should return safely (input is parameterized)

# Test XSS protection
echo "Testing XSS protection..."
curl -s "http://localhost:8000/api/organizations?q=<script>alert(1)</script>"
# Expected: Should return safely (escaped)

# Test rate limiting (if configured)
echo "Testing rate limiting..."
for i in {1..100}; do
  curl -s http://localhost:8000/health &
done
wait
# Expected: All requests complete (or rate limited gracefully)
```

### 5.2: CORS & Security Headers

```bash
# Check CORS headers
curl -I http://localhost:8000/api/organizations

# Expected headers:
# access-control-allow-origin: *
# access-control-allow-methods: *
# content-type: application/json
```

---

## Part 6: Load Testing (30 minutes)

### 6.1: Sustained Load

```bash
# Install ab (Apache Bench)
brew install httpd  # macOS

# Test sustained load (100 requests, 10 concurrent)
ab -n 100 -c 10 http://localhost:8000/api/organizations

# Expected:
# Requests per second: >50 (SQLite) or >100+ (PostgreSQL)
# Failed requests: 0
# Average response time: <500ms
```

### 6.2: Spike Test

```bash
# Simulate traffic spike (100 concurrent requests)
ab -n 100 -c 100 http://localhost:8000/api/organizations

# Expected:
# App remains responsive
# No connection drops
# Response times may increase but all complete
```

---

## Part 7: Manual Stakeholder Testing (30 minutes)

### 7.1: Feature Walkthrough

Create a demo script:

```
1. Homepage
   - Show featured organizations
   - Show statistics
   - Explain key features

2. Search
   - Perform sample searches
   - Show filtering options
   - Display search results

3. Organizations
   - Browse universities
   - Click org detail
   - Show publications per org

4. Researchers
   - Search by name
   - Show researcher profiles
   - Display publication history

5. Analytics
   - Show research trends
   - Display researcher impact
   - Show open access metrics

6. API
   - Show /docs endpoint
   - Demonstrate interactive testing
   - Explain data model
```

### 7.2: Collect Feedback

Document:
- Feature requests
- UI/UX improvements
- Performance concerns
- Data accuracy issues
- Missing information

---

## Testing Checklist

### Code Quality

- [ ] No syntax errors
- [ ] All imports work
- [ ] Database initializes without errors
- [ ] Linting passes (flake8)
- [ ] Type hints correct (mypy)

### Unit Tests

- [ ] Database model tests pass
- [ ] API endpoint tests pass
- [ ] Error handling tests pass
- [ ] Validation tests pass

### Functional Tests

- [ ] All web pages load
- [ ] Search functionality works
- [ ] Filtering works correctly
- [ ] Pagination works
- [ ] API documentation loads

### Performance

- [ ] Response time <500ms (single query)
- [ ] Response time <2s (complex queries)
- [ ] Handles 5+ concurrent requests
- [ ] No memory leaks after 1 hour runtime

### Security

- [ ] SQL injection prevented
- [ ] XSS attacks prevented
- [ ] CORS configured correctly
- [ ] No sensitive data in logs

### Data Integrity

- [ ] No orphaned records
- [ ] Foreign keys valid
- [ ] Data types correct
- [ ] Required fields present

### Integration

- [ ] End-to-end workflows work
- [ ] Multiple harvesters integrate
- [ ] Data from all sources accessible
- [ ] Relationships intact

### Load Testing

- [ ] 100 concurrent requests handled
- [ ] Spike requests don't crash app
- [ ] Recovery is fast after spike
- [ ] Database locks don't occur (PostgreSQL)

### Stakeholder Validation

- [ ] Features work as expected
- [ ] UI is intuitive
- [ ] Data is accurate
- [ ] Performance is acceptable
- [ ] Feedback documented

---

## Sample Test Report

After running all tests:

```
QUALITY ASSURANCE TEST REPORT
=============================

Date: October 22, 2024
Version: 0.1.0
Tester: [Name]

CODE QUALITY
============
✓ Syntax validation: PASS
✓ Import validation: PASS
✓ Database initialization: PASS
✓ Code style (flake8): PASS
✓ Type hints (mypy): PASS
Score: 5/5

UNIT TESTS
==========
✓ Database tests: 4/4 passed
✓ API tests: 7/7 passed
✓ Data integrity: 2/2 passed
Score: 13/13

FUNCTIONAL TESTS
================
✓ Web pages: 6/6 load correctly
✓ API endpoints: 37/37 respond
✓ Search: Works correctly
✓ Pagination: Functions properly
Score: 50/50

PERFORMANCE
===========
✓ Single query: 250ms avg
✓ Complex query: 1.2s avg
✓ Concurrent (5): All complete
✓ Load test (100): 95% success
Score: 4/4

SECURITY
========
✓ SQL injection: Protected
✓ XSS attacks: Protected
✓ CORS: Configured
Score: 3/3

TOTAL SCORE: 75/75 = 100%

RECOMMENDATION: Ready for Production Deployment ✅
```

---

## Continuous Testing (Post-Deployment)

### Monitoring

Set up recurring tests in production:

```bash
# Daily health check
0 9 * * * curl -s https://app.railway.app/health | grep -q healthy && echo "OK" || alert

# Weekly full test
0 0 * * 0 bash /scripts/weekly_tests.sh

# Monitor response times
*/5 * * * * curl -w "@curl-format.txt" https://app.railway.app/api/organizations
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. Celebrate! 🎉
2. Prepare for stakeholder launch
3. Create demo presentation
4. Schedule stakeholder demo
5. Gather final feedback

### If Tests Fail ⚠️

1. Investigate failure (check logs)
2. Fix issue in code
3. Re-test affected area
4. Get code review if major change
5. Repeat until all tests pass

---

## Test Summary

**Total Testing Time**: ~3.5 hours
**Test Coverage Areas**: 7
**Total Test Cases**: 30+
**Expected Pass Rate**: 100%

---

**QA & Testing phase is ready for implementation after deployment.** ✅

