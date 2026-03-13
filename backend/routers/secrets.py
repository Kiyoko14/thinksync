"""
Secrets / environment-variable management.

Secrets are stored as rows in the Supabase ``server_secrets`` table.
The latest set of secrets for a server is cached in Redis as a hash
(key: ``secrets:{server_id}``) for sub-ms reads by agents and pipelines.

The actual values are stored in Supabase and only ever transmitted over
TLS; Redis only caches name→value pairs in the same way env vars are used.

Routes:
  GET    /secrets/{server_id}         — list all secret names (values redacted)
  POST   /secrets/{server_id}         — create / upsert a secret
  DELETE /secrets/{server_id}/{name}  — delete a secret
  GET    /secrets/{server_id}/env     — return full map for internal use (auth-gated)
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List

from config import supabase, redis_client
from routers.auth import get_current_user

router = APIRouter(prefix="/secrets", tags=["secrets"])

_CACHE_TTL = 300   # 5-minute Redis cache for secret maps

# ── Helpers ───────────────────────────────────────────────────────────────────

def _cache_key(server_id: str) -> str:
    return f"secrets:{server_id}"


def _invalidate_cache(server_id: str) -> None:
    if redis_client:
        try:
            redis_client.delete(_cache_key(server_id))
        except Exception:
            pass


def _warm_cache(server_id: str, env_map: Dict[str, str]) -> None:
    if redis_client:
        try:
            redis_client.setex(_cache_key(server_id), _CACHE_TTL, json.dumps(env_map))
        except Exception:
            pass


def _read_cache(server_id: str) -> Dict[str, str] | None:
    if redis_client:
        try:
            raw = redis_client.get(_cache_key(server_id))
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    return None


def _load_env_map(server_id: str, user_id: str) -> Dict[str, str]:
    """Return {name: value} for all secrets of this server.

    Uses Redis cache first; falls back to Supabase and warms the cache.
    """
    cached = _read_cache(server_id)
    if cached is not None:
        return cached

    if not supabase:
        return {}
    try:
        resp = (
            supabase.table("server_secrets")
            .select("name,value")
            .eq("server_id", server_id)
            .eq("user_id", user_id)
            .execute()
        )
        env_map = {row["name"]: row["value"] for row in (resp.data or [])}
        _warm_cache(server_id, env_map)
        return env_map
    except Exception as e:
        print(f"secrets._load_env_map error: {e}")
        return {}


def _assert_server_access(server_id: str, user_id: str) -> None:
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    resp = (
        supabase.table("servers")
        .select("id")
        .eq("id", server_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Server not found")


# ── Models ────────────────────────────────────────────────────────────────────

class UpsertSecretRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    value: str = Field(max_length=4096)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{server_id}", response_model=List[dict])
async def list_secrets(
    server_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List secret names for a server (values are redacted)."""
    _assert_server_access(server_id, current_user["id"])
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    resp = (
        supabase.table("server_secrets")
        .select("id,name,created_at,updated_at")
        .eq("server_id", server_id)
        .eq("user_id", current_user["id"])
        .order("name")
        .execute()
    )
    return resp.data or []


@router.post("/{server_id}", response_model=dict)
async def upsert_secret(
    server_id: str,
    request: UpsertSecretRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create or update a secret (upsert by name)."""
    _assert_server_access(server_id, current_user["id"])
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Try update first; insert if not found
    resp = (
        supabase.table("server_secrets")
        .select("id")
        .eq("server_id", server_id)
        .eq("user_id", current_user["id"])
        .eq("name", request.name)
        .execute()
    )

    try:
        if resp.data:
            # Update existing
            result = (
                supabase.table("server_secrets")
                .update({"value": request.value})
                .eq("id", resp.data[0]["id"])
                .execute()
            )
            row = result.data[0]
        else:
            # Insert new
            result = supabase.table("server_secrets").insert({
                "server_id": server_id,
                "user_id": current_user["id"],
                "name": request.name,
                "value": request.value,
            }).execute()
            row = result.data[0]

        _invalidate_cache(server_id)
        return {"id": row["id"], "name": row["name"], "message": "Secret saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save secret: {e}")


@router.delete("/{server_id}/{name}")
async def delete_secret(
    server_id: str,
    name: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a secret by name."""
    _assert_server_access(server_id, current_user["id"])
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    supabase.table("server_secrets").delete().eq("server_id", server_id).eq(
        "user_id", current_user["id"]
    ).eq("name", name).execute()
    _invalidate_cache(server_id)
    return {"message": f"Secret '{name}' deleted"}


@router.get("/{server_id}/env", response_model=dict)
async def get_env_map(
    server_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Return the full name→value map for this server's secrets.
    Used internally by pipelines and agents.  Cached in Redis (5 min).
    """
    _assert_server_access(server_id, current_user["id"])
    return _load_env_map(server_id, current_user["id"])
