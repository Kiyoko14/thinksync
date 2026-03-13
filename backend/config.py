import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv
import redis
from typing import Optional
from openai import OpenAI
from pathlib import Path

# Load .env file if present (Replit secrets take precedence via the environment)
ENV_FILE = Path(__file__).resolve().parent / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=False)

# Supabase
# The backend uses the service role key so it can bypass Row Level Security
# and perform privileged operations.  Fall back to the anon key only when the
# service key is not provided (e.g. in local development without full secrets).
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
if not os.getenv("SUPABASE_SERVICE_KEY") and os.getenv("SUPABASE_ANON_KEY"):
    print("⚠ SUPABASE_SERVICE_KEY not set — falling back to SUPABASE_ANON_KEY (RLS is active)")

supabase: Optional[Client] = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✓ Supabase initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Supabase: {e}")
        supabase = None
else:
    print("⚠ Supabase credentials not found in environment variables")

# Redis / Upstash Redis
# Supports both standard Redis (redis://) and Upstash Redis (rediss://).
# Upstash provides a Redis-compatible endpoint via rediss:// with TLS.
# Set REDIS_URL to your Upstash connection string, e.g.:
#   rediss://default:<TOKEN>@<HOST>.upstash.io:6380
redis_url = os.getenv("REDIS_URL")
redis_client: Optional[redis.Redis] = None
if redis_url:
    try:
        # ssl_cert_reqs=None allows connecting to Upstash and other hosted
        # Redis services that use self-signed or managed TLS certificates.
        _redis_kwargs: dict = {}
        if redis_url.startswith("rediss://"):
            _redis_kwargs["ssl_cert_reqs"] = None
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            max_connections=50,       # connection pool — handle 1 000 concurrent users
            socket_connect_timeout=3, # fail fast if Redis is unreachable
            socket_timeout=3,
            retry_on_timeout=True,
            **_redis_kwargs,
        )
        redis_client.ping()  # Test connection
        _redis_type = "Upstash Redis" if redis_url.startswith("rediss://") else "Redis"
        print(f"✓ {_redis_type} initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Redis: {e}")
        redis_client = None
else:
    print("⚠ REDIS_URL not set — caching and state tracking will use in-memory fallback")

# OpenAI — default model is gpt-4o-mini for cost-efficient agent operations.
# Override via the OPENAI_MODEL environment variable (e.g. gpt-4o for higher quality).
openai_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
openai_client: Optional[OpenAI] = None
if openai_key:
    try:
        openai_client = OpenAI(api_key=openai_key)
        print(f"✓ OpenAI initialized successfully (model: {openai_model})")
    except Exception as e:
        print(f"✗ Failed to initialize OpenAI: {e}")
        openai_client = None
else:
    print("⚠ OpenAI API key not found in environment variables")
# ── Async OpenAI helper ───────────────────────────────────────────────────────
# The standard `openai` SDK uses a synchronous HTTP client which blocks the
# asyncio event loop.  `call_openai` wraps each call in asyncio.to_thread so
# it runs in the thread pool and frees the event loop for other coroutines.
# A semaphore caps concurrent OpenAI requests at 20 to stay within rate limits.

_OPENAI_SEMAPHORE = asyncio.Semaphore(20)


async def call_openai(**kwargs):
    """
    Semaphore-gated, thread-offloaded OpenAI chat completion call.

    Usage:
        response = await call_openai(model="gpt-4o-mini", messages=[...])
        if response:
            text = response.choices[0].message.content
    """
    if not openai_client:
        return None
    async with _OPENAI_SEMAPHORE:
        return await asyncio.to_thread(
            openai_client.chat.completions.create,
            **kwargs,
        )
