"""
Server health monitoring service.

Metrics are collected via SSH commands and stored in two ways:
  • Redis sorted-set  mon:ts:{server_id}:{metric}   — time-series (score = unix ts)
  • Redis hash        mon:latest:{server_id}          — most-recent snapshot
  • Supabase          server_alerts                   — threshold breaches

Time-series entries are automatically trimmed to 1 h (360 × 10-second samples)
so Redis memory stays bounded without a separate eviction job.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from config import redis_client, supabase

# ── Constants ─────────────────────────────────────────────────────────────────
_TS_WINDOW = 3_600          # keep 1 h of per-metric samples
_LATEST_TTL = 300           # latest snapshot expires after 5 min
_ALERTS_TTL = 86_400        # alert-state key lives 24 h in Redis

# Alert thresholds (can be overridden per-call)
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "cpu_percent": 85.0,
    "mem_percent": 90.0,
    "disk_percent": 80.0,
    "load_1m": 4.0,
}

# SSH commands used to collect each metric
_METRIC_COMMANDS: Dict[str, str] = {
    "cpu_percent": (
        "grep 'cpu ' /proc/stat | "
        "awk '{idle=$5; total=0; for(i=2;i<=NF;i++) total+=$i; "
        "pct=(total-idle)/total*100; printf \"%.1f\", pct}'"
    ),
    "mem_percent": (
        "free | grep Mem | awk '{printf \"%.1f\", ($3/$2)*100}'"
    ),
    "disk_percent": (
        "df / | tail -1 | awk '{print $5}' | tr -d '%'"
    ),
    "load_1m": (
        "cat /proc/loadavg | awk '{print $1}'"
    ),
    "uptime_seconds": (
        "cat /proc/uptime | awk '{print $1}'"
    ),
}


# ── Internal Redis helpers ────────────────────────────────────────────────────

def _ts_key(server_id: str, metric: str) -> str:
    return f"mon:ts:{server_id}:{metric}"


def _latest_key(server_id: str) -> str:
    return f"mon:latest:{server_id}"


def _alert_key(server_id: str) -> str:
    return f"mon:alert:{server_id}"


def _record_sample(server_id: str, metric: str, value: float) -> None:
    """Append one sample to the Redis sorted-set time-series."""
    if not redis_client:
        return
    key = _ts_key(server_id, metric)
    now = time.time()
    try:
        pipe = redis_client.pipeline()
        pipe.zadd(key, {json.dumps({"ts": now, "v": value}): now})
        # trim to last _TS_WINDOW seconds
        pipe.zremrangebyscore(key, "-inf", now - _TS_WINDOW)
        pipe.expire(key, _TS_WINDOW + 60)
        pipe.execute()
    except Exception as e:
        print(f"MonitorService._record_sample error: {e}")


def _get_series(server_id: str, metric: str, since: float) -> List[Dict]:
    """Return time-series samples for a metric since *since* (unix ts)."""
    if not redis_client:
        return []
    key = _ts_key(server_id, metric)
    try:
        raw = redis_client.zrangebyscore(key, since, "+inf")
        return [json.loads(r) for r in raw]
    except Exception as e:
        print(f"MonitorService._get_series error: {e}")
        return []


# ── Public API ────────────────────────────────────────────────────────────────

class MonitorService:
    """Collect, store, and query server health metrics."""

    async def collect(
        self,
        server_id: str,
        server_config: Dict[str, Any],
        thresholds: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        SSH into the server, collect all metrics, store them, check thresholds.

        Returns a snapshot dict with metric values and any triggered alerts.
        """
        from services.execution import ExecutionSandbox

        sandbox = ExecutionSandbox()
        snapshot: Dict[str, float] = {}
        errors: List[str] = []
        active_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

        for metric, command in _METRIC_COMMANDS.items():
            try:
                result = await sandbox._run_ssh_command(
                    command,
                    server_config,
                    timeout=10,
                )
                if result.get("status") == "success":
                    raw_value = result.get("output", "").strip()
                    snapshot[metric] = float(raw_value)
                    _record_sample(server_id, metric, snapshot[metric])
                else:
                    errors.append(f"{metric}: {result.get('error', 'unknown')}")
            except Exception as exc:
                errors.append(f"{metric}: {exc}")

        # ── Store latest snapshot in Redis ────────────────────────────────
        if redis_client and snapshot:
            try:
                redis_client.hset(
                    _latest_key(server_id),
                    mapping={k: json.dumps(v) for k, v in snapshot.items()},
                )
                redis_client.expire(_latest_key(server_id), _LATEST_TTL)
            except Exception as e:
                print(f"MonitorService.collect redis snapshot error: {e}")

        # ── Threshold checks & alert persistence ──────────────────────────
        triggered: List[Dict] = []
        for metric, value in snapshot.items():
            limit = active_thresholds.get(metric)
            if limit and value >= limit:
                alert = {
                    "server_id": server_id,
                    "metric": metric,
                    "value": value,
                    "threshold": limit,
                    "ts": time.time(),
                }
                triggered.append(alert)
                _persist_alert(server_id, alert)

        return {
            "server_id": server_id,
            "metrics": snapshot,
            "alerts": triggered,
            "errors": errors,
            "collected_at": time.time(),
        }

    def get_latest(self, server_id: str) -> Dict[str, Any]:
        """Return the most-recent metrics snapshot (Redis hash, or empty)."""
        if not redis_client:
            return {}
        try:
            raw = redis_client.hgetall(_latest_key(server_id))
            return {k: json.loads(v) for k, v in raw.items()}
        except Exception as e:
            print(f"MonitorService.get_latest error: {e}")
            return {}

    def get_history(
        self,
        server_id: str,
        metric: str,
        minutes: int = 60,
    ) -> List[Dict]:
        """Return up to *minutes* minutes of time-series data from Redis."""
        since = time.time() - minutes * 60
        return _get_series(server_id, metric, since)

    def get_alerts(self, server_id: str, limit: int = 20) -> List[Dict]:
        """Return recent alerts from Supabase (fallback: Redis list)."""
        if supabase:
            try:
                resp = (
                    supabase.table("server_alerts")
                    .select("*")
                    .eq("server_id", server_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                return resp.data or []
            except Exception as e:
                print(f"MonitorService.get_alerts supabase error: {e}")

        # Fallback: read from Redis list
        if redis_client:
            try:
                raw = redis_client.lrange(_alert_key(server_id), 0, limit - 1)
                return [json.loads(r) for r in raw]
            except Exception as e:
                print(f"MonitorService.get_alerts redis error: {e}")
        return []


def _persist_alert(server_id: str, alert: Dict) -> None:
    """Write alert to Supabase and append to Redis list as fallback."""
    if supabase:
        try:
            supabase.table("server_alerts").insert({
                "server_id": alert["server_id"],
                "metric": alert["metric"],
                "value": alert["value"],
                "threshold": alert["threshold"],
            }).execute()
        except Exception as e:
            print(f"_persist_alert supabase error: {e}")

    if redis_client:
        try:
            key = _alert_key(server_id)
            pipe = redis_client.pipeline()
            pipe.lpush(key, json.dumps(alert))
            pipe.ltrim(key, 0, 99)          # keep last 100 alerts per server
            pipe.expire(key, _ALERTS_TTL)
            pipe.execute()
        except Exception as e:
            print(f"_persist_alert redis error: {e}")


monitor_service = MonitorService()
