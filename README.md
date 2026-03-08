# thinksync

AI-powered DevOps platform with intelligent agent orchestration, server deployment, and infrastructure management.

## Overview

ThinkSync is a comprehensive DevOps automation platform powered by AI agents. It helps teams manage infrastructure, deploy applications, and monitor systems through an intelligent chat interface.

## Features

- 🤖 AI-powered infrastructure management with multi-agent orchestration
- 🚀 Multi-server deployment support with various strategies
- 💬 Interactive chat interface for infrastructure management
- 🗄️ Database management with Supabase PostgreSQL
- 📊 Real-time task execution and monitoring with Redis
- 🔐 Secure SSH connectivity and command execution
- ⚡ Health monitoring and auto-recovery
- 🛡️ Command sandboxing and security measures

## Tech Stack

### Backend
- **Framework**: FastAPI 0.104.1
- **Database**: Supabase (PostgreSQL)
- **Cache**: Redis 5.0.1
- **AI**: OpenAI API
- **Server Communication**: Paramiko (SSH)
- **Authentication**: Python-Jose with encryption

### Frontend
- **Framework**: Next.js 14
- **UI Components**: React
- **Database Client**: Supabase JS 2.98.0
- **Styling**: TailwindCSS

## Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.12+ (for local development)
- Node.js 20+ (for local development)
- Supabase account (free tier available)
- OpenAI API key
- Redis (or use Docker)

## Quick Start with Docker

1. **Clone and setup**
```bash
git clone <repository>
cd thinksync
cp .env.example .env.local
```

2. **Configure credentials in `.env.local`**
```env
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_ACCESS_TOKEN=your-access-token
SUPABASE_ORG_ID=your-org-id
OPENAI_API_KEY=your-openai-key
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

3. **Start services**
```bash
docker-compose up --build
```

4. **Access application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Local Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
redis-server  # In another terminal
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Health Check

```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "openai": "configured"
}
```

## Deployment

### Using Docker Compose
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment
- Configure environment variables on the server
- Use health checks for monitoring
- Enable HTTPS with reverse proxy (nginx/traefik)
- Set up database backups for Supabase
- Monitor Redis and API logs

## Security Features

✅ **Implemented**:
- Secure password generation for databases
- SSH key storage and validation
- Command sandboxing with banned command blocks
- Rate limiting on command execution
- Secure credential handling via environment variables
- Type-safe Supabase queries
- Redis connection validation

⚠️ **Configuration Required**:
- Update CORS origins for production domains
- Enable Supabase row-level security
- Configure OAuth providers
- Set up SSL certificates

## Project Structure

```
thinksync/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration & clients
│   ├── requirements.txt      # Python dependencies
│   ├── routers/              # API endpoints
│   ├── models/               # Data models
│   ├── services/             # Business logic
│   ├── agents/               # AI agent orchestration
│   └── database/             # DB utilities
├── frontend/
│   ├── app/                  # Next.js app directory
│   ├── components/           # React components
│   ├── lib/                  # Utilities
│   ├── package.json
│   └── tsconfig.json
├── Dockerfile                # Backend container
├── docker-compose.yml        # Local development setup
└── .env.example              # Environment template
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health status |
| POST | `/auth/login` | Send magic link |
| GET | `/auth/session` | Get current session |
| GET | `/servers` | List servers |
| POST | `/servers` | Create server |
| POST | `/servers/{id}/deploy` | Deploy code |
| GET | `/chats` | List chats |
| POST | `/chats/{id}/messages` | Send message |
| GET | `/deployments` | List deployments |
| GET | `/tasks` | List tasks |

## Troubleshooting

### Services Won't Start
```bash
# Check logs
docker-compose logs -f backend
docker-compose logs -f redis

# Rebuild images
docker-compose build --no-cache
docker-compose up
```

### Connection Errors
- Verify `.env.local` has all required variables
- Check Supabase URL and key are correct
- Ensure Redis and API ports are available
- Check firewall/network settings

### Health Check Failures
```bash
# Test connections
curl http://localhost:8000/health
redis-cli PING
```

## Development

### Running Tests
```bash
cd backend
pytest tests/

cd frontend
npm run test
```

### Code Quality
- Python: Use black, flake8
- TypeScript: Use eslint, prettier

## License

MIT - See LICENSE file

## Support & Contributing

For issues, feature requests, or contributions:
1. Check existing issues on GitHub
2. Provide environment details and error logs
3. Follow the code structure in contributions
4. Add tests for new features

## Changelog

### v1.0.0
- Initial release with multi-agent orchestration
- Supabase and Redis integration
- Docker deployment support
- Health monitoring endpoints
- Security improvements and error handling
