from fastapi import APIRouter, HTTPException
from agents.orchestrator import process_message
from config import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/agents", tags=["agents"])

class ProcessMessageRequest(BaseModel):
    message: str
    context: Optional[dict] = None

@router.post("/process/{chat_id}")
async def process_chat_message(chat_id: str, request: ProcessMessageRequest):
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
    
    # Verify chat exists and belongs to user
    try:
        chat_response = supabase.table("chats").select("id").eq("id", chat_id).execute()
        if not chat_response.data:
            raise HTTPException(
                status_code=404, 
                detail="Chat not found"
            )
    except Exception as e:
        print(f"Error verifying chat: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to verify chat"
        )
    
    try:
        result = await process_message(chat_id, request.message)
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
async def get_task_status(task_id: str):
    """Get the status of a task"""
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Database not configured"
        )
    
    try:
        task_response = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not task_response.data:
            raise HTTPException(
                status_code=404, 
                detail="Task not found"
            )
        
        task = task_response.data[0]
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