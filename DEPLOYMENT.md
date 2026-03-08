# Deployment Guide

## Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Supabase project created and tables set up
- [ ] OpenAI API key generated
- [ ] Redis instance accessible
- [ ] SSL certificates obtained (for production)
- [ ] Domain names configured
- [ ] Backup strategy in place

## Environment Variables Setup

### Required Variables

```bash
# Supabase (get from Supabase dashboard)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_ACCESS_TOKEN=
SUPABASE_ORG_ID=

# OpenAI (get from OpenAI dashboard)
OPENAI_API_KEY=

# Frontend URLs
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Redis
REDIS_URL=redis://localhost:6379

# Server Configuration
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
```

## Docker Deployment

### Step 1: Build Docker Images

```bash
# Build both services
docker-compose build

# Or build specific service
docker-compose build backend
docker-compose build frontend
```

### Step 2: Deploy

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check health
curl http://localhost:8000/health
```

### Step 3: Monitor

```bash
# View logs
docker-compose logs -f

# Restart service if needed
docker-compose restart backend
docker-compose restart frontend
```

## Kubernetes Deployment

### Prerequisites
- kubectl configured
- Docker images pushed to registry

### Deploy Steps

```bash
# Create namespace
kubectl create namespace thinksync

# Create secrets
kubectl create secret generic thinksync-secrets \
  --from-literal=SUPABASE_URL=$SUPABASE_URL \
  --from-literal=SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY \
  --from-literal=OPENAI_API_KEY=$OPENAI_API_KEY \
  --from-literal=REDIS_URL=$REDIS_URL \
  -n thinksync

# Apply manifests
kubectl apply -f k8s/ -n thinksync

# Verify deployment
kubectl get pods -n thinksync
kubectl get svc -n thinksync
```

## Cloud Deployment

### AWS Deployment

#### Option 1: ECS (Elastic Container Service)
```bash
# Push images to ECR
aws ecr create-repository --repository-name thinksync-backend
aws ecr create-repository --repository-name thinksync-frontend

docker tag thinksync-backend:latest [ECR_URI]/thinksync-backend:latest
docker push [ECR_URI]/thinksync-backend:latest
```

#### Option 2: Elastic Beanstalk
```bash
# Initialize EB
eb init -p docker thinksync

# Deploy
eb create thinksync-env
eb deploy
```

### Google Cloud Deployment (Cloud Run)

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/thinksync-backend
gcloud builds submit --tag gcr.io/PROJECT_ID/thinksync-frontend

# Deploy
gcloud run deploy thinksync-backend \
  --image gcr.io/PROJECT_ID/thinksync-backend \
  --set-env-vars SUPABASE_URL=$SUPABASE_URL \
  --memory 1Gi \
  --timeout 3600
```

### Heroku Deployment

```bash
# Login and create app
heroku login
heroku create thinksync

# Set environment variables
heroku config:set SUPABASE_URL=$SUPABASE_URL
heroku config:set SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
heroku config:set OPENAI_API_KEY=$OPENAI_API_KEY
heroku config:set REDIS_URL=$REDIS_URL

# Deploy
git push heroku main
```

## Reverse Proxy Setup

### Nginx Configuration

```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/thinksync.crt;
    ssl_certificate_key /etc/ssl/private/thinksync.key;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/ssl/certs/thinksync.crt;
    ssl_certificate_key /etc/ssl/private/thinksync.key;

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
    }
}
```

### Update CORS in main.py

```python
allowed_origins = [
    "https://yourdomain.com",
    "https://api.yourdomain.com",
]
```

## Database Setup (Supabase)

### Tables Required

```sql
-- Users table (auto-managed by Supabase Auth)

-- Servers table
CREATE TABLE servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    ssh_user VARCHAR(100),
    ssh_port INT DEFAULT 22,
    ssh_key TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Chats table
CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID REFERENCES servers(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    workspace_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    role VARCHAR(20),
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Deployments table
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID REFERENCES servers(id),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    code TEXT,
    language VARCHAR(50),
    deployment_type VARCHAR(50),
    deployment_script TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    state VARCHAR(50),
    step VARCHAR(100),
    attempts INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Databases table
CREATE TABLE databases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    server_id UUID REFERENCES servers(id),
    project_id VARCHAR(255),
    db_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Enable Row-Level Security

```sql
ALTER TABLE servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view their own servers"
ON servers FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can create servers"
ON servers FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Similar policies for other tables
```

## Redis Setup

### Docker
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### Manual Install
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Start service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test connection
redis-cli PING  # Should return PONG
```

## Health Monitoring

### Check Service Health

```bash
# API Health
curl https://api.yourdomain.com/health

# Should return:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected",
#   "openai": "configured"
# }
```

### Set Up Monitoring

```bash
# Using curl and cron for simple monitoring
0 */5 * * * curl -f https://api.yourdomain.com/health || mail admin@domain.com
```

## Logging & Debugging

### View Logs

```bash
# Docker Compose
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f redis

# Kubernetes
kubectl logs -f deployment/thinksync-backend -n thinksync
```

### Debug Connection Issues

```bash
# Test Supabase connection
curl -H "apikey: $SUPABASE_ANON_KEY" https://your-project.supabase.co/rest/v1/servers

# Test Redis
redis-cli -h localhost ping

# Test OpenAI API
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Backup & Recovery

### Supabase Backup
- Automatic daily backups (free tier)
- Manual backups in Supabase dashboard
- Export data as CSV/JSON

### Redis Backup
```bash
redis-cli BGSAVE  # Background save
redis-cli LASTSAVE  # Check last save time
```

## Scaling

### Horizontal Scaling
- Deploy multiple API instances behind load balancer
- Use Redis for shared session state
- Database connection pooling in production

### Vertical Scaling
- Increase container memory and CPU
- Upgrade Redis instance size
- Upgrade Supabase plan

## SSL Certificate Setup

### Let's Encrypt with Certbot
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d api.yourdomain.com
sudo certbot renew --dry-run
```

## Rollback Procedure

### Docker Rollback
```bash
# Get previous version
docker-compose down
git checkout previous-tag
docker-compose up -d
```

### Kubernetes Rollback
```bash
# Rollback deployment
kubectl rollout undo deployment/thinksync-backend -n thinksync
kubectl rollout status deployment/thinksync-backend -n thinksync
```

## Performance Optimization

1. **Caching**: Use Redis for frequently accessed data
2. **Database**: Add indexes on frequently queried columns
3. **CDN**: Serve static assets from CloudFront/Cloudflare
4. **Rate Limiting**: Implemented in execution.py
5. **Compression**: Enable gzip in reverse proxy

## Production Checklist

- [ ] HTTPS enabled with valid SSL certificate
- [ ] CORS properly configured for your domains
- [ ] Environment variables securely set
- [ ] Database backups automated
- [ ] Monitoring and alerting configured
- [ ] Log aggregation set up
- [ ] Rate limiting tested
- [ ] Security headers configured
- [ ] Database Row-Level Security enabled
- [ ] Regular security updates applied
