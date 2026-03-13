import os
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import supabase, redis_client, openai_client, _int_env


# ── Runtime tunables (configurable via environment variables) ─────────────────
_REQUEST_TIMEOUT: int = _int_env("REQUEST_TIMEOUT", 60)
_RATE_LIMIT_PER_MINUTE: int = _int_env("RATE_LIMIT_PER_MINUTE", 120)


# ── Request timeout middleware ────────────────────────────────────────────────
# Prevents hung requests (slow SSH, slow Supabase, slow OpenAI) from tying up
# workers indefinitely.  Long-running intentional operations (SSE streams,
# pipelines) should be kicked off as background tasks.

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Cancel requests that take longer than *timeout_seconds* seconds."""

    def __init__(self, app, timeout_seconds: int = 60) -> None:
        super().__init__(app)
        self.timeout = timeout_seconds

    async def dispatch(self, request: Request, call_next):
        # SSE endpoints are long-lived — skip timeout for them
        if request.url.path.startswith("/logs/"):
            return await call_next(request)
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out. Please retry."},
            )


# ── Lifespan: warm connections on startup ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Verify Redis is reachable on startup (fail fast, don't silently degrade)
    if redis_client:
        try:
            redis_client.ping()
            print("✓ Redis connection verified on startup")
        except Exception as e:
            print(f"⚠ Redis ping failed on startup: {e}")
    yield
    # Graceful shutdown — nothing to close for sync Redis / Supabase clients


app = FastAPI(title="AI DevOps Platform", version="1.0.0", lifespan=lifespan)

# CORS Configuration — allow production, local development, and Replit domains
_replit_domain = os.getenv("REPLIT_DEV_DOMAIN", "")
allowed_origins = [
    "https://app.thinksync.art",
    "https://thinksync.art",
    # Local development origins
    "http://localhost:3000",
    "http://localhost:5000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000",
    *(
        [f"https://{_replit_domain}"]
        if _replit_domain else []
    ),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Performance & resilience middleware (applied outermost → innermost) ───────
# GZip compresses responses > 1 KB (JSON lists, log history, etc.)
app.add_middleware(GZipMiddleware, minimum_size=1_000)

# Request timeout — cancel slow requests before they exhaust worker capacity
# Controlled via REQUEST_TIMEOUT env var (default: 60 s)
app.add_middleware(TimeoutMiddleware, timeout_seconds=_REQUEST_TIMEOUT)

# Rate limiter — per-IP fixed-window via Redis
# Controlled via RATE_LIMIT_PER_MINUTE env var (default: 120)
from services.limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=_RATE_LIMIT_PER_MINUTE)

@app.get("/")
async def root():
    return {"message": "AI DevOps Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    redis_ok = False
    if redis_client:
        try:
            redis_client.ping()
            redis_ok = True
        except Exception:
            pass

    health_status = {
        "status": "healthy",
        "database": "connected" if supabase else "disconnected",
        "redis": "connected" if redis_ok else ("configured_but_unreachable" if redis_client else "disconnected"),
        "openai": "configured" if openai_client else "not_configured",
        "pid": os.getpid(),
    }
    return health_status

# Include routers
from routers import auth, servers, chats, agents, database, deployments, tasks, messages
from routers import pipelines, monitor, secrets, logs
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(agents.router)
app.include_router(database.router)
app.include_router(deployments.router)
app.include_router(tasks.router)
app.include_router(pipelines.router)
app.include_router(monitor.router)
app.include_router(secrets.router)
app.include_router(logs.router)
