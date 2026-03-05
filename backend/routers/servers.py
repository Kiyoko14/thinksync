from fastapi import APIRouter, Depends, HTTPException
from config import supabase, openai_client
from models import Server
from routers.auth import get_current_user
from services.execution import ExecutionSandbox
from pydantic import BaseModel
from typing import List
import json

router = APIRouter(prefix="/servers", tags=["servers"])

class CreateServerRequest(BaseModel):
    name: str
    host: str
    ssh_user: str
    ssh_port: int = 22
    ssh_key: str

class DeploymentRequest(BaseModel):
    code: str
    language: str
    deployment_type: str  # docker, kubernetes, bare-metal

class ExecuteCommandRequest(BaseModel):
    command: str
    timeout: int = 30

@router.get("/", response_model=List[Server])
async def get_servers(current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    response = supabase.table("servers").select("*").eq("user_id", current_user["id"]).execute()
    return response.data

@router.post("/", response_model=Server)
async def create_server(request: CreateServerRequest, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    server_data = {
        "user_id": current_user["id"],
        "name": request.name,
        "host": request.host,
        "ssh_user": request.ssh_user,
        "ssh_port": request.ssh_port,
        "ssh_key": request.ssh_key
    }
    response = supabase.table("servers").insert(server_data).execute()
    return response.data[0]

@router.put("/{server_id}", response_model=Server)
async def update_server(server_id: str, request: CreateServerRequest, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    server_data = {
        "name": request.name,
        "host": request.host,
        "ssh_user": request.ssh_user,
        "ssh_port": request.ssh_port,
        "ssh_key": request.ssh_key
    }
    response = supabase.table("servers").update(server_data).eq("id", server_id).eq("user_id", current_user["id"]).execute()
    return response.data[0]

@router.delete("/{server_id}")
async def delete_server(server_id: str, current_user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Delete related chats and workspaces
    supabase.table("chats").delete().eq("server_id", server_id).execute()
    supabase.table("servers").delete().eq("id", server_id).eq("user_id", current_user["id"]).execute()
    return {"message": "Server deleted"}

@router.post("/{server_id}/deploy")
async def deploy_code(server_id: str, request: DeploymentRequest, current_user: dict = Depends(get_current_user)):
    """Deploy code to a server using AI assistance"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Verify server belongs to user
    server_response = supabase.table("servers").select("*").eq("id", server_id).eq("user_id", current_user["id"]).execute()
    if not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = server_response.data[0]
    
    # Use AI to generate deployment script
    if openai_client:
        try:
            response = openai_client.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"""Generate a deployment script for {request.deployment_type} deployment.
                        
Code to deploy:
{request.code}

Language: {request.language}

Provide only the deployment script/commands."""
                    }
                ]
            )
            deployment_script = response.choices[0].message.content
        except:
            deployment_script = f"# Deployment script for {request.language}\necho 'Deploying...'"
    else:
        deployment_script = f"# Deployment script for {request.language}\necho 'Deploying...'"
    
    # Store deployment in database
    deployment_data = {
        "server_id": server_id,
        "user_id": current_user["id"],
        "code": request.code,
        "language": request.language,
        "deployment_type": request.deployment_type,
        "deployment_script": deployment_script,
        "status": "pending"
    }
    
    try:
        result = supabase.table("deployments").insert(deployment_data).execute()
        return {
            "deployment_id": result.data[0]["id"],
            "status": "pending",
            "script": deployment_script,
            "message": "Deployment queued successfully"
        }
    except Exception as e:
        return {
            "status": "pending",
            "script": deployment_script,
            "message": "Deployment script generated (database unavailable)"
        }

@router.post("/{server_id}/execute")
async def execute_command(server_id: str, request: ExecuteCommandRequest, current_user: dict = Depends(get_current_user)):
    """Execute a command on a server"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Verify server belongs to user
    server_response = supabase.table("servers").select("*").eq("id", server_id).eq("user_id", current_user["id"]).execute()
    if not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = server_response.data[0]
    sandbox = ExecutionSandbox()
    
    # Safety check
    dangerous_commands = ["rm -rf /", "mkfs", "shutdown", "reboot", "mount", "umount", "passwd", "useradd"]
    if any(cmd in request.command for cmd in dangerous_commands):
        raise HTTPException(status_code=400, detail="Command contains dangerous operations")
    
    try:
        result = await sandbox.execute_action(
            {
                "action": "run_command",
                "command": request.command,
                "chat_id": "direct_execution"
            },
            {
                "host": server["host"],
                "port": server["ssh_port"],
                "username": server["ssh_user"],
                "ssh_key": server["ssh_key"]
            }
        )
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "output": ""
        }

@router.get("/{server_id}/status")
async def get_server_status(server_id: str, current_user: dict = Depends(get_current_user)):
    """Get server status"""
    if not supabase:
        return {"status": "unknown", "message": "Database not configured"}
    
    server_response = supabase.table("servers").select("*").eq("id", server_id).eq("user_id", current_user["id"]).execute()
    if not server_response.data:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = server_response.data[0]
    sandbox = ExecutionSandbox()
    
    try:
        result = await sandbox.execute_action(
            {
                "action": "run_command",
                "command": "echo 'online'",
                "chat_id": "status_check"
            },
            {
                "host": server["host"],
                "port": server["ssh_port"],
                "username": server["ssh_user"],
                "ssh_key": server["ssh_key"]
            }
        )
        return {"status": "online", "server": server}
    except:
        return {"status": "offline", "server": server}