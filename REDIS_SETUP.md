# Redis Setup Guide

This guide walks you through setting up Redis for ThinkSync.

## Quick Start (Docker)

The easiest way is to use Docker Compose which automatically sets up Redis:

```bash
docker-compose up -d redis
```

Then configure in `.env.local`:
```
REDIS_URL=redis://redis:6379
```

---

## Manual Installation

### Option 1: Ubuntu/Debian

```bash
# Install Redis
sudo apt-get update
sudo apt-get install redis-server

# Start service
sudo systemctl start redis-server
sudo systemctl enable redis-server  # Auto-start on boot

# Verify installation
redis-cli PING  # Should return PONG
```

### Option 2: macOS (with Homebrew)

```bash
# Install Redis
brew install redis

# Start service
brew services start redis

# Verify installation
redis-cli PING
```

### Option 3: Windows

Download from [github.com/microsoftarchive/redis](https://github.com/microsoftarchive/redis/releases)

Or use WSL2 with the Ubuntu instructions above.

---

## Configuration

### Basic Configuration (`.env.local`)

```bash
# For local development
REDIS_URL=redis://localhost:6379

# For Docker
REDIS_URL=redis://redis:6379

# With authentication (optional)
REDIS_URL=redis://:password@localhost:6379

# With database selection (optional)
REDIS_URL=redis://localhost:6379/1
```

### Redis Configuration File

Create `/etc/redis/redis.conf` (on Linux) or edit the default config:

```conf
# Network
bind 127.0.0.1
port 6379

# Authentication (optional)
requirepass yourpassword

# Memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1        # Save after 900 seconds if 1 key changed
save 300 10       # Save after 300 seconds if 10 keys changed
save 60 10000     # Save after 60 seconds if 10000 keys changed

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Database
databases 16
```

Apply configuration:
```bash
sudo systemctl restart redis-server
```

---

## Security Configuration

### Enable Password Authentication

Edit `/etc/redis/redis.conf`:
```conf
requirepass your-strong-password-here
```

Update `.env.local`:
```bash
REDIS_URL=redis://:your-strong-password-here@localhost:6379
```

### Network Security

For production, restrict Redis to internal network only:

```conf
# /etc/redis/redis.conf
bind 127.0.0.1  # or internal IP only
# Don't expose to 0.0.0.0
```

### Firewall Rules
```bash
# UFW (Ubuntu)
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 6379

# iptables
sudo iptables -A INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6379 -j DROP
```

---

## Data Persistence

### Backup Redis Data

```bash
# Create data backup
redis-cli BGSAVE

# Check backup status
redis-cli LASTSAVE

# Manual backup (blocking)
redis-cli SAVE
```

### Backup Location
- Default: `/var/lib/redis/dump.rdb`
- Configure: `dir /path/to/backup` in redis.conf

### Automated Backup Script

```bash
#!/bin/bash
# backup-redis.sh

BACKUP_DIR="/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/dump_$DATE.rdb"

# Keep only last 7 days
find $BACKUP_DIR -name "dump_*.rdb" -mtime +7 -delete
```

Schedule with cron:
```bash
0 2 * * * /path/to/backup-redis.sh  # Daily at 2 AM
```

---

## Monitoring

### Redis CLI Tools

```bash
# Connect to Redis
redis-cli

# Ping server
redis-cli ping

# Get info
redis-cli INFO

# Monitor commands in real-time
redis-cli MONITOR

# Get memory stats
redis-cli INFO memory

# Get key count
redis-cli DBSIZE

# Search keys (careful on large datasets)
redis-cli KEYS "*"
redis-cli KEYS "task:*"
redis-cli KEYS "rate:*"
```

### Redis Statistics

```bash
# Get all stats
redis-cli INFO

# Specific sections
redis-cli INFO server      # Server information
redis-cli INFO clients     # Client connections
redis-cli INFO memory      # Memory usage
redis-cli INFO stats       # Statistics
redis-cli INFO cpu         # CPU usage
redis-cli INFO replication # Replication info
```

### Monitor Command Usage

```bash
# Watch all commands being executed
redis-cli MONITOR

# Watch specific key pattern
redis-cli MONITOR | grep "task:"
```

---

## Troubleshooting

### Connection Error: "Connection refused"

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Start if not running
sudo systemctl start redis-server

# Test connection
redis-cli ping  # Should return PONG
```

### Authentication Error: "NOAUTH"

```bash
# Connect with password
redis-cli -a yourpassword

# Or use environment variable
export REDISPASS=yourpassword
redis-cli -a $REDISPASS
```

### Memory Warning

```bash
# Check memory usage
redis-cli INFO memory

# If using too much:
# 1. Increase maxmemory in redis.conf
# 2. Change eviction policy: maxmemory-policy allkeys-lru
# 3. Clear old data with TTL
redis-cli FLUSHDB  # Careful! Clears current database

# Set TTL (Time To Live) on keys
redis-cli EXPIRE mykey 3600  # Expires in 1 hour
redis-cli TTL mykey          # Check TTL
```

### Persistence Issues

```bash
# If dump.rdb is corrupted
redis-cli --rdb /tmp/dump.rdb  # Try to create new dump

# Restore from backup
sudo systemctl stop redis-server
sudo cp /backups/redis/dump_backup.rdb /var/lib/redis/dump.rdb
sudo systemctl start redis-server
```

---

## ThinkSync Specific Usage

### Data Structure

ThinkSync uses Redis for:

```python
# Task storage
task:{task_id} -> JSON serialized task

# Rate limiting
rate:{chat_id} -> Rate limit flag (1 second)

# Execution logs
execution_log:{chat_id}:{action_id} -> Execution result (1 hour TTL)
```

### Monitoring ThinkSync Operations

```bash
# Watch task progress
redis-cli MONITOR | grep "task:"

# Check rate limiting
redis-cli KEYS "rate:*"

# Get task details
redis-cli GET "task:12345678-1234-1234-1234-123456789012"

# Clear specific task
redis-cli DEL "task:12345678-1234-1234-1234-123456789012"
```

---

## Performance Tuning

### Optimize for ThinkSync

```conf
# /etc/redis/redis.conf

# Memory settings
maxmemory 2gb
maxmemory-policy allkeys-lru

# Network
timeout 300
tcp-keepalive 60

# Persistence (for task state)
save 60 1000

# Slow log monitoring
slowlog-log-slower-than 10000  # microseconds
slowlog-max-len 128
```

### Connection Pooling

The Python Redis client will handle connection pooling automatically.
Configure in your application if needed:

```python
import redis
from redis import ConnectionPool

pool = ConnectionPool.from_url(
    os.getenv("REDIS_URL"),
    max_connections=50,
    decode_responses=True
)
redis_client = redis.Redis(connection_pool=pool)
```

---

## Docker Configuration

### Docker Compose Service

Already configured in `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  container_name: thinksync-redis
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
  volumes:
    - redis-data:/data
```

### Custom Redis Docker Setup

```dockerfile
# Dockerfile.redis
FROM redis:7-alpine

COPY redis.conf /usr/local/etc/redis/redis.conf
RUN chmod 644 /usr/local/etc/redis/redis.conf

CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
```

---

## Testing Redis Connection

### From Backend

```bash
# Test connection
cd backend
python3 -c "
import redis
from config import redis_client
if redis_client:
    print('Connected:', redis_client.ping())
else:
    print('Redis not configured')
"
```

### Testing Script

```bash
#!/bin/bash
# test-redis.sh

REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

echo "Testing Redis connection..."
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping

if [ $? -eq 0 ]; then
    echo "✓ Redis is running"
else
    echo "✗ Redis is not responding"
    exit 1
fi
```

---

## Scaling Redis

### Standalone to Replication

For high availability, set up Redis Replication:

**Master** (`redis-master.conf`):
```conf
port 6379
bind 0.0.0.0
requirepass masterpass
```

**Slave** (`redis-slave.conf`):
```conf
port 6379
bind 0.0.0.0
requirepass slavepass
slaveof master-host 6379
masterauth masterpass
```

### Redis Cluster

For distributed caching:

```bash
# Create cluster nodes
for i in {1..6}; do
  redis-server --port 700$i --cluster-enabled yes --cluster-config-file node-700$i.conf
done

# Create cluster
redis-cli --cluster create 127.0.0.1:7001 127.0.0.1:7002 \
          127.0.0.1:7003 127.0.0.1:7004 \
          127.0.0.1:7005 127.0.0.1:7006 --cluster-replicas 1
```

---

## Production Checklist

- [ ] Redis running on secure port (not 0.0.0.0)
- [ ] Redis password configured
- [ ] Persistent storage enabled (RDB/AOF)
- [ ] Automated backups configured
- [ ] Monitoring/alerting set up
- [ ] Memory limits configured
- [ ] Eviction policy set to allkeys-lru
- [ ] Replication or clustering for HA
- [ ] Firewall rules restricting access

---

## Resources

- [Redis Official Docs](https://redis.io/documentation)
- [Redis Configuration](https://redis.io/topics/config)
- [Redis Security](https://redis.io/topics/security)
- [Redis Modules](https://redis.io/modules)
