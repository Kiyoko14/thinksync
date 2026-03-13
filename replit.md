# ThinkSync - AI DevOps Platform

## Project Overview
AI-powered DevOps platform for managing servers, deployments, databases, and AI chat workflows.

## Architecture
- **Frontend**: Next.js 16 (React 19, Tailwind CSS 4, TypeScript) — runs on port 5000
- **Backend**: FastAPI (Python 3.12, uvicorn) — runs on port 8000

## Directory Structure
```
/
├── frontend/           # Next.js app
│   ├── app/            # App Router pages (dashboard, login, etc.)
│   ├── src/
│   │   ├── lib/        # API client (api.ts, auth.ts)
│   │   ├── context/    # AuthContext
│   │   └── components/ # Shared components (Footer, Navbar, Sidebar)
│   └── package.json
├── backend/            # FastAPI app
│   ├── routers/        # Route handlers (auth, servers, chats, etc.)
│   ├── models/         # Pydantic models
│   ├── services/       # Business logic
│   ├── config.py       # Supabase, Redis, OpenAI initialization
│   └── main.py         # App entry point + CORS
└── package.json        # Root (supabase-js only)
```

## Workflows
- **Start application**: `cd frontend && npm run dev` → port 5000 (webview)
- **Backend API**: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload` → port 8000 (console)

## Required Environment Variables (set as Replit Secrets)
| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_ACCESS_TOKEN` | Supabase management API token (for DB provisioning) |
| `SUPABASE_ORG_ID` | Supabase org ID (for DB provisioning) |
| `REDIS_URL` | Redis connection URL |
| `OPENAI_API_KEY` | OpenAI API key |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL (exposed to frontend) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (exposed to frontend) |
| `NEXT_PUBLIC_API_URL` | Backend URL (e.g. https://your-replit-domain:8000) |

## Key Notes
- Frontend `@/` path alias maps to `frontend/src/`
- Backend config gracefully degrades when secrets are missing (logs warnings, doesn't crash)
- CORS is configured to allow the Replit dev domain automatically via `REPLIT_DEV_DOMAIN` env var
