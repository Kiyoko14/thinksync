"""
CI/CD Pipeline execution engine.

A pipeline is a named, ordered list of stages.  Each stage contains one or
more shell commands that are executed sequentially on a target server via SSH.

State is stored in two places:
  • Redis hash     pipe:run:{run_id}          — hot path, sub-ms reads
  • Supabase       pipeline_runs table        — durable history / audit trail

Each stage transition publishes a Redis pub/sub event on the ``pipeline:events``
channel so WebSocket gateways and monitoring tools receive live updates.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from config import redis_client, supabase
from agents.memory import agent_memory

# ── Constants ─────────────────────────────────────────────────────────────────
_RUN_TTL = 86_400           # keep run state in Redis for 24 h
PIPELINE_EVENTS_CHANNEL = "pipeline:events"

# ── State machine values ───────────────────────────────────────────────────────
class RunStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Redis helpers ─────────────────────────────────────────────────────────────

def _run_key(run_id: str) -> str:
    return f"pipe:run:{run_id}"


def _save_run(run_id: str, data: Dict) -> None:
    if redis_client:
        try:
            redis_client.setex(_run_key(run_id), _RUN_TTL, json.dumps(data))
        except Exception as e:
            print(f"PipelineEngine._save_run redis error: {e}")


def _load_run(run_id: str) -> Optional[Dict]:
    """Load run state; prefer Redis, fall back to Supabase."""
    if redis_client:
        try:
            raw = redis_client.get(_run_key(run_id))
            if raw:
                return json.loads(raw)
        except Exception as e:
            print(f"PipelineEngine._load_run redis error: {e}")

    if supabase:
        try:
            resp = (
                supabase.table("pipeline_runs")
                .select("*")
                .eq("id", run_id)
                .execute()
            )
            if resp.data:
                return resp.data[0]
        except Exception as e:
            print(f"PipelineEngine._load_run supabase error: {e}")
    return None


def _publish(event_type: str, data: Dict) -> None:
    if redis_client:
        try:
            payload = json.dumps({"type": event_type, "ts": time.time(), **data})
            redis_client.publish(PIPELINE_EVENTS_CHANNEL, payload)
        except Exception as e:
            print(f"PipelineEngine._publish error: {e}")


# ── Engine ────────────────────────────────────────────────────────────────────

class PipelineEngine:
    """Execute multi-stage CI/CD pipelines with full Redis + Supabase tracking."""

    async def create_run(
        self,
        pipeline_id: str,
        pipeline_name: str,
        stages: List[Dict],
        server_config: Dict[str, Any],
        triggered_by: str = "manual",
        user_id: str = "",
        chat_id: str = "",
    ) -> str:
        """
        Create a new pipeline run record and return its *run_id*.

        Each stage in *stages* must have:
            name        : str   — human-readable label
            commands    : list  — shell commands to execute in order
            on_failure  : str   — "fail_fast" | "continue" (default: "fail_fast")
            timeout     : int   — seconds per command (default: 120)
        """
        run_id = str(uuid.uuid4())
        run = {
            "id": run_id,
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline_name,
            "user_id": user_id,
            "chat_id": chat_id,
            "triggered_by": triggered_by,
            "status": RunStatus.PENDING,
            "stages": stages,
            "stage_results": [],
            "current_stage": None,
            "server_config": server_config,
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "duration_seconds": None,
        }

        _save_run(run_id, run)

        if supabase:
            try:
                supabase.table("pipeline_runs").insert({
                    "id": run_id,
                    "pipeline_id": pipeline_id,
                    "pipeline_name": pipeline_name,
                    "user_id": user_id or None,
                    "chat_id": chat_id or None,
                    "triggered_by": triggered_by,
                    "status": RunStatus.PENDING,
                    "stage_count": len(stages),
                }).execute()
            except Exception as e:
                print(f"PipelineEngine.create_run supabase error: {e}")

        _publish("run_created", {
            "run_id": run_id,
            "pipeline_name": pipeline_name,
            "user_id": user_id,
            "stage_count": len(stages),
        })

        return run_id

    async def execute_run(self, run_id: str) -> Dict[str, Any]:
        """
        Execute all stages of a pipeline run.

        This method is designed to be awaited directly; for long pipelines
        callers should wrap it in a background task.
        """
        from services.execution import ExecutionSandbox

        run = _load_run(run_id)
        if not run:
            return {"error": f"Run {run_id} not found"}

        sandbox = ExecutionSandbox()
        stages: List[Dict] = run["stages"]
        server_config: Dict = run["server_config"]
        stage_results: List[Dict] = []

        run["status"] = RunStatus.RUNNING
        run["started_at"] = time.time()
        _save_run(run_id, run)
        _publish("run_started", {"run_id": run_id, "pipeline_name": run["pipeline_name"]})

        try:
            for idx, stage in enumerate(stages):
                stage_name = stage.get("name", f"stage_{idx + 1}")
                commands = stage.get("commands", [])
                on_failure = stage.get("on_failure", "fail_fast")
                timeout = int(stage.get("timeout", 120))

                run["current_stage"] = stage_name
                _save_run(run_id, run)
                _publish("stage_started", {
                    "run_id": run_id,
                    "stage": stage_name,
                    "stage_index": idx,
                })

                stage_result: Dict[str, Any] = {
                    "name": stage_name,
                    "index": idx,
                    "status": RunStatus.RUNNING,
                    "command_results": [],
                    "started_at": time.time(),
                    "finished_at": None,
                }
                stage_failed = False

                for cmd in commands:
                    # Check if run was cancelled before each command
                    fresh = _load_run(run_id)
                    if fresh and fresh.get("status") == RunStatus.CANCELLED:
                        stage_result["status"] = RunStatus.CANCELLED
                        stage_results.append(stage_result)
                        run["stage_results"] = stage_results
                        run["status"] = RunStatus.CANCELLED
                        _save_run(run_id, run)
                        _persist_finished_run(run_id, run)
                        return _build_result(run)

                    cmd_result = await sandbox._run_ssh_command(
                        cmd, server_config, timeout=timeout
                    )
                    cmd_entry = {
                        "command": cmd,
                        "status": cmd_result.get("status"),
                        "output": (cmd_result.get("output") or "")[:4000],
                        "error": (cmd_result.get("error") or "")[:1000],
                        "exit_status": cmd_result.get("exit_status"),
                        "ts": time.time(),
                    }
                    stage_result["command_results"].append(cmd_entry)

                    # Stream the output line by line via pub/sub
                    _publish("command_output", {
                        "run_id": run_id,
                        "stage": stage_name,
                        "command": cmd,
                        "output": cmd_entry["output"],
                        "exit_status": cmd_entry["exit_status"],
                    })

                    if cmd_result.get("status") != "success":
                        stage_failed = True
                        if on_failure == "fail_fast":
                            break

                stage_result["finished_at"] = time.time()
                stage_result["status"] = RunStatus.FAILED if stage_failed else RunStatus.SUCCESS
                stage_results.append(stage_result)
                run["stage_results"] = stage_results
                _save_run(run_id, run)

                _publish("stage_finished", {
                    "run_id": run_id,
                    "stage": stage_name,
                    "stage_index": idx,
                    "status": stage_result["status"],
                })

                if stage_failed and on_failure == "fail_fast":
                    run["status"] = RunStatus.FAILED
                    break
            else:
                run["status"] = RunStatus.SUCCESS

        except Exception as exc:
            run["status"] = RunStatus.FAILED
            run["error"] = str(exc)
            stage_results.append({"name": "internal_error", "error": str(exc)})
            run["stage_results"] = stage_results

        run["finished_at"] = time.time()
        started = run.get("started_at") or run.get("created_at") or run["finished_at"]
        run["duration_seconds"] = run["finished_at"] - started
        _save_run(run_id, run)
        _persist_finished_run(run_id, run)

        _publish("run_finished", {
            "run_id": run_id,
            "pipeline_name": run.get("pipeline_name", ""),
            "status": run["status"],
            "duration_seconds": run.get("duration_seconds"),
        })

        # Record outcome in agent memory for analytics
        agent_memory.publish_event("pipeline_finished", {
            "run_id": run_id,
            "pipeline_name": run.get("pipeline_name", ""),
            "status": run["status"],
            "user_id": run.get("user_id", ""),
        })

        return _build_result(run)

    def get_run(self, run_id: str) -> Optional[Dict]:
        """Return current run state (Redis-first, Supabase fallback)."""
        return _load_run(run_id)

    def cancel_run(self, run_id: str) -> bool:
        """
        Signal a running pipeline to stop after the current command finishes.
        Sets status to CANCELLED in Redis so the execution loop picks it up.
        """
        run = _load_run(run_id)
        if not run:
            return False
        if run.get("status") in (RunStatus.SUCCESS, RunStatus.FAILED, RunStatus.CANCELLED):
            return False
        run["status"] = RunStatus.CANCELLED
        _save_run(run_id, run)
        _persist_finished_run(run_id, run)
        _publish("run_cancelled", {"run_id": run_id})
        return True

    def list_runs(self, pipeline_id: str, limit: int = 20) -> List[Dict]:
        """Return recent runs for a pipeline from Supabase."""
        if not supabase:
            return []
        try:
            resp = (
                supabase.table("pipeline_runs")
                .select("id,pipeline_name,status,triggered_by,created_at,duration_seconds")
                .eq("pipeline_id", pipeline_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            print(f"PipelineEngine.list_runs error: {e}")
            return []


def _build_result(run: Dict) -> Dict[str, Any]:
    return {
        "run_id": run["id"],
        "pipeline_name": run.get("pipeline_name"),
        "status": run["status"],
        "stage_results": run.get("stage_results", []),
        "duration_seconds": run.get("duration_seconds"),
        "error": run.get("error"),
    }


def _persist_finished_run(run_id: str, run: Dict) -> None:
    """Update the Supabase pipeline_runs row with final state."""
    if not supabase:
        return
    try:
        supabase.table("pipeline_runs").update({
            "status": run.get("status", RunStatus.FAILED),
            "duration_seconds": run.get("duration_seconds"),
            "stage_count": len(run.get("stage_results", [])),
        }).eq("id", run_id).execute()
    except Exception as e:
        print(f"PipelineEngine._persist_finished_run error: {e}")


pipeline_engine = PipelineEngine()
