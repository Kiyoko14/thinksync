"""
Real-time log streaming via Server-Sent Events (SSE).

GET /logs/stream/{server_id}   — live SSH log tail (EventSource-compatible)
GET /logs/history/{server_id}  — paginated log history from Redis + Supabase

Redis is used as:
  • A pub/sub subscriber: pipeline and agent events are forwarded to SSE clients
  • A ring buffer (list) for recent raw log lines: logs:raw:{server_id}

Supabase is used for durable log storage: server_logs table.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from config import redis_client, supabase
from routers.auth import get_current_user
from services.pipeline import PIPELINE_EVENTS_CHANNEL
from agents.memory import AGENT_EVENTS_CHANNEL

router = APIRouter(prefix="/logs", tags=["logs"])

_RAW_LOG_TTL = 3_600          # 1 h ring buffer per server
_RAW_LOG_MAX = 2_000          # keep last 2 000 lines per server


def _raw_key(server_id: str) -> str:
    return f"logs:raw:{server_id}"


def _append_raw_log(server_id: str, line: str) -> None:
    """Append a log line to the Redis ring buffer and Supabase."""
    if redis_client:
        try:
            key = _raw_key(server_id)
            entry = json.dumps({"line": line, "ts": time.time()})
            pipe = redis_client.pipeline()
            pipe.rpush(key, entry)
            pipe.ltrim(key, -_RAW_LOG_MAX, -1)
            pipe.expire(key, _RAW_LOG_TTL)
            pipe.execute()
        except Exception as e:
            print(f"_append_raw_log redis error: {e}")

    if supabase:
        try:
            supabase.table("server_logs").insert({
                "server_id": server_id,
                "line": line[:4000],
            }).execute()
        except Exception:
            pass   # non-fatal


# ── SSE generator helpers ─────────────────────────────────────────────────────

def _sse(data: str, event: Optional[str] = None) -> str:
    """Format a Server-Sent Events message."""
    if event:
        return f"event: {event}\ndata: {data}\n\n"
    return f"data: {data}\n\n"


async def _ssh_tail_generator(
    server_id: str,
    server_config: dict,
    log_file: str,
    lines: int,
) -> AsyncGenerator[str, None]:
    """
    Tail a remote log file via SSH and yield SSE lines.
    Falls back to an event-stream comment every 15 s if SSH is unavailable.
    """
    from collections import deque
    from services.execution import ExecutionSandbox

    sandbox = ExecutionSandbox()
    # Bounded deque prevents unbounded memory growth during long-lived streams
    seen_lines: deque = deque(maxlen=2000)

    while True:
        try:
            result = await sandbox._run_ssh_command(
                f"tail -n {lines} {log_file} 2>&1",
                server_config,
                timeout=10,
            )
            output = (result.get("output") or "").strip()
            if output:
                seen_set = set(seen_lines)
                for raw_line in output.splitlines():
                    if raw_line not in seen_set:
                        seen_lines.append(raw_line)
                        seen_set.add(raw_line)
                        _append_raw_log(server_id, raw_line)
                        yield _sse(json.dumps({"server_id": server_id, "line": raw_line}), event="log")
        except Exception as exc:
            yield _sse(json.dumps({"error": str(exc)}), event="error")

        # Keep-alive comment
        yield ": keep-alive\n\n"
        await asyncio.sleep(5)


async def _redis_pubsub_generator(
    server_id: str,
    channels: list,
) -> AsyncGenerator[str, None]:
    """
    Subscribe to Redis pub/sub channels and forward matching events as SSE.
    Reconnects automatically if Redis is unavailable.
    """
    if not redis_client:
        # Emit a keep-alive every 15 s when Redis is not available
        while True:
            yield ": keep-alive\n\n"
            await asyncio.sleep(15)
        return

    try:
        pubsub = redis_client.pubsub()
        pubsub.subscribe(*channels)
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("data"):
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    payload = json.loads(data)
                    yield _sse(data, event=payload.get("type", "event"))
                except Exception:
                    yield _sse(data, event="event")

            yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)
    except Exception as exc:
        yield _sse(json.dumps({"error": str(exc)}), event="error")
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/stream/{server_id}")
async def stream_logs(
    server_id: str,
    log_file: str = Query("/var/log/syslog", description="Remote log file path"),
    lines: int = Query(50, ge=1, le=500, description="Lines to fetch per poll"),
    current_user: dict = Depends(get_current_user),
):
    """
    Stream log lines from a remote server via SSH + SSE.
    Connect with EventSource in the browser:

        const es = new EventSource('/logs/stream/{server_id}?log_file=/var/log/nginx/access.log');
        es.addEventListener('log', e => console.log(JSON.parse(e.data).line));
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    resp = (
        supabase.table("servers")
        .select("*")
        .eq("id", server_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Server not found")

    server = resp.data[0]
    server_config = {
        "host": server["host"],
        "port": int(server.get("ssh_port") or 22),
        "username": server.get("ssh_user"),
        "ssh_auth_method": server.get("ssh_auth_method", "private_key"),
        "ssh_key": server.get("ssh_key"),
        "ssh_password": server.get("ssh_password"),
    }

    return StreamingResponse(
        _ssh_tail_generator(server_id, server_config, log_file, lines),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/events")
async def stream_events(
    current_user: dict = Depends(get_current_user),
):
    """
    Stream all agent + pipeline lifecycle events via SSE.
    Listens on the ``agent:events`` and ``pipeline:events`` Redis channels.
    """
    return StreamingResponse(
        _redis_pubsub_generator(
            server_id="*",
            channels=[AGENT_EVENTS_CHANNEL, PIPELINE_EVENTS_CHANNEL],
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{server_id}", response_model=dict)
async def get_log_history(
    server_id: str,
    limit: int = Query(200, ge=1, le=2000),
    current_user: dict = Depends(get_current_user),
):
    """
    Return recent log lines for a server.

    Primary:  Redis ring buffer (latest N lines, sub-ms).
    Fallback: Supabase server_logs table.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    resp = (
        supabase.table("servers")
        .select("id")
        .eq("id", server_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Server not found")

    lines = []
    if redis_client:
        try:
            raw = redis_client.lrange(_raw_key(server_id), -limit, -1)
            lines = [json.loads(r) for r in raw]
        except Exception as e:
            print(f"get_log_history redis error: {e}")

    if not lines and supabase:
        try:
            db_resp = (
                supabase.table("server_logs")
                .select("line,created_at")
                .eq("server_id", server_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            lines = [{"line": r["line"], "ts": r["created_at"]} for r in reversed(db_resp.data or [])]
        except Exception as e:
            print(f"get_log_history supabase error: {e}")

    return {"server_id": server_id, "lines": lines, "count": len(lines)}
