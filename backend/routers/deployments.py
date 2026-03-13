"""
Deployment router — create deployments and execute them via the PipelineEngine.

A deployment is created from the servers router (POST /servers/{id}/deploy)
and stored in the Supabase ``deployments`` table with status "pending".

This router adds:
  GET  /deployments/                    — list deployments
  GET  /deployments/{id}               — get deployment detail
  POST /deployments/{id}/execute        — actually execute the deployment script
  GET  /deployments/{id}/status         — fast status from Redis, fallback DB
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from config import supabase, redis_client
from routers.auth import get_current_user
from services.pipeline import pipeline_engine, RunStatus
import json
from typing import List

router = APIRouter(prefix="/deployments", tags=["deployments"])

_RUN_LINK_TTL = 86_400   # keep deployment→run_id link for 24 h


def _dep_run_key(deployment_id: str) -> str:
    return f"deploy:run:{deployment_id}"


@router.get("/", response_model=List[dict])
async def get_deployments(current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("deployments").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
    return response.data


@router.get("/{deployment_id}", response_model=dict)
async def get_deployment(deployment_id: str, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("deployments").select("*").eq("id", deployment_id).eq("user_id", current_user["id"]).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return response.data[0]


@router.post("/{deployment_id}/execute", response_model=dict)
async def execute_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Execute a pending deployment by running its script on the target server
    via the PipelineEngine.  Returns a run_id for polling.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Load deployment
    dep_resp = (
        supabase.table("deployments")
        .select("*")
        .eq("id", deployment_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not dep_resp.data:
        raise HTTPException(status_code=404, detail="Deployment not found")
    dep = dep_resp.data[0]

    if dep.get("status") == "running":
        raise HTTPException(status_code=409, detail="Deployment is already running")

    # Load server
    srv_resp = (
        supabase.table("servers")
        .select("*")
        .eq("id", dep["server_id"])
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not srv_resp.data:
        raise HTTPException(status_code=404, detail="Server not found")
    server = srv_resp.data[0]

    server_config = {
        "host": server["host"],
        "port": int(server.get("ssh_port") or 22),
        "username": server.get("ssh_user"),
        "ssh_auth_method": server.get("ssh_auth_method", "private_key"),
        "ssh_key": server.get("ssh_key"),
        "ssh_password": server.get("ssh_password"),
    }

    # Split multi-line script into individual commands
    script: str = dep.get("deployment_script", "echo 'No script'")
    commands = [line.strip() for line in script.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not commands:
        commands = ["echo 'Empty deployment script'"]

    stages = [{
        "name": f"deploy_{dep.get('language', 'app')}_{dep.get('deployment_type', 'bare-metal')}",
        "commands": commands,
        "on_failure": "fail_fast",
        "timeout": 300,
    }]

    run_id = await pipeline_engine.create_run(
        pipeline_id=deployment_id,
        pipeline_name=f"Deployment {deployment_id[:8]}",
        stages=stages,
        server_config=server_config,
        triggered_by="deployment",
        user_id=current_user["id"],
    )

    # Link deployment → run_id in Redis for fast status checks
    if redis_client:
        try:
            redis_client.setex(_dep_run_key(deployment_id), _RUN_LINK_TTL, run_id)
        except Exception:
            pass

    # Mark deployment as running in Supabase
    try:
        supabase.table("deployments").update({
            "status": "running",
            "run_id": run_id,
        }).eq("id", deployment_id).execute()
    except Exception as e:
        print(f"deployments.execute: supabase update warning: {e}")

    background_tasks.add_task(_run_and_update, run_id, deployment_id)

    return {
        "deployment_id": deployment_id,
        "run_id": run_id,
        "status": RunStatus.PENDING,
        "message": "Deployment started in background",
    }


async def _run_and_update(run_id: str, deployment_id: str) -> None:
    """Background task: execute the pipeline run and update deployment status."""
    result = await pipeline_engine.execute_run(run_id)
    if supabase:
        try:
            supabase.table("deployments").update({
                "status": result.get("status", "failed"),
            }).eq("id", deployment_id).execute()
        except Exception as e:
            print(f"deployments._run_and_update supabase update warning: {e}")


@router.get("/{deployment_id}/status", response_model=dict)
async def get_deployment_status(
    deployment_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Return deployment execution status.
    Fast path: Redis pipeline run state.
    Fallback:  Supabase deployments row.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    dep_resp = (
        supabase.table("deployments")
        .select("id,status,run_id")
        .eq("id", deployment_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not dep_resp.data:
        raise HTTPException(status_code=404, detail="Deployment not found")
    dep = dep_resp.data[0]

    run_id = dep.get("run_id")
    if not run_id and redis_client:
        try:
            run_id = redis_client.get(_dep_run_key(deployment_id))
        except Exception:
            pass

    run_state = None
    if run_id:
        raw = pipeline_engine.get_run(run_id)
        if raw:
            run_state = {
                "run_id": run_id,
                "status": raw.get("status"),
                "current_stage": raw.get("current_stage"),
                "duration_seconds": raw.get("duration_seconds"),
                "stage_results": [
                    {
                        "name": s.get("name"),
                        "status": s.get("status"),
                    }
                    for s in raw.get("stage_results", [])
                ],
            }

    return {
        "deployment_id": deployment_id,
        "status": dep.get("status", "unknown"),
        "run": run_state,
    }

