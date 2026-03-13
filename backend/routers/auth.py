import asyncio
import hashlib
import json
import threading
from collections import OrderedDict

from fastapi import APIRouter, Depends, Header, HTTPException
from supabase import Client
from config import supabase, redis_client
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Optional
from uuid import uuid4
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginResponse(BaseModel):
    token: str
    user: dict

class SessionResponse(BaseModel):
    user_id: str
    email: str
    created_at: str


# ── Bounded in-memory session store (dev/fallback mode only) ─────────────────
# Capped at 5 000 entries so the process never accumulates unbounded RAM when
# Redis/Supabase are unavailable (e.g. local development).
# Thread-safe via an internal threading.Lock (multiple uvicorn workers share
# nothing, but a single worker may have multiple threads from to_thread calls).

class _BoundedSessionStore(OrderedDict):
    """Thread-safe LRU dict capped at *maxsize* entries."""

    def __init__(self, maxsize: int = 5_000) -> None:
        super().__init__()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def __setitem__(self, key, value):
        with self._lock:
            if key in self:
                self.move_to_end(key)
            super().__setitem__(key, value)
            if len(self) > self._maxsize:
                self.popitem(last=False)  # evict oldest

    def __getitem__(self, key):
        with self._lock:
            return super().__getitem__(key)

    def __contains__(self, key):
        with self._lock:
            return super().__contains__(key)

    def __delitem__(self, key):
        with self._lock:
            super().__delitem__(key)


LOCAL_SESSIONS: _BoundedSessionStore = _BoundedSessionStore(maxsize=5_000)

# TTL for caching Supabase JWT validation results in Redis
_AUTH_CACHE_TTL = 300  # 5 minutes


def _auth_cache_key(token: str) -> str:
    digest = hashlib.sha256(token.encode()).hexdigest()[:32]
    return f"auth:user:{digest}"


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    return authorization[len(prefix):].strip()

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Password-based login with local fallback session support."""
    if supabase:
        try:
            response = await asyncio.to_thread(
                supabase.auth.sign_in_with_password,
                {"email": request.email, "password": request.password},
            )
            session = getattr(response, "session", None)
            user = getattr(response, "user", None)

            if not session or not user:
                raise HTTPException(status_code=401, detail="Invalid email or password")

            return LoginResponse(
                token=session.access_token,
                user={
                    "id": str(user.id),
                    "email": user.email or request.email,
                    "created_at": str(user.created_at),
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Supabase login error for {request.email}: {e}")

    token = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": f"local-{request.email}",
        "email": request.email,
        "created_at": now,
    }
    LOCAL_SESSIONS[token] = user
    return LoginResponse(token=token, user=user)

@router.get("/session", response_model=SessionResponse)
async def get_session(authorization: Optional[str] = Header(default=None)):
    """Get current user session"""
    token = _extract_token(authorization)
    if token and token in LOCAL_SESSIONS:
        local_user = LOCAL_SESSIONS[token]
        return SessionResponse(
            user_id=local_user["id"],
            email=local_user["email"],
            created_at=local_user["created_at"],
        )

    if not supabase or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Check Redis cache before hitting Supabase
    cache_key = _auth_cache_key(token)
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                user_dict = json.loads(cached)
                return SessionResponse(
                    user_id=user_dict["id"],
                    email=user_dict["email"],
                    created_at=user_dict["created_at"],
                )
        except Exception:
            pass

    try:
        # Validate the client-supplied JWT against Supabase (non-blocking)
        user_response = await asyncio.to_thread(supabase.auth.get_user, token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please login first."
            )

        user = user_response.user
        user_dict = {
            "id": str(user.id),
            "email": user.email or "",
            "created_at": str(user.created_at),
        }
        # Cache in Redis for future requests
        if redis_client:
            try:
                redis_client.setex(cache_key, _AUTH_CACHE_TTL, json.dumps(user_dict))
            except Exception:
                pass

        return SessionResponse(
            user_id=user_dict["id"],
            email=user_dict["email"],
            created_at=user_dict["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Session error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    supabase_client: Optional[Client] = Depends(lambda: supabase),
) -> dict:
    """
    Dependency to get current authenticated user.

    Hot path optimisation — three layers to avoid hitting Supabase on every request:
    1. In-process LOCAL_SESSIONS dict  (dev / fallback mode)
    2. Redis cache (TTL=5 min)         — sub-ms lookup
    3. Supabase JWT validation          — async thread, result cached in Redis
    """
    token = _extract_token(authorization)
    if token and token in LOCAL_SESSIONS:
        return LOCAL_SESSIONS[token]

    if not supabase_client or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # ── Redis cache check ─────────────────────────────────────────────────────
    cache_key = _auth_cache_key(token)
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass  # Cache miss — fall through to Supabase

    # ── Supabase JWT validation (run in thread pool, non-blocking) ────────────
    try:
        user_response = await asyncio.to_thread(supabase_client.auth.get_user, token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user = user_response.user
        user_dict = {
            "id": str(user.id),
            "email": user.email or "",
            "created_at": str(user.created_at),
        }

        # ── Cache result in Redis ─────────────────────────────────────────────
        if redis_client:
            try:
                redis_client.setex(cache_key, _AUTH_CACHE_TTL, json.dumps(user_dict))
            except Exception:
                pass

        return user_dict
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )

@router.post("/logout")
async def logout(authorization: Optional[str] = Header(default=None)):
    """Logout current user"""
    token = _extract_token(authorization)
    if token and token in LOCAL_SESSIONS:
        del LOCAL_SESSIONS[token]
        return {"message": "Logged out successfully"}

    if not supabase:
        return {"message": "Logged out successfully"}

    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        print(f"Logout error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Logout failed"
        )