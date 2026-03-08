from fastapi import APIRouter, Depends, HTTPException
from config import supabase
from models import Task
from routers.auth import get_current_user
from typing import List

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[Task])
async def get_tasks(current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("tasks").select("*").eq("user_id", current_user["id"]).execute()
    return response.data

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("tasks").select("*").eq("id", task_id).eq("user_id", current_user["id"]).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return response.data[0]
