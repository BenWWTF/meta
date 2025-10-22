# Deployment Guide - Austrian Research Metadata Platform

Guide to deploying ARMP to the public internet for stakeholder demos and production use.

## Quick Deployment (30 minutes)

### Option 1: Railway (Recommended for beginners)

Railway is the easiest option with minimal configuration.

#### Step 1: Create Railway Account
1. Go to https://railway.app
2. Click "Start a New Project"
3. Sign in with GitHub

#### Step 2: Deploy from GitHub

```bash
# Push to GitHub (if not already done)
cd /Users/Missbach/Desktop/claude/meta
git remote add origin https://github.com/YOUR_USERNAME/armp.git
git branch -M main
git push -u origin main
```

#### Step 3: Create Railway Project
1. On Railway dashboard, click "New Project"
2. Select "Deploy from GitHub"
3. Search for and select your `armp` repository
4. Railway auto-detects Python project

#### Step 4: Configure Environment
1. Go to project settings
2. Add environment variables:
   ```
   DATABASE_URL=sqlite:///./data/armp.db
   ENVIRONMENT=production
   ```

#### Step 5: Deploy
```bash
# Railway automatically deploys on git push
git push origin main

# Or trigger manual deploy in Railway dashboard
# → Project → "Deploy" button
```

**Result**: Live at `https://your-project-name.railway.app`

---

### Option 2: Render

Render also offers free tier with good documentation.

#### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub
3. Give Render access to your repositories

#### Step 2: Create Web Service
1. Dashboard → "New" → "Web Service"
2. Select your ARMP repository
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3.11

#### Step 3: Set Environment Variables
1. Environment tab
2. Add DATABASE_URL: `sqlite:///./data/armp.db`

#### Step 4: Deploy
Click "Create Web Service" - auto-deploys!

**Result**: Live at `https://your-service-name.onrender.com`

---

### Option 3: Heroku (Free tier removed, paid only)

If you still have Heroku free credits:

```bash
# Install Heroku CLI
brew install heroku

# Login
heroku login

# Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create app
heroku create your-app-name

# Set environment
heroku config:set DATABASE_URL="sqlite:///./data/armp.db"

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

---

## Production Configuration

### Database Setup

#### For SQLite (Simple, Works Fine)
```python
# Default configuration in app/database.py
DATABASE_URL = "sqlite:///./data/armp.db"
```

**Pros**: Zero setup, works out of the box
**Cons**: Single writer limitation, not ideal for high concurrency

#### For PostgreSQL (Recommended for Production)

1. **Create managed PostgreSQL**:
   - Railway: Auto-creates PostgreSQL
   - Render: "New PostgreSQL" → Free tier
   - AWS RDS: ~$15/month

2. **Get connection string**:
   ```
   postgresql://user:password@host:5432/armp
   ```

3. **Update database.py**:
   ```python
   import os
   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/armp.db")
   ```

4. **Apply migrations**:
   ```bash
   python -c "from app.database import init_db; init_db()"
   ```

---

## Performance Optimization for Production

### 1. Add Caching Headers

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import mimetypes

# In main.py
@app.get("/static/{file_path:path}")
async def static_files(file_path: str):
    response = FileResponse(f"app/static/{file_path}")
    response.headers["Cache-Control"] = "max-age=31536000"  # 1 year
    return response
```

### 2. Enable Compression

```python
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

### 3. Database Connection Pooling

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10
)
```

### 4. Redis Caching (Optional)

```bash
pip install redis aioredis
```

```python
from redis import Redis

redis = Redis.from_url(os.getenv("REDIS_URL"))

# Cache API responses
@app.get("/api/publications/stats/overview")
async def cached_stats():
    cached = redis.get("stats:overview")
    if cached:
        return json.loads(cached)

    # Expensive operation...
    result = calculate_stats()
    redis.setex("stats:overview", 3600, json.dumps(result))
    return result
```

---

## Monitoring & Logging

### Enable Application Logging

```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

### Monitor Performance

```bash
# Add monitoring service
pip install sentry-sdk

import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1
)
```

### Check Deployment Health

```bash
# Test on deployed server
curl https://your-deployment.app/health

# Should return:
# {
#   "status": "healthy",
#   "database": "connected"
# }
```

---

## Custom Domain Setup

### Railway Custom Domain

1. Go to project → Settings → Domains
2. Click "Add Domain"
3. Enter your domain (e.g., research.example.at)
4. Update DNS CNAME:
   ```
   CNAME: your-railway-app.railway.app
   ```

### Render Custom Domain

1. Project → Environment → Custom Domains
2. Enter domain
3. Follow DNS instructions

### CloudFlare (Recommended for DNS)

1. Add your domain to CloudFlare
2. Create CNAME record:
   ```
   Type: CNAME
   Name: armp
   Value: your-app.railway.app
   Proxied: Yes
   ```

---

## Continuous Deployment

### Automatic Deployment on Push

Both Railway and Render auto-deploy on git push.

```bash
# Just push to trigger deployment
git add .
git commit -m "Update feature"
git push origin main

# Monitor deployment in dashboard
# → Deployments tab → See logs
```

### Manual Deployments

If auto-deploy fails:

```bash
# Railway
railway up

# Render
# Via dashboard only

# Heroku
git push heroku main
```

---

## Environment Variables Checklist

```bash
# Create .env.production file (don't commit!)
DATABASE_URL=postgresql://...          # If using PostgreSQL
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
SENTRY_DSN=https://...                # If using Sentry
REDIS_URL=redis://...                 # If using Redis
ALLOWED_HOSTS=research.example.at      # Your domain
```

---

## Troubleshooting Deployments

### Issue: "Port already in use"
**Solution**: Platform automatically assigns $PORT variable
```python
import os
port = os.getenv("PORT", 8000)
```

### Issue: "Database locked"
**Solution**: Migrate to PostgreSQL or ensure single writer
```bash
# For PostgreSQL
heroku config:set DATABASE_URL="postgresql://..."
```

### Issue: "Module not found"
**Solution**: Ensure requirements.txt is committed
```bash
git add requirements.txt
git commit -m "Update dependencies"
git push
```

### Issue: "Static files not found"
**Solution**: Use CDN for CSS/JS (Tailwind via CDN already done)
```html
<script src="https://cdn.tailwindcss.com"></script>
```

### Issue: "CORS errors"
**Solution**: Configure allowed origins
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Pre-Deployment Checklist

- [ ] Code committed to git
- [ ] All tests passing (if any)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Static files verified
- [ ] API documentation working (/docs)
- [ ] Health check passing (/health)
- [ ] Domain configured (if custom)
- [ ] Monitoring enabled (Sentry optional)
- [ ] Database backups configured

---

## Post-Deployment Verification

```bash
# Test deployed application
export APP_URL="https://your-app.railway.app"

# 1. Health check
curl $APP_URL/health

# 2. API endpoints
curl $APP_URL/api/organizations?limit=1

# 3. Web interface
curl $APP_URL/ | grep "ARMP"

# 4. Check logs
# → In Dashboard → Deployments → Logs

# 5. Performance test
time curl $APP_URL/api/publications/stats/overview
```

---

## Cost Analysis

| Platform | Free Tier | Paid Tier | Notes |
|----------|-----------|-----------|-------|
| Railway | $5 credit/month | Pay as you go | Stops if credit runs out |
| Render | Limited hours | $7-12/month | Easy scaling |
| Heroku | None (removed) | $5-50+/month | Good for production |
| AWS Lightsail | Free tier | $3.50-10/month | Most control |

**Recommended**: Railway or Render for MVP, AWS Lightsail for production scale.

---

## Rollback Strategy

### If Deployment Breaks

```bash
# Railway
railway logs                    # Check error
git revert HEAD                 # Revert last commit
git push origin main            # Auto-redeploy

# Render
# Manual rollback in dashboard → Deployments → Revert
```

---

## Scaling Beyond MVP

### When You Outgrow Free Tier

1. **Database**: Migrate to managed PostgreSQL
2. **Caching**: Add Redis for session/data caching
3. **CDN**: Use CloudFlare for static content
4. **Monitoring**: Add Sentry or New Relic
5. **Analytics**: Add PostHog or Mixpanel
6. **Email**: Configure SMTP for contact forms

---

## Deployment Timeline

| Step | Time | Notes |
|------|------|-------|
| Account setup | 5 min | Sign up on Railway/Render |
| Git setup | 5 min | Push code to GitHub |
| Initial deploy | 10 min | Auto-build and start |
| Configuration | 5 min | Add env variables |
| Testing | 5 min | Verify endpoints |
| Custom domain | 5 min | Configure DNS (takes ~24h) |
| **Total** | **~35 min** | App live and shareable |

---

## Next Steps

1. **Choose platform**: Railway recommended for speed
2. **Follow Step-by-step guide above**
3. **Share public URL with stakeholders**
4. **Monitor logs and performance**
5. **Plan Phase 2 enhancements**

---

## Support Resources

- **Railway Docs**: https://docs.railway.app
- **Render Docs**: https://render.com/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Troubleshooting**: Check `/health` endpoint and logs

**You're ready to go public!** 🚀
