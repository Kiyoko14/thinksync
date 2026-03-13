"""
Pipeline management router.

POST   /pipelines/                  — create a pipeline definition
GET    /pipelines/                  — list user pipelines
GET    /pipelines/{id}              — get pipeline definition
PUT    /pipelines/{id}              — update pipeline definition
DELETE /pipelines/{id}              — delete pipeline definition

POST   /pipelines/{id}/run          — trigger a run (async execution)
GET    /pipelines/runs/{run_id}     — get run state (Redis-first)
POST   /pipelines/runs/{run_id}/cancel — cancel a running pipeline
GET    /pipelines/{id}/runs         — list recent runs (Supabase)
"""

import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from config import supabase, redis_client
from routers.auth import get_current_user
from services.pipeline import pipeline_engine, RunStatus

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


# ── Request / Response models ─────────────────────────────────────────────────

class StageDefinition(BaseModel):
    name: str
    commands: List[str]
    on_failure: str = "fail_fast"   # "fail_fast" | "continue"
    timeout: int = 120              # seconds per command


class CreatePipelineRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    server_id: str
    stages: List[StageDefinition]
    environment_variables: Dict[str, str] = {}


class TriggerRunRequest(BaseModel):
    triggered_by: str = "manual"
    override_env: Dict[str, str] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_pipeline(pipeline_id: str, user_id: str) -> Dict:
    """Load a pipeline from Supabase; raise 404 if not found."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    resp = (
        supabase.table("pipelines")
        .select("*")
        .eq("id", pipeline_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return resp.data[0]


def _get_server(server_id: str, user_id: str) -> Dict:
    """Load a server config from Supabase; raise 404 if not found."""
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


# ── Pipeline CRUD ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[dict])
async def list_pipelines(current_user: dict = Depends(get_current_user)):
    """List all pipelines belonging to the current user."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    resp = (
        supabase.table("pipelines")
        .select("id,name,description,server_id,created_at,stage_count")
        .eq("user_id", current_user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


@router.post("/", response_model=dict)
async def create_pipeline(
    request: CreatePipelineRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new pipeline definition in Supabase."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Verify server ownership
    _get_server(request.server_id, current_user["id"])

    stages_json = [s.model_dump() for s in request.stages]
    try:
        resp = supabase.table("pipelines").insert({
            "user_id": current_user["id"],
            "server_id": request.server_id,
            "name": request.name,
            "description": request.description,
            "stages": stages_json,
            "stage_count": len(stages_json),
            "environment_variables": request.environment_variables,
        }).execute()
        return resp.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pipeline: {e}")


@router.get("/{pipeline_id}", response_model=dict)
async def get_pipeline(
    pipeline_id: str,
    current_user: dict = Depends(get_current_user),
):
    return _get_pipeline(pipeline_id, current_user["id"])


@router.put("/{pipeline_id}", response_model=dict)
async def update_pipeline(
    pipeline_id: str,
    request: CreatePipelineRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_pipeline(pipeline_id, current_user["id"])
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    stages_json = [s.model_dump() for s in request.stages]
    resp = (
        supabase.table("pipelines")
        .update({
            "name": request.name,
            "description": request.description,
            "server_id": request.server_id,
            "stages": stages_json,
            "stage_count": len(stages_json),
            "environment_variables": request.environment_variables,
        })
        .eq("id", pipeline_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return resp.data[0]


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    current_user: dict = Depends(get_current_user),
):
    _get_pipeline(pipeline_id, current_user["id"])
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    supabase.table("pipelines").delete().eq("id", pipeline_id).eq("user_id", current_user["id"]).execute()
    return {"message": "Pipeline deleted"}


# ── Run management ────────────────────────────────────────────────────────────

@router.post("/{pipeline_id}/run", response_model=dict)
async def trigger_run(
    pipeline_id: str,
    request: TriggerRunRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger a pipeline run.  The run executes in the background; the endpoint
    returns the *run_id* immediately so the caller can poll or subscribe.
    """
    pipeline = _get_pipeline(pipeline_id, current_user["id"])
    server = _get_server(pipeline["server_id"], current_user["id"])
    server_config = _server_to_config(server)

    stages = pipeline.get("stages", [])
    if not stages:
        raise HTTPException(status_code=400, detail="Pipeline has no stages")

    # Inject env vars from pipeline definition (merge with override_env)
    pipeline_env = pipeline.get("environment_variables", {}) or {}
    merged_env = {**pipeline_env, **request.override_env}

    # Prepend env-var export commands to the first stage if any vars defined.
    # Use shlex.quote on values to prevent command injection.
    if merged_env:
        import shlex
        export_cmds = [f"export {k}={shlex.quote(str(v))}" for k, v in merged_env.items()]
        stages = list(stages)
        first = dict(stages[0])
        first["commands"] = export_cmds + first.get("commands", [])
        stages[0] = first

    run_id = await pipeline_engine.create_run(
        pipeline_id=pipeline_id,
        pipeline_name=pipeline["name"],
        stages=stages,
        server_config=server_config,
        triggered_by=request.triggered_by,
        user_id=current_user["id"],
    )

    background_tasks.add_task(pipeline_engine.execute_run, run_id)

    return {
        "run_id": run_id,
        "pipeline_id": pipeline_id,
        "status": RunStatus.PENDING,
        "message": "Pipeline run started in background",
    }


@router.get("/runs/{run_id}", response_model=dict)
async def get_run(run_id: str, current_user: dict = Depends(get_current_user)):
    """Get the current state of a pipeline run (Redis-first)."""
    run = pipeline_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    # Strip sensitive server_config from response
    safe = {k: v for k, v in run.items() if k != "server_config"}
    return safe


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel a running pipeline."""
    ok = pipeline_engine.cancel_run(run_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Run cannot be cancelled (not running or not found)")
    return {"run_id": run_id, "status": RunStatus.CANCELLED}


@router.get("/{pipeline_id}/runs", response_model=List[dict])
async def list_runs(
    pipeline_id: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """List recent runs for a pipeline from Supabase."""
    _get_pipeline(pipeline_id, current_user["id"])
    return pipeline_engine.list_runs(pipeline_id, limit=limit)
