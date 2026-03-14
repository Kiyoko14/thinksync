# Deployment Checklist

## Pre-Deployment (Local Testing)

### ✓ Environment Setup
- [ ] Copy `.env.example` to `.env.local`
- [ ] Configure `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- [ ] Configure `OPENAI_API_KEY`
- [ ] Run `bash validate.sh` - all checks pass
- [ ] Review `.env.local` file for all required vars

### ✓ Docker Setup
- [ ] Docker installed (`docker --version`)
- [ ] Docker Compose installed (`docker-compose --version`)
- [ ] No conflicts on ports 3000, 6379, 8000
- [ ] Sufficient disk space (5+ GB)

### ✓ Code Verification
- [ ] Run `git status` - no uncommitted changes
- [ ] Verify no merge conflicts (`grep -r "<<<<<<" backend/`)
- [ ] Backend dependencies installed (`pip list | grep fastapi`)
- [ ] Frontend dependencies installed (`ls frontend/node_modules`)

### ✓ Health Checks (Local)
```bash
docker-compose up --build
```
- [ ] Backend service running (port 8000)
- [ ] Frontend service running (port 3000)
- [ ] Redis container running
- [ ] `curl http://localhost:8000/health` returns healthy
- [ ] All services show "healthy" in `docker-compose ps`

### ✓ Functionality Tests
- [ ] API documentation accessible: http://localhost:8000/docs
- [ ] Frontend loads: http://localhost:3000
- [ ] Test API with: `bash test-api.sh`
- [ ] All endpoints respond (200 or expected status)

---

## Supabase Configuration

### ✓ Database Setup
- [ ] Created Supabase project
- [ ] All tables created from SUPABASE_SETUP.md
- [ ] Indexes created for performance
- [ ] Row-Level Security (RLS) enabled
- [ ] Test connection: `curl -H "apikey: $KEY" https://url/rest/v1/servers`

### ✓ Authentication
- [ ] Email authentication enabled
- [ ] Magic link email template configured
- [ ] Redirect URL set correctly (localhost for dev)
- [ ] Test login flow works

### ✓ Storage (Optional)
- [ ] Buckets created (ssh-keys, deployments)
- [ ] Storage policies configured
- [ ] Backup retention set

---

## Redis Configuration

### ✓ Local Development
- [ ] Redis running (`redis-cli ping` returns PONG)
- [ ] Port 6379 accessible
- [ ] Connection string correct in `.env.local`
- [ ] No password required (or configured)

### ✓ Data Verification
- [ ] Can set keys: `redis-cli SET test value`
- [ ] Can get keys: `redis-cli GET test`
- [ ] TTL working: `redis-cli EXPIRE test 10`
- [ ] Clean up: `redis-cli DEL test`

---

## Security Review

### ✓ Code Security
- [ ] No hardcoded passwords (search for "password"=")
- [ ] No API keys in source code
- [ ] No SSH keys in repository (.gitignore verified)
- [ ] No credentials in .env.* files (except .example)

### ✓ Environment Security
- [ ] `.env.local` added to .gitignore ✓
- [ ] `.env.production` created with security notes
- [ ] All env vars are templates/examples
- [ ] CORS whitelist configured (not allow_all)

### ✓ Database Security
- [ ] Supabase RLS policies enabled ✓
- [ ] Strong database password set
- [ ] No public URLs exposed
- [ ] API keys have appropriate scopes

### ✓ API Security
- [ ] No debug mode in production
- [ ] Error messages don't expose details
- [ ] Rate limiting implemented ✓
- [ ] Command sandboxing active ✓

---

## Production Deployment

### ✓ Pre-Production
- [ ] DEPLOYMENT.md reviewed and understood
- [ ] Choose deployment platform (AWS/GCP/Heroku/K8s)
- [ ] Create production environment
- [ ] Provision Redis instance (or use Docker)
- [ ] Provision PostgreSQL/Supabase (if not using managed)

### ✓ Secrets Management
- [ ] Set up secret management (AWS Secrets/Vault/etc.)
- [ ] Production Supabase URLs and keys configured
- [ ] Production OpenAI key configured
- [ ] Production Redis URL configured
- [ ] SSL certificate obtained

### ✓ Infrastructure
- [ ] Domain name configured
- [ ] SSL/TLS certificate installed
- [ ] Reverse proxy configured (Nginx/Traefik)
- [ ] Load balancer setup (if needed)
- [ ] Database backups automated
- [ ] Logging/monitoring configured

### ✓ Docker Build & Registry
- [ ] Docker images built successfully
- [ ] Images tagged with version number
- [ ] Images pushed to registry (Docker Hub/ECR/GCR)
- [ ] Registry credentials configured
- [ ] Image scanning for vulnerabilities

### ✓ Deployment Platform Setup
**For AWS:**
- [ ] ECS cluster created
- [ ] ECR repositories set up
- [ ] IAM roles/policies configured
- [ ] Load balancer configured
- [ ] Auto-scaling rules set

**For GCP:**
- [ ] Project created
- [ ] Cloud Run service configured
- [ ] Artifact Registry set up
- [ ] Cloud SQL instance created (if needed)
- [ ] Secret Manager configured

**For Kubernetes:**
- [ ] Cluster created and verified
- [ ] kubectl configured
- [ ] Secrets created
- [ ] ConfigMaps created
- [ ] Persistent volumes configured

**For Heroku:**
- [ ] App created
- [ ] Config vars set
- [ ] Procfile configured
- [ ] Buildpack selected

### ✓ DNS & SSL
- [ ] Domain points to load balancer/endpoint
- [ ] SSL certificate valid and installed
- [ ] HTTPS redirect configured
- [ ] DNS propagated (verify with `nslookup`)

### ✓ Database Migration
- [ ] Supabase tables exist in production
- [ ] Indexes created
- [ ] RLS policies enabled
- [ ] Backups configured
- [ ] Data migrated (if applicable)

### ✓ Environment Variables (Production)
```bash
# Verify all set on the platform:
SUPABASE_URL=<production-url>
SUPABASE_ANON_KEY=<production-key>
SUPABASE_ACCESS_TOKEN=<production-token>
OPENAI_API_KEY=<production-key>
REDIS_URL=<production-redis>
NEXT_PUBLIC_SUPABASE_URL=<production-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<production-key>
NEXT_PUBLIC_API_URL=https://api.thinksync.art
CORS_ALLOW_ORIGINS=https://app.thinksync.art
CORS_ALLOW_ORIGIN_REGEX=
ENVIRONMENT=production
DEBUG=false
```

### ✓ Health Checks Setup
- [ ] `/health` endpoint monitored
- [ ] Health check frequency: 30 seconds
- [ ] Restart policy: auto-restart on failure
- [ ] Alerts configured for unhealthy services

### ✓ Logging & Monitoring
- [ ] Log aggregation configured (CloudWatch/Stack Driver/etc.)
- [ ] Error tracking enabled (Sentry/DataDog/etc.)
- [ ] Dashboard created for key metrics
- [ ] Alerts configured for critical issues

### ✓ Deployment Verification
- [ ] Application deployed successfully
- [ ] All services healthy
- [ ] Frontend accessible via domain
- [ ] API responding with correct CORS headers
- [ ] Database connection verified
- [ ] Redis connection verified
- [ ] Authentication working (magic link email)

### ✓ Smoke Tests (Production)
```bash
# Test health
curl https://api.thinksync.art/health

# Test CORS
curl -H "Origin: https://app.thinksync.art" https://api.thinksync.art/

# Test frontend
curl https://app.thinksync.art

# Test API
curl -X POST https://api.thinksync.art/auth/login
```

---

## Post-Deployment

### ✓ Monitoring Setup
- [ ] Application monitoring active
- [ ] Error rate < 1%
- [ ] Response time < 1 second (p95)
- [ ] Database queries optimized
- [ ] Redis cache hit rate > 70%

### ✓ Backup & Recovery
- [ ] Database backups running daily
- [ ] Redis backups automated
- [ ] Backup restoration tested
- [ ] Recovery time objective (RTO) < 1 hour
- [ ] Recovery point objective (RPO) < 15 minutes

### ✓ Security Audit (Post-Deploy)
- [ ] Disable SSH root login
- [ ] Security group rules reviewed
- [ ] WAF rules configured (if applicable)
- [ ] Rate limiting tested
- [ ] Command injection protection verified
- [ ] SQL injection protection verified
- [ ] OWASP top 10 mitigated

### ✓ Documentation
- [ ] Runbook created for common issues
- [ ] Scaling procedures documented
- [ ] Rollback procedures documented
- [ ] Incident response plan created
- [ ] Team trained on deployment

### ✓ Performance Tuning
- [ ] Database connection pooling optimized
- [ ] Redis eviction policy reviewed
- [ ] CDN configured for static assets
- [ ] Database query optimization complete
- [ ] Caching strategy validated

---

## Rollback Plan

### ✓ Documented Procedures
- [ ] Previous version tagged in Git
- [ ] Docker images kept in registry
- [ ] Database rollback strategy
- [ ] Rollback tested (at least documented)
- [ ] Rollback time: < 5 minutes

### ✓ Testing Rollback
- [ ] Rollback procedure documented
- [ ] Previous database state recoverable
- [ ] Communication plan for rollback
- [ ] Approval process defined

---

## Sign-Off

- [ ] All checks verified
- [ ] Team lead approval
- [ ] Security team approval (if required)
- [ ] Product team confirmation (production ready)

---

## Maintenance Schedule

- [ ] Daily: Monitor health checks
- [ ] Weekly: Review logs and metrics
- [ ] Weekly: Backup verification
- [ ] Monthly: Security updates
- [ ] Monthly: Performance review
- [ ] Quarterly: Full security audit

---

## Contact & Escalation

- **On-Call Engineer**: _____________
- **Team Lead**: _____________
- **DevOps**: _____________
- **Slack Channel**: _____________
- **Emergency Hotline**: _____________

---

## Timeline

- **Local Testing**: 2-4 hours
- **Infrastructure Setup**: 2-4 hours
- **Deployment**: 1-2 hours
- **Verification**: 1 hour
- **Total**: 6-11 hours

**Estimated Go-Live**: ___________

---

## Notes

```
[Space for deployment notes and observations]
```

---

**Checklist Created**: 2026-03-09
**Last Updated**: _____________
**Deployed By**: _____________
**Deployment Date**: _____________
