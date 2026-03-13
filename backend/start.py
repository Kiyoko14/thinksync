"""
Uvicorn startup script — all tunables configurable via environment variables.

Every important uvicorn/concurrency setting can be overridden at runtime by
setting the corresponding environment variable.  Sane defaults are provided
for production use with ~1 000 concurrent users.

Environment variables
---------------------
WEB_CONCURRENCY          int   Number of uvicorn worker processes (default: 4)
UVICORN_HOST             str   Bind host (default: 0.0.0.0)
UVICORN_PORT             int   Bind port (default: 8000)
UVICORN_TIMEOUT_KEEP_ALIVE int Keep-alive timeout in seconds (default: 30)
UVICORN_ACCESS_LOG       bool  Enable access logging (default: true)
UVICORN_LOG_LEVEL        str   Log level: debug/info/warning/error (default: info)
REQUEST_TIMEOUT          int   Per-request wall-clock timeout in seconds (default: 60)
RATE_LIMIT_PER_MINUTE    int   Max requests per IP per 60-s window (default: 120)
OPENAI_CONCURRENCY       int   Max parallel OpenAI calls (default: 20)
SSH_CONCURRENCY          int   Max parallel SSH connections (default: 50)
"""

import os
import sys
import multiprocessing

import uvicorn


def _int_env(name: str, default: int) -> int:
    val = os.getenv(name, "")
    if val.strip().isdigit():
        return int(val.strip())
    return default


def _bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name, "").strip().lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


if __name__ == "__main__":
    # ── Worker count ──────────────────────────────────────────────────────────
    # Default: 4 workers.  Override with WEB_CONCURRENCY env var.
    # Rule of thumb: 2 × CPU cores + 1 (for I/O-heavy workloads).
    cpu_count = multiprocessing.cpu_count()
    default_workers = max(2, min(cpu_count * 2 + 1, 8))  # cap at 8 by default
    workers = _int_env("WEB_CONCURRENCY", default_workers)

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = _int_env("UVICORN_PORT", 8000)
    timeout_keep_alive = _int_env("UVICORN_TIMEOUT_KEEP_ALIVE", 30)
    access_log = _bool_env("UVICORN_ACCESS_LOG", True)
    log_level = os.getenv("UVICORN_LOG_LEVEL", "info").lower()

    print(
        f"🚀 Starting ThinksSync backend: "
        f"workers={workers}, host={host}, port={port}, "
        f"keep_alive={timeout_keep_alive}s, log_level={log_level}"
    )

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=workers,
        timeout_keep_alive=timeout_keep_alive,
        access_log=access_log,
        log_level=log_level,
        # Reload only in dev mode
        reload=os.getenv("ENVIRONMENT", "production") == "development",
    )
