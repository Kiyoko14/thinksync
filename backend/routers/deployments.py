from fastapi import APIRouter, Depends, HTTPException
from config import supabase
from models import Server
from routers.auth import get_current_user
from typing import List

router = APIRouter(prefix="/deployments", tags=["deployments"])

@router.get("/", response_model=List[dict])
async def get_deployments(current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("deployments").select("*").eq("user_id", current_user["id"]).execute()
    return response.data

@router.get("/{deployment_id}", response_model=dict)
async def get_deployment(deployment_id: str, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("deployments").select("*").eq("id", deployment_id).eq("user_id", current_user["id"]).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return response.data[0]
