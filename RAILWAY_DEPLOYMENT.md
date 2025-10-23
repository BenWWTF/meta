# Railway Deployment Guide - Austrian Research Metadata Platform

## One-Click Deployment (Easiest)

### Step 1: Deploy with Railway Button
Click this button to deploy directly to Railway:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?repo=https://github.com/BenWWTF/meta&referralCode=BenWWTF)

This will automatically:
- Fork your repository to Railway
- Set up the deployment pipeline
- Configure environment variables
- Deploy the application

---

## Manual Deployment (Complete Control)

### Prerequisites
- Railway account (free at https://railway.app)
- GitHub repository connected (already done!)
- Git installed

### Step 1: Connect GitHub Repository

1. Go to https://railway.app
2. Click **"Create a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose **BenWWTF/meta** repository
5. Railway will auto-detect the Procfile and requirements.txt

### Step 2: Configure Environment Variables

In Railway Dashboard → Project → Variables:

```
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=[generate-a-secure-random-string]
CORS_ORIGINS=https://your-app-name.railway.app
API_TITLE=Austrian Research Metadata Platform
API_VERSION=0.1.0
LOG_LEVEL=INFO
```

### Step 3: Add PostgreSQL Database (Optional but Recommended)

1. In Railway, click **"Create New Service"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically inject `DATABASE_URL` environment variable
4. Update `.env` if needed to use PostgreSQL URL

For SQLite (no database service needed):
```
DATABASE_URL=sqlite:///./data/armp.db
```

### Step 4: Deploy

Railway automatically deploys when you:
- Push to GitHub main branch
- Or click **"Deploy"** in Railway Dashboard

Watch the deployment logs in real-time.

### Step 5: Verify Deployment

Once deployed, Railway will give you a URL like:
```
https://meta-production-xxxx.railway.app
```

Test endpoints:
```bash
# Health check
curl https://meta-production-xxxx.railway.app/health

# Homepage
curl https://meta-production-xxxx.railway.app/

# API docs
curl https://meta-production-xxxx.railway.app/docs
```

---

## Monitoring & Logs

### View Logs in Railway
1. Go to project → Deployments
2. Click latest deployment
3. View logs in real-time

### View Logs via CLI
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# View logs
railway logs --tail
```

---

## Troubleshooting

### Application Won't Start
Check logs for errors:
```
railway logs --tail -f
```

Common issues:
- Missing environment variables → Add in Railway Dashboard
- Port binding error → Railway automatically sets `$PORT` environment variable
- Database connection → Ensure `DATABASE_URL` is set correctly

### Database Issues
If using PostgreSQL:
1. Ensure database service is added
2. Check `DATABASE_URL` is injected
3. Verify migrations ran (check logs)

If using SQLite:
1. No setup needed
2. Data persists in `data/armp.db`

### CORS Issues
If you get CORS errors:
1. Update `CORS_ORIGINS` in Railway Variables
2. Format: `https://your-domain.railway.app` (no trailing slash)
3. Multiple origins: `https://domain1.com,https://domain2.com`

---

## Performance Optimization

### Enable Caching
Railway provides free Redis add-on:
1. Add Redis service in Railway
2. Set `REDIS_URL` environment variable
3. Update code to use Redis caching

### Monitor Resource Usage
In Railway Dashboard:
- Check CPU/Memory usage
- Scale up dyno if needed (Team plan required)

### Optimize Database
For PostgreSQL:
```sql
-- Create indexes for faster searches
CREATE INDEX idx_organization_ror ON organization(ror_id);
CREATE INDEX idx_publication_doi ON publication(doi);
CREATE INDEX idx_researcher_orcid ON researcher(orcid_id);
```

---

## Custom Domain

### Add Custom Domain
1. In Railway → Project Settings → Domains
2. Click **"Add Custom Domain"**
3. Enter your domain (e.g., `meta.example.com`)
4. Railway provides DNS settings
5. Update your domain DNS records

### SSL Certificate
Railway automatically provides free SSL with custom domains via Let's Encrypt.

---

## Continuous Deployment

### Auto-Deploy on Push
Railway automatically deploys when you push to main branch.

To disable:
1. Railway Dashboard → Project Settings
2. Uncheck "Auto Deploy"

### Manual Deploy
```bash
git push origin main
# Railway will automatically build and deploy
```

---

## Rollback to Previous Version

If deployment breaks:
1. Go to Railway Dashboard → Deployments
2. Click previous successful deployment
3. Click **"Redeploy"**

Or revert in Git:
```bash
git revert HEAD
git push origin main
# Railway will redeploy with reverted code
```

---

## Scaling

### Upgrade Plan (Free → Pro)
Railway free tier includes:
- 512 MB memory
- 100 GB bandwidth/month
- Unlimited deployments

For production:
- Upgrade to Team plan for more resources
- Auto-scaling available

### Vertical Scaling
In Railway → Project Settings → Plan

### Horizontal Scaling
Currently not available on free tier. Consider Docker Swarm or Kubernetes for advanced scaling.

---

## Cost Estimation

**Railway Pricing** (as of 2025):
- Free tier: $5/month credit
- Pro: $7/month + usage costs
- Database: ~$4-10/month for PostgreSQL

**Estimated Monthly Cost:**
- Small deployment: $5-15/month
- Medium deployment: $15-30/month
- Large deployment: $30+/month

---

## Alternative Deployment Platforms

If you want to try other platforms:

### Heroku (Similar to Railway)
```bash
heroku login
heroku create your-app-name
git push heroku main
heroku open
```

### AWS (More control, more complex)
- Use Elastic Beanstalk for easy deployment
- Or EC2 for full control

### Google Cloud Run
```bash
gcloud run deploy armp \
  --source . \
  --platform managed \
  --region us-central1
```

### Azure
- Use App Service for easy deployment
- Use Container Instances for Docker

---

## Post-Deployment Checklist

- [ ] Application accessible at deployment URL
- [ ] Health check returns 200 OK
- [ ] Homepage loads properly
- [ ] Search functionality works
- [ ] API documentation available at `/docs`
- [ ] Security headers present (check with curl -i)
- [ ] Database connected and working
- [ ] Logs show no errors
- [ ] Custom domain configured (if needed)
- [ ] Email notifications setup (optional)

---

## Support

- Railway Docs: https://docs.railway.app
- Email: support@railway.app
- Discord: https://discord.gg/railway

---

**Status**: Ready for Production ✅
**Last Updated**: October 23, 2025
**Platform**: Railway
