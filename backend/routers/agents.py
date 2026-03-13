from fastapi import APIRouter, Depends, HTTPException
from agents.orchestrator import process_message
from agents.memory import agent_memory, KNOWN_AGENTS
from config import supabase, async_db
from routers.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/agents", tags=["agents"])

class ProcessMessageRequest(BaseModel):
    message: str
    context: Optional[dict] = None


async def _get_chat_for_user(chat_id: str, user_id: str) -> dict:
    chat_response = await async_db(
        lambda: supabase.table("chats")
        .select("id,server_id,user_id")
        .eq("id", chat_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not chat_response.data:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat_response.data[0]


async def _get_server_config_for_user(server_id: str, user_id: str) -> dict:
    server_response = await async_db(
        lambda: supabase.table("servers")
        .select("host,ssh_port,ssh_user,ssh_auth_method,ssh_key,ssh_password")
        .eq("id", server_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")

    server = server_response.data[0]
    return {
        "host": server.get("host"),
        "port": int(server.get("ssh_port") or 22),
        "username": server.get("ssh_user"),
        "ssh_auth_method": server.get("ssh_auth_method", "private_key"),
        "ssh_key": server.get("ssh_key"),
        "ssh_password": server.get("ssh_password"),
    }


async def _get_task_for_user(task_id: str, user_id: str) -> dict:
    task_response = await async_db(
        lambda: supabase.table("tasks")
        .select("id,chat_id,state,step,attempts,created_at")
        .eq("id", task_id)
        .execute()
    )
    if not task_response.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_response.data[0]
    await _get_chat_for_user(task["chat_id"], user_id)
    return task

@router.post("/process/{chat_id}")
async def process_chat_message(
    chat_id: str,
    request: ProcessMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Process a chat message through the agent orchestration system"""
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Database not configured"
        )
    
    if not chat_id or not request.message:
        raise HTTPException(
            status_code=400, 
            detail="chat_id and message are required"
        )
    
    try:
        chat = await _get_chat_for_user(chat_id, current_user["id"])
        server_config = await _get_server_config_for_user(chat["server_id"], current_user["id"])
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        print(f"Error verifying chat: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to verify chat"
        )
    
    try:
        context = {
            **(request.context or {}),
            "chat_id": chat_id,
            "server_id": chat["server_id"],
            "user_id": current_user["id"],
            "server_config": server_config,
            "environment": (request.context or {}).get("environment", "production"),
        }
        result = await process_message(chat_id, request.message, context)
        if result.get("error"):
            raise HTTPException(
                status_code=500, 
                detail=result.get("error", "Failed to process message")
            )
        return {
            "status": "processing",
            "chat_id": chat_id,
            "task_id": result.get("task_id", "unknown"),
            "message": "Message queued for processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing message: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to process message"
        )

@router.get("/status/{task_id}")
async def get_task_status(task_id: str, current_user: dict = Depends(get_current_user)):
    """Get the status of a task"""
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Database not configured"
        )
    
    try:
            task = await _get_task_for_user(task_id, current_user["id"])
        return {
            "task_id": task_id,
            "state": task.get("state"),
            "step": task.get("step"),
            "attempts": task.get("attempts"),
            "created_at": task.get("created_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting task status: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve task status"
        )

@router.get("/stats")
async def get_agent_stats(current_user: dict = Depends(get_current_user)):
    """Return performance metrics for all agents from Redis."""
    return {agent: agent_memory.get_stats(agent) for agent in KNOWN_AGENTS}


@router.get("/memory/{task_id}")
async def get_task_working_memory(task_id: str, current_user: dict = Depends(get_current_user)):
    """Return the current working memory for a task (Redis hash)."""
    await _get_task_for_user(task_id, current_user["id"])
    data = agent_memory.get_working(task_id)
    if not data:
        raise HTTPException(status_code=404, detail="Working memory not found for task")
    return data
