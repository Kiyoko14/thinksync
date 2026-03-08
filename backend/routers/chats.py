from fastapi import APIRouter, Depends, HTTPException
from config import supabase, redis_client
from models import Chat, Message, Task
from routers.auth import get_current_user
from pydantic import BaseModel
from typing import List
import os
import json

router = APIRouter(prefix="/chats", tags=["chats"])

class CreateChatRequest(BaseModel):
    server_id: str
    name: str

@router.get("/", response_model=List[Chat])
async def get_chats(current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("chats").select("*").eq("user_id", current_user["id"]).execute()
    return response.data

@router.post("/", response_model=Chat)
async def create_chat(request: CreateChatRequest, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    workspace_path = f"/home/aiuser/workspaces/{request.name.replace(' ', '_')}"
    chat_data = {
        "server_id": request.server_id,
        "user_id": current_user["id"],
        "name": request.name,
        "workspace_path": workspace_path
    }
    response = supabase.table("chats").insert(chat_data).execute()
    # Create workspace directory
    os.makedirs(workspace_path, exist_ok=True)
    return response.data[0]

@router.get("/{chat_id}/messages", response_model=List[Message])
async def get_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at").execute()
    return response.data

@router.post("/{chat_id}/messages")
async def send_message(chat_id: str, content: str, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    message_data = {
        "chat_id": chat_id,
        "role": "user",
        "content": content
    }
    response = supabase.table("messages").insert(message_data).execute()
    # Trigger AI processing with error handling
    try:
        from agents.orchestrator import process_message
        await process_message(chat_id, content)
    except ImportError:
        print("Warning: agents.orchestrator module not found")
    except Exception as e:
        print(f"Error processing message: {e}")
    return response.data[0]