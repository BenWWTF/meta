# Phase 3c: Database Migration - SQLite to PostgreSQL

**Phase**: 3c - Database Migration for Production Scalability
**Status**: ⏳ IN PROGRESS - Migration Infrastructure
**Objective**: Enable platform to scale beyond 10 concurrent users
**Duration**: 2-4 hours (full migration including testing)
**Last Updated**: October 2024

---

## Executive Summary

As the platform scales from MVP to production use, SQLite's limitations become apparent:
- Single-file database (concurrency issues)
- Limited to ~10 concurrent users
- Cannot be used with multiple application instances
- No advanced features (connection pooling, prepared statements optimization)

PostgreSQL is the industry-standard solution:
- Handles 50+ concurrent users easily
- Horizontal scalability
- Advanced indexing and query optimization
- Connection pooling support
- Better performance for large datasets

This phase provides **zero-downtime migration** from SQLite to PostgreSQL while maintaining full application functionality.

---

## Why PostgreSQL?

### Limitations of SQLite

| Issue | Impact | Symptom |
|-------|--------|---------|
| Single writer | Slow concurrent writes | "Database is locked" errors |
| File-based | No scaling | One server only |
| No connection pooling | Resource exhaustion | App crashes under load |
| Limited indices | Slow queries | 5+ sec response times |
| No transactions at scale | Data integrity | Race conditions |

### PostgreSQL Advantages

| Benefit | Result | Value |
|---------|--------|-------|
| Multi-process architecture | Handle 100+ concurrent users | Production-ready |
| ACID transactions | Data consistency | Financial/critical data safe |
| Advanced indices | Query optimization | <100ms for complex queries |
| Connection pooling | Resource efficiency | Scales to many instances |
| Replication | High availability | Automated backups |
| Cloud-native | Easy scaling | AWS RDS, Railway, etc. |

---

## Migration Strategy

### Phase 3c Approach: Seamless Migration

```
Current State: SQLite (MVP - 15 organizations, 0 publications)
                ↓ (Create PostgreSQL clone)
Parallel State: SQLite + PostgreSQL running simultaneously
                ↓ (Validate data integrity)
Validation:    Compare row counts, checksums
                ↓ (Switch application)
Final State:   PostgreSQL (Production - full data)
```

### Timeline

| Step | Duration | Task |
|------|----------|------|
| 1 | 10 min | Set up PostgreSQL database |
| 2 | 5 min | Update database connection |
| 3 | 10 min | Migrate schema |
| 4 | 30 sec | Load initial data |
| 5 | 10 min | Validate migration |
| 6 | 5 min | Update application |
| 7 | 2 min | Deploy to Railway |
| 8 | 5 min | Verify production |

**Total**: 1-2 hours (no downtime required)

---

## Option 1: Railway PostgreSQL (Easiest)

Railway provides managed PostgreSQL with automatic backups.

### Step 1: Add PostgreSQL to Railway

1. Go to Railway dashboard
2. Click your project
3. **Plugin** → **PostgreSQL**
4. Railway creates PostgreSQL instance automatically
5. Database URL auto-injected as `DATABASE_URL` environment variable

**Result**:
```
DATABASE_URL=postgresql://user:password@host:5432/armp
```

### Step 2: Run Migration

```bash
# Create migration script (see below for content)
cat > scripts/migrate_to_postgresql.py << 'EOF'
# ... migration script content from next section
EOF

# Update database connection to use new URL
# (Railway already set DATABASE_URL automatically)
```

### Step 3: Test Connection

```bash
# Via Railway shell, test PostgreSQL connection:
python -c "
from app.database import SessionLocal
db = SessionLocal()
print('✓ PostgreSQL connection successful')
db.close()
"
```

---

## Option 2: Manual PostgreSQL Setup (More Control)

### Install PostgreSQL Locally

```bash
# macOS
brew install postgresql@15

# Start PostgreSQL
brew services start postgresql@15

# Verify
psql --version  # Should show postgres 15.x
```

### Create Database

```bash
# Create user and database
createuser armp_user -P  # Enter password when prompted
createdb -O armp_user armp

# Test connection
psql -U armp_user -d armp -h localhost
```

### Create Connection String

```
postgresql://armp_user:YOUR_PASSWORD@localhost:5432/armp
```

---

## Step 1: Update Configuration

### Create .env.postgres

```bash
# Copy current .env
cp .env .env.sqlite.backup

# Update .env with PostgreSQL URL
cat > .env << 'EOF'
# Switch to PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/armp
ENVIRONMENT=production
LOG_LEVEL=info
EOF
```

### Verify Connection

```bash
python -c "
import os
from sqlalchemy import create_engine, text

db_url = os.getenv('DATABASE_URL', 'sqlite:///./data/armp.db')
engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print('✓ PostgreSQL connection successful')
    print(f'Version: {result.scalar()}')
"
```

**Expected Output**:
```
✓ PostgreSQL connection successful
Version: PostgreSQL 15.x on ...
```

---

## Step 2: Migrate Schema

SQLAlchemy automatically creates schema from models.

### Create Migration Script

```bash
cat > scripts/migrate_schema.py << 'EOF'
#!/usr/bin/env python3
"""
Migrate schema from SQLite to PostgreSQL

Creates all tables in PostgreSQL matching SQLAlchemy models.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, engine
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def migrate():
    """Create all tables in target database."""
    logger.info("Starting PostgreSQL schema migration...")

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Schema migration complete")
        logger.info(f"Created tables from {len(Base.metadata.tables)} models")

        for table_name in Base.metadata.tables:
            logger.info(f"  - {table_name}")

        return True
    except Exception as e:
        logger.error(f"Schema migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/migrate_schema.py
```

### Run Schema Migration

```bash
python scripts/migrate_schema.py

# Expected output:
# Starting PostgreSQL schema migration...
# ✓ Schema migration complete
# Created tables from 7 models
#   - organization
#   - publication
#   - researcher
#   - project
#   - harvest_log
#   - publication_author
#   - project_publication
```

---

## Step 3: Migrate Data

### Create Data Migration Script

```bash
cat > scripts/migrate_data.py << 'EOF'
#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL

Exports data from old database and imports into new one.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import (
    Base, Organization, Publication, Researcher, Project,
    HarvestLog, publication_author, project_publication
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def migrate_data():
    """Migrate data from SQLite to PostgreSQL."""

    # Source: SQLite
    sqlite_url = "sqlite:///./data/armp.db"
    sqlite_engine = create_engine(sqlite_url)
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    sqlite_db = SQLiteSession()

    # Target: PostgreSQL
    postgres_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/armp")
    postgres_engine = create_engine(postgres_url)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_db = PostgresSession()

    try:
        logger.info("Starting data migration from SQLite to PostgreSQL...")

        # Count records in source
        org_count = sqlite_db.query(Organization).count()
        pub_count = sqlite_db.query(Publication).count()
        res_count = sqlite_db.query(Researcher).count()
        proj_count = sqlite_db.query(Project).count()

        logger.info(f"Source database contains:")
        logger.info(f"  - {org_count} organizations")
        logger.info(f"  - {pub_count} publications")
        logger.info(f"  - {res_count} researchers")
        logger.info(f"  - {proj_count} projects")

        # Migrate organizations (no dependencies)
        logger.info("Migrating organizations...")
        for org in sqlite_db.query(Organization).all():
            postgres_db.add(Organization(**{c.name: getattr(org, c.name) for c in Organization.__table__.columns}))
        postgres_db.commit()
        logger.info(f"✓ Migrated {org_count} organizations")

        # Migrate publications (depends on organization)
        logger.info("Migrating publications...")
        for pub in sqlite_db.query(Publication).all():
            postgres_db.add(Publication(**{c.name: getattr(pub, c.name) for c in Publication.__table__.columns}))
        postgres_db.commit()
        logger.info(f"✓ Migrated {pub_count} publications")

        # Migrate researchers
        logger.info("Migrating researchers...")
        for res in sqlite_db.query(Researcher).all():
            postgres_db.add(Researcher(**{c.name: getattr(res, c.name) for c in Researcher.__table__.columns}))
        postgres_db.commit()
        logger.info(f"✓ Migrated {res_count} researchers")

        # Migrate projects
        logger.info("Migrating projects...")
        for proj in sqlite_db.query(Project).all():
            postgres_db.add(Project(**{c.name: getattr(proj, c.name) for c in Project.__table__.columns}))
        postgres_db.commit()
        logger.info(f"✓ Migrated {proj_count} projects")

        # Migrate association tables
        logger.info("Migrating relationships...")

        # Publication authors
        author_count = sqlite_db.execute(text("SELECT COUNT(*) FROM publication_author")).scalar() or 0
        if author_count > 0:
            # Copy association table data
            authors = sqlite_db.execute(text("SELECT * FROM publication_author")).fetchall()
            for author in authors:
                postgres_db.execute(publication_author.insert().values(**dict(author)))
            postgres_db.commit()
            logger.info(f"✓ Migrated {author_count} publication-author relationships")

        # Project publications
        proj_pub_count = sqlite_db.execute(text("SELECT COUNT(*) FROM project_publication")).scalar() or 0
        if proj_pub_count > 0:
            proj_pubs = sqlite_db.execute(text("SELECT * FROM project_publication")).fetchall()
            for proj_pub in proj_pubs:
                postgres_db.execute(project_publication.insert().values(**dict(proj_pub)))
            postgres_db.commit()
            logger.info(f"✓ Migrated {proj_pub_count} project-publication relationships")

        logger.info("✓ Data migration complete!")

        # Verify counts
        verify_org = postgres_db.query(Organization).count()
        verify_pub = postgres_db.query(Publication).count()
        verify_res = postgres_db.query(Researcher).count()
        verify_proj = postgres_db.query(Project).count()

        logger.info("Verification:")
        logger.info(f"  Organizations: {verify_org}/{org_count} ✓" if verify_org == org_count else f"  Organizations: {verify_org}/{org_count} ✗")
        logger.info(f"  Publications: {verify_pub}/{pub_count} ✓" if verify_pub == pub_count else f"  Publications: {verify_pub}/{pub_count} ✗")
        logger.info(f"  Researchers: {verify_res}/{res_count} ✓" if verify_res == res_count else f"  Researchers: {verify_res}/{res_count} ✗")
        logger.info(f"  Projects: {verify_proj}/{proj_count} ✓" if verify_proj == proj_count else f"  Projects: {verify_proj}/{proj_count} ✗")

        return True

    except Exception as e:
        logger.error(f"Data migration failed: {e}", exc_info=True)
        return False
    finally:
        sqlite_db.close()
        postgres_db.close()

if __name__ == "__main__":
    success = migrate_data()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/migrate_data.py
```

### Run Data Migration

```bash
# Ensure PostgreSQL DATABASE_URL is set
export DATABASE_URL="postgresql://user:password@host/armp"

# Run migration
python scripts/migrate_data.py

# Expected output:
# Starting data migration from SQLite to PostgreSQL...
# Source database contains:
#   - 15 organizations
#   - 0 publications
#   - 0 researchers
#   - 0 projects
# Migrating organizations...
# ✓ Migrated 15 organizations
# ... (other tables)
# ✓ Data migration complete!
```

---

## Step 4: Update Application Configuration

### Create Production Database Config

Update `app/database.py` to use PostgreSQL in production:

```python
# In app/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Check environment for database URL
# Production: PostgreSQL
# Development: SQLite (default)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/armp.db"
)

# For SQLite, add special parameters
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections
        echo=False
    )

# Rest of database.py remains unchanged
```

### Create Migration Helper Script

```bash
cat > scripts/verify_migration.py << 'EOF'
#!/usr/bin/env python3
"""
Verify migration success by comparing SQLite and PostgreSQL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify():
    """Compare record counts between SQLite and PostgreSQL."""

    sqlite_engine = create_engine("sqlite:///./data/armp.db")

    import os
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url or "postgresql" not in postgres_url:
        logger.error("DATABASE_URL not set or not PostgreSQL")
        return False

    postgres_engine = create_engine(postgres_url)

    tables = [
        "organization",
        "publication",
        "researcher",
        "project"
    ]

    logger.info("Verifying migration...")
    all_match = True

    for table in tables:
        sqlite_count = sqlite_engine.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        postgres_count = postgres_engine.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

        match = "✓" if sqlite_count == postgres_count else "✗"
        logger.info(f"{match} {table}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")

        if sqlite_count != postgres_count:
            all_match = False

    return all_match

if __name__ == "__main__":
    success = verify()
    logger.info("Migration verified!" if success else "Migration has issues!")
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/verify_migration.py

python scripts/verify_migration.py
```

---

## Step 5: Test in Production (Railway)

### Update Railway PostgreSQL Connection

1. **Add PostgreSQL Plugin** to your Railway project
2. **Environment Variables** auto-updated with `DATABASE_URL`
3. **Restart app** to use new connection

### Verify Production Connection

```bash
# Via Railway shell or direct SSH
curl https://your-app.railway.app/health
# Should return healthy status with PostgreSQL

# Check /api/organizations
curl https://your-app.railway.app/api/organizations
# Should return organizations from PostgreSQL
```

---

## Step 6: Enable Connection Pooling

### Install pgBouncer (Optional, for scaling)

PostgreSQL connection pooling improves resource efficiency:

```bash
# macOS
brew install pgbouncer

# Create pgbouncer.ini
cat > /usr/local/etc/pgbouncer.ini << 'EOF'
[databases]
armp = host=localhost port=5432 dbname=armp

[pgbouncer]
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
min_pool_size = 5
EOF

# Start pgBouncer
pgbouncer -d /usr/local/etc/pgbouncer.ini

# Use localhost:6432 instead of 5432 in connection string
# DATABASE_URL=postgresql://user:pass@localhost:6432/armp
```

---

## Step 7: Optimize PostgreSQL

### Create Indices for Performance

```bash
cat > scripts/optimize_postgresql.py << 'EOF'
#!/usr/bin/env python3
"""
Create indices on commonly-queried columns for PostgreSQL
"""

import sys
import os
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize():
    """Create indices for query performance."""

    indices = [
        # Publications
        ("publication", "doi"),
        ("publication", "title"),
        ("publication", "publication_date"),
        ("publication", "organization_id"),

        # Researchers
        ("researcher", "orcid"),
        ("researcher", "name"),
        ("researcher", "organization_id"),

        # Projects
        ("project", "grant_number"),
        ("project", "title"),
        ("project", "funder"),

        # Organization
        ("organization", "ror_id"),
        ("organization", "name"),
    ]

    with engine.connect() as conn:
        for table, column in indices:
            index_name = f"idx_{table}_{column}"
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})"
            try:
                conn.execute(text(sql))
                logger.info(f"✓ Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Index {index_name} may already exist: {e}")

        conn.commit()

    logger.info("✓ PostgreSQL optimization complete")

if __name__ == "__main__":
    optimize()
EOF

python scripts/optimize_postgresql.py
```

---

## Rollback Plan

If PostgreSQL migration causes issues:

### Quick Rollback to SQLite

```bash
# Update DATABASE_URL back to SQLite
export DATABASE_URL="sqlite:///./data/armp.db"

# Or in Railway: remove PostgreSQL plugin
# Railway dashboard → Project → Plugins → PostgreSQL → Destroy

# Restart application
# Application will work with SQLite again
```

---

## Performance Comparison

### Before (SQLite)

```
Concurrent Users: 5-10
Response Time: 500ms - 2s
Max Connections: 1 writer
Scaling: Single server only
```

### After (PostgreSQL)

```
Concurrent Users: 50-100
Response Time: 50-200ms
Max Connections: 20+ simultaneous
Scaling: Horizontal (multiple servers)
```

---

## Phase 3c Checklist

- [ ] PostgreSQL database created (Railway or local)
- [ ] Connection string obtained
- [ ] DATABASE_URL environment variable set
- [ ] Schema migration script created and tested
- [ ] Data migration script created and tested
- [ ] All data verified (counts match)
- [ ] Application updated to use DATABASE_URL
- [ ] Local testing with PostgreSQL completed
- [ ] Railway PostgreSQL plugin added
- [ ] Production deployment tested
- [ ] All endpoints working with PostgreSQL
- [ ] Rollback procedure understood

---

## Next Steps

Once Phase 3c is complete:

### Phase QA: Testing & Optimization
- Comprehensive endpoint testing
- Performance profiling
- Load testing
- Security audit

### Phase Launch: Stakeholder Presentation
- Live demo preparation
- Feedback collection
- Documentation finalization

---

## Timeline Summary

| Task | Duration | Status |
|------|----------|--------|
| PostgreSQL setup | 10 min | ⏳ |
| Schema migration | 5 min | ⏳ |
| Data migration | 10 min | ⏳ |
| Verification | 5 min | ⏳ |
| Local testing | 10 min | ⏳ |
| Railway deployment | 5 min | ⏳ |
| Production verification | 5 min | ⏳ |
| **Total** | **~50 min** | ⏳ |

---

**Phase 3c: Database Migration to PostgreSQL is ready for implementation.** ✅

