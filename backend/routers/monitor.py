"""
Server monitoring router.

GET  /monitor/{server_id}/collect   — SSH collect & store metrics now
GET  /monitor/{server_id}/latest    — latest snapshot from Redis
GET  /monitor/{server_id}/history   — time-series from Redis (sorted sets)
GET  /monitor/{server_id}/alerts    — alert history from Supabase / Redis
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Dict, List, Optional

from config import supabase
from routers.auth import get_current_user
from services.monitor import monitor_service

router = APIRouter(prefix="/monitor", tags=["monitor"])


def _get_server(server_id: str, user_id: str) -> Dict:
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    resp = (
        supabase.table("servers")
        .select("*")
        .eq("id", server_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Server not found")
    return resp.data[0]


def _server_to_config(server: Dict) -> Dict:
    return {
        "host": server["host"],
        "port": int(server.get("ssh_port") or 22),
        "username": server.get("ssh_user") or server.get("username"),
        "ssh_auth_method": server.get("ssh_auth_method", "private_key"),
        "ssh_key": server.get("ssh_key"),
        "ssh_password": server.get("ssh_password"),
    }


@router.post("/{server_id}/collect", response_model=dict)
async def collect_metrics(
    server_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    SSH into the server, collect CPU / RAM / disk / load metrics,
    store them in Redis (time-series + latest hash) and persist any
    threshold breaches to Supabase.
    """
    server = _get_server(server_id, current_user["id"])
    server_config = _server_to_config(server)

    try:
        result = await monitor_service.collect(server_id, server_config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics collection failed: {e}")


@router.get("/{server_id}/latest", response_model=dict)
async def get_latest_metrics(
    server_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return the most-recent metrics snapshot from Redis."""
    _get_server(server_id, current_user["id"])
    data = monitor_service.get_latest(server_id)
    if not data:
        raise HTTPException(
            status_code=404,
            detail="No metrics found. Call /collect first.",
        )
    return {"server_id": server_id, "metrics": data}


@router.get("/{server_id}/history", response_model=dict)
async def get_metrics_history(
    server_id: str,
    metric: str = Query(..., description="Metric name: cpu_percent | mem_percent | disk_percent | load_1m | uptime_seconds"),
    minutes: int = Query(60, ge=1, le=1440, description="How many minutes of history to return"),
    current_user: dict = Depends(get_current_user),
):
    """
    Return time-series data for a single metric from Redis sorted sets.
    Each point: {"ts": unix_timestamp, "v": float_value}
    """
    _get_server(server_id, current_user["id"])
    valid_metrics = {"cpu_percent", "mem_percent", "disk_percent", "load_1m", "uptime_seconds"}
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Choose from: {', '.join(sorted(valid_metrics))}",
        )
    series = monitor_service.get_history(server_id, metric, minutes=minutes)
    return {
        "server_id": server_id,
        "metric": metric,
        "minutes": minutes,
        "points": series,
    }


@router.get("/{server_id}/alerts", response_model=List[dict])
async def get_alerts(
    server_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Return recent threshold-breach alerts (Supabase, Redis fallback)."""
    _get_server(server_id, current_user["id"])
    return monitor_service.get_alerts(server_id, limit=limit)
