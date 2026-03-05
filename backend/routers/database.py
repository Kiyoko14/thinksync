from fastapi import APIRouter, Depends, HTTPException
from config import supabase
from models import Database
from routers.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional
import requests
import os

router = APIRouter(prefix="/database", tags=["database"])

class CreateDatabaseRequest(BaseModel):
    server_id: Optional[str] = None

@router.get("/", response_model=List[Database])
async def get_databases(current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("databases").select("*").eq("user_id", current_user["id"]).execute()
    return response.data

@router.post("/", response_model=Database)
async def create_database(request: CreateDatabaseRequest, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Create Supabase project
    access_token = os.getenv("SUPABASE_ACCESS_TOKEN")
    org_id = os.getenv("SUPABASE_ORG_ID")
    
    if not access_token or not org_id:
        raise HTTPException(status_code=500, detail="Supabase configuration missing")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    project_data = {
        "name": f"db-{current_user['id']}-{request.server_id or 'global'}",
        "organization_id": org_id,
        "db_pass": "secure_password",  # Generate secure password
        "region": "us-east-1"
    }
    
    response = requests.post("https://api.supabase.com/v1/projects", json=project_data, headers=headers)
    if response.status_code != 201:
        raise HTTPException(status_code=400, detail="Failed to create database")
    
    project = response.json()
    db_url = f"postgres://postgres:{project['db_pass']}@{project['id']}.supabase.co:5432/postgres"
    
    database_data = {
        "user_id": current_user["id"],
        "server_id": request.server_id,
        "project_id": project["id"],
        "db_url": db_url
    }
    
    db_response = supabase.table("databases").insert(database_data).execute()
    return db_response.data[0]