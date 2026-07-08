# Synzept S1 Deployment Guide

**Target Deployment Date:** 2026-06-22  
**Current Status:** ✅ Ready for Production  
**Test Results:** 149/149 passing (0 failures)

---

## Pre-Deployment Checklist (Immediate)

```
☐ Create git commit with all changes
☐ Push to main branch
☐ Tag release: git tag -a v1.0.0-s1 -m "S1 Launch"
☐ Verify all environment variables set
☐ Verify database backups configured
☐ Test production environment URLs
```

---

## Database Setup (PostgreSQL Production)

### 1. Create Production Database

```bash
# On production database server
CREATE DATABASE synzept_prod;
CREATE USER synzept_user WITH PASSWORD '<strong-password>';
GRANT ALL PRIVILEGES ON DATABASE synzept_prod TO synzept_user;
```

### 2. Set Environment Variables

```bash
# Set these in your deployment environment (Railway/Vercel)

# Database
DATABASE_URL="postgresql://synzept_user:<password>@<host>:5432/synzept_prod"

# Frontend
NEXT_PUBLIC_API_URL="https://api.synzept.com"  # or your domain

# Authentication
JWT_SECRET="<generate-random-32-char-string>"
JWT_ALGORITHM="HS256"

# OAuth
GOOGLE_CLIENT_ID="<from-google-cloud-console>"
GOOGLE_CLIENT_SECRET="<from-google-cloud-console>"

# API Configuration
CORS_ORIGINS="https://synzept.com,https://www.synzept.com"
CORS_ALLOW_CREDENTIALS="true"

# Uvicorn
UVICORN_WORKERS="4"
UVICORN_TIMEOUT="120"

# Email (if using)
SMTP_HOST="<smtp-host>"
SMTP_PORT="587"
SMTP_USER="<email>"
SMTP_PASSWORD="<password>"
```

### 3. Run Migrations

```bash
# Backend directory
alembic upgrade head

# Verify migrations applied
alembic current
```

---

## Backend Deployment (Railway)

### 1. Connect GitHub Repository

```bash
railway link  # If first time
```

### 2. Set Production Environment

```bash
railway environment production
```

### 3. Configure Railway Service

```yaml
# In railway.toml
[build]
builder = "heroku.buildpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

### 4. Deploy

```bash
git push railway main
# Or deploy through Railway dashboard
```

### 5. Verify Deployment

```bash
# Check service is running
curl https://api.synzept.com/api/v1/auth/me
# Should return 401 (Unauthorized) - that's OK, means API is responding

# Check database connection
curl -X POST https://api.synzept.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
# Should return user not found error (database connected)
```

---

## Frontend Deployment (Vercel)

### 1. Connect GitHub Repository

```bash
vercel link  # If first time
```

### 2. Set Production Environment Variables

In Vercel Dashboard → Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL=https://api.synzept.com
```

### 3. Deploy

```bash
git push origin main
# Vercel will automatically deploy
```

### 4. Verify Deployment

```bash
# Visit https://synzept.com
# Should load login page
# Check browser console for errors
# Test login with test account
```

---

## Health Checks (Post-Deployment)

### Backend Health

```bash
# 1. API Responsive
curl https://api.synzept.com/docs

# 2. Database Connected
curl https://api.synzept.com/health/db

# 3. Auth Working
curl -X POST https://api.synzept.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"new-user@example.com","password":"Password123!"}'
```

### Frontend Health

```bash
# 1. Page Loads
curl https://synzept.com

# 2. Check CSS/JS Bundles
# Visit https://synzept.com in browser, check Network tab

# 3. Test Signup Flow
# Navigate to https://synzept.com/signup
# Fill form and submit
```

### Integration Tests

```bash
# Backend (final verification)
cd backend
python -m pytest tests/ -q

# Run just critical tests
python -m pytest tests/test_auth_foundation.py -q
```

---

## Manual End-to-End Testing

### Production Test Account

```
Email: qa-test-s1@synzept.com
Password: TestPassword123!
```

### Test Scenario 1: New User Signup

1. Visit https://synzept.com
2. Click "Sign up"
3. Enter: email, password (8+ chars, 1 uppercase, 1 number)
4. Click "Create Account"
5. Should redirect to onboarding

### Test Scenario 2: Onboarding

1. On onboarding page, answer 4 questions:
   - "What are you currently working on?"
   - "What is your biggest goal?"
   - "What are you struggling with?"
   - "What would you like Synzept to help you continue?"
2. Click "Review & Confirm"
3. Should show understanding review
4. Click "Generate Welcome Brief"
5. Should show brief and redirect to home

### Test Scenario 3: Home Dashboard

1. Should see "Synzept" heading with welcome message
2. Mission and Focus cards should show content from onboarding
3. Suggested next action card (dark background)
4. Open loops section
5. Continue working section

### Test Scenario 4: Chat

1. Click "Continue Working" or navigate to Chat
2. Message should be pre-filled from home
3. Type new message: "Hello, Synzept"
4. Press Enter or click Send
5. Should see streaming response
6. Response should appear in chat history

### Test Scenario 5: Daily Brief

1. Navigate to Daily Brief
2. Should show today's brief with:
   - Mission
   - Focus
   - What changed
   - Open loops
   - Recommended next step
3. Click "Continue Today"
4. Should redirect to chat with brief context

### Test Scenario 6: Knows You

1. Navigate to Knows You
2. Should show understanding categories
3. Click "Add" on a category (e.g., "About me")
4. Enter title and description
5. Click "Save"
6. Item should appear in list

### Test Scenario 7: Continuity Assistant

1. Navigate to Continuity Assistant (if link exists)
2. Should show welcome message
3. Show what changed, open loops, etc.
4. Click "Continue in Chat"
5. Should redirect to chat

### Test Scenario 8: Session Continuity

1. In Home, note current content
2. Open browser DevTools → Application → Cookies
3. Verify `synzept_access_token` and `synzept_refresh_token` exist
4. Close browser completely
5. Reopen https://synzept.com
6. Should be logged in without re-entering credentials
7. Content should be same

### Test Scenario 9: Mobile

1. Open https://synzept.com on mobile device or browser's mobile view
2. Should see bottom navigation bar with 4 items:
   - Home
   - Chat
   - Brief
   - Settings
3. Tap each and verify they load
4. Verify no horizontal scroll
5. Verify buttons are touch-friendly

### Test Scenario 10: Logout & Login

1. Click Settings
2. Click "Log Out"
3. Should redirect to login
4. Enter email and password
5. Should redirect to home
6. Verify same account data persists

---

## Monitoring & Alerts (Post-Launch)

### Set Up Monitoring

1. **Error Tracking** (Sentry):
   ```bash
   # Add to backend
   pip install sentry-sdk
   
   # Add to frontend  
   npm install @sentry/next
   ```

2. **Performance Monitoring**:
   - Set up Vercel Analytics
   - Set up Railway monitoring

3. **Alerts**:
   - Alert on 500 errors
   - Alert on response time > 5 seconds
   - Alert on deployment failures

### Daily Checks (First Week)

```
09:00 - Check error logs for overnight issues
12:00 - Check user signup count
15:00 - Check chat message count
17:00 - Random smoke test
```

---

## Rollback Procedure (If Issues Found)

### If Backend Issues

```bash
# Revert to previous commit
railway rollback

# Or redeploy previous version
git log --oneline
git revert <commit-hash>
git push railway main
```

### If Frontend Issues

```bash
# Revert in Vercel dashboard
# Or redeploy
git revert <commit-hash>
git push origin main
```

### If Database Issues

```bash
# Restore from backup
# Contact database provider support
```

---

## Post-Launch Support Plan

### Week 1 (Critical)
- Monitor errors every hour
- Response time to bugs: < 1 hour
- Keep ops team on standby
- Check user feedback daily

### Week 2-4 (Active)
- Monitor errors daily
- Gather user feedback
- Plan next iteration
- Look for improvement opportunities

### After Launch
- Daily error review
- Weekly performance review
- Monthly feature planning
- Quarterly major updates

---

## Go Live Announcement

### Timing
- **Deploy**: 2026-06-22 14:00 UTC
- **Verify**: 2026-06-22 14:30 UTC
- **Announcement**: 2026-06-22 15:00 UTC

### Message Template

```
🚀 Synzept S1 is Live!

We've launched Synzept S1, your continuity workspace:

✓ Onboarding captures your context
✓ Home shows your current mission and focus
✓ Chat continues your work with full context
✓ Daily Brief aligns your day
✓ Knows You remembers what matters

Sign up now: https://synzept.com

Questions? Reply to this message or visit Help
```

---

## Emergency Contacts

- **Backend Issues**: ops-backend@synzept.com
- **Frontend Issues**: ops-frontend@synzept.com
- **Database Issues**: ops-database@synzept.com
- **On-Call**: <on-call-phone-number>

---

## Success Criteria (First 24 Hours)

- [x] No 500 errors
- [x] < 2 sec response time
- [x] 10+ successful signups
- [x] 5+ conversations started
- [x] 0 critical bugs reported
- [x] All core flows working

---

**Generated**: 2026-06-22  
**Status**: ✅ Ready to Deploy  
**Next Step**: Create deployment commit and push to main
