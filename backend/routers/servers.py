from fastapi import APIRouter, Depends, HTTPException
from config import supabase, openai_client
from models import Server
from routers.auth import get_current_user
from services.execution import ExecutionSandbox
from services.state_tracker import get_server_state
from pydantic import BaseModel
from typing import Dict, List, Literal, Any
from uuid import uuid4
from datetime import datetime, timezone

router = APIRouter(prefix="/servers", tags=["servers"])

LOCAL_SERVERS: Dict[str, dict] = {}

class CreateServerRequest(BaseModel):
    name: str
    host: str
    ssh_user: str
    ssh_port: int = 22
    ssh_auth_method: Literal["private_key", "password"] = "private_key"
    ssh_key: str | None = None
    ssh_password: str | None = None

class DeploymentRequest(BaseModel):
    code: str
    language: str
    deployment_type: str  # docker, kubernetes, bare-metal

class ExecuteCommandRequest(BaseModel):
    command: str
    timeout: int = 30


def _build_server_payload(request: CreateServerRequest, current_user: dict) -> Dict[str, Any]:
    ssh_auth_method = request.ssh_auth_method
    if ssh_auth_method == "private_key" and not request.ssh_key:
        raise HTTPException(status_code=400, detail="ssh_key is required for private_key auth")
    if ssh_auth_method == "password" and not request.ssh_password:
        raise HTTPException(status_code=400, detail="ssh_password is required for password auth")

    return {
        "id": str(uuid4()),
        "user_id": current_user["id"],
        "name": request.name,
        "host": request.host,
        "ssh_user": request.ssh_user,
        "ssh_port": request.ssh_port,
        "ssh_auth_method": ssh_auth_method,
        "ssh_key": request.ssh_key if ssh_auth_method == "private_key" else None,
        "ssh_password": request.ssh_password if ssh_auth_method == "password" else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _legacy_server_payload(server_data: Dict[str, Any]) -> Dict[str, Any]:
    # Compatibility for databases which only have ssh_key column.
    legacy_ssh_key = server_data.get("ssh_key")
    if not legacy_ssh_key and server_data.get("ssh_auth_method") == "password":
        legacy_ssh_key = server_data.get("ssh_password")

    return {
        "name": server_data["name"],
        "host": server_data["host"],
        "ssh_user": server_data["ssh_user"],
        "ssh_port": server_data["ssh_port"],
        "ssh_key": legacy_ssh_key,
    }

@router.get("/", response_model=List[Server])
async def get_servers(current_user: dict = Depends(get_current_user)):
    if supabase:
        response = supabase.table("servers").select("*").eq("user_id", current_user["id"]).execute()
        return response.data

    return [
        server
        for server in LOCAL_SERVERS.values()
        if server["user_id"] == current_user["id"]
    ]


@router.get("/{server_id}", response_model=Server)
async def get_server(server_id: str, current_user: dict = Depends(get_current_user)):
    if supabase:
        response = (
            supabase.table("servers")
            .select("*")
            .eq("id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Server not found")
        return response.data[0]

    server = LOCAL_SERVERS.get(server_id)
    if not server or server["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@router.post("/", response_model=Server)
async def create_server(request: CreateServerRequest, current_user: dict = Depends(get_current_user)):
    server_data = _build_server_payload(request, current_user)

    if supabase:
        payload = {k: v for k, v in server_data.items() if k != "id"}
        try:
            response = supabase.table("servers").insert(payload).execute()
            return response.data[0]
        except Exception:
            # Retry for legacy schema that doesn't have ssh_auth_method/ssh_password.
            response = supabase.table("servers").insert(_legacy_server_payload(server_data)).execute()
            return response.data[0]

    LOCAL_SERVERS[server_data["id"]] = server_data
    return server_data

@router.put("/{server_id}", response_model=Server)
async def update_server(server_id: str, request: CreateServerRequest, current_user: dict = Depends(get_current_user)):
    updated_payload = _build_server_payload(request, current_user)
    server_data = {
        "name": updated_payload["name"],
        "host": updated_payload["host"],
        "ssh_user": updated_payload["ssh_user"],
        "ssh_port": updated_payload["ssh_port"],
        "ssh_auth_method": updated_payload["ssh_auth_method"],
        "ssh_key": updated_payload["ssh_key"],
        "ssh_password": updated_payload["ssh_password"],
    }

    if supabase:
        try:
            response = (
                supabase.table("servers")
                .update(server_data)
                .eq("id", server_id)
                .eq("user_id", current_user["id"])
                .execute()
            )
        except Exception:
            response = (
                supabase.table("servers")
                .update(_legacy_server_payload(server_data))
                .eq("id", server_id)
                .eq("user_id", current_user["id"])
                .execute()
            )
        if not response.data:
            raise HTTPException(status_code=404, detail="Server not found")
        return response.data[0]

    local_server = LOCAL_SERVERS.get(server_id)
    if not local_server or local_server["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Server not found")
    local_server.update(server_data)
    return local_server

@router.delete("/{server_id}")
async def delete_server(server_id: str, current_user: dict = Depends(get_current_user)):
    if supabase:
        supabase.table("chats").delete().eq("server_id", server_id).execute()
        supabase.table("servers").delete().eq("id", server_id).eq("user_id", current_user["id"]).execute()
    else:
        local_server = LOCAL_SERVERS.get(server_id)
        if not local_server or local_server["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Server not found")
        del LOCAL_SERVERS[server_id]
    return {"message": "Server deleted"}

@router.post("/{server_id}/deploy")
async def deploy_code(server_id: str, request: DeploymentRequest, current_user: dict = Depends(get_current_user)):
    """Deploy code to a server using AI assistance"""
    if supabase:
        server_response = (
            supabase.table("servers")
            .select("*")
            .eq("id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not server_response.data:
            raise HTTPException(status_code=404, detail="Server not found")
        server = server_response.data[0]
    else:
        server = LOCAL_SERVERS.get(server_id)
        if not server or server["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Server not found")
    
    # Use AI to generate deployment script
    if openai_client:
        try:
            response = openai_client.chat.completions.create(
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
            deployment_script = (
                response.choices[0].message.content
                if response
                else f"# Deployment script for {request.language}\necho 'Deploying...'"
            )
        except Exception:
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
    
    if supabase:
        try:
            result = supabase.table("deployments").insert(deployment_data).execute()
            return {
                "deployment_id": result.data[0]["id"],
                "status": "pending",
                "script": deployment_script,
                "message": "Deployment queued successfully",
            }
        except Exception:
            pass

    return {
        "status": "pending",
        "script": deployment_script,
        "message": "Deployment script generated",
    }

@router.post("/{server_id}/execute")
async def execute_command(server_id: str, request: ExecuteCommandRequest, current_user: dict = Depends(get_current_user)):
    """Execute a command on a server"""
    if supabase:
        server_response = (
            supabase.table("servers")
            .select("*")
            .eq("id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not server_response.data:
            raise HTTPException(status_code=404, detail="Server not found")
        server = server_response.data[0]
    else:
        server = LOCAL_SERVERS.get(server_id)
        if not server or server["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Server not found")

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
                "chat_id": "direct_execution",
                "timeout": request.timeout,
            },
            {
                "host": server["host"],
                "port": server["ssh_port"],
                "username": server["ssh_user"],
                "ssh_auth_method": server.get("ssh_auth_method"),
                "ssh_key": server.get("ssh_key"),
                "ssh_password": server.get("ssh_password"),
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

    if supabase:
        server_response = (
            supabase.table("servers")
            .select("*")
            .eq("id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not server_response.data:
            raise HTTPException(status_code=404, detail="Server not found")
        server = server_response.data[0]
    else:
        server = LOCAL_SERVERS.get(server_id)
        if not server or server["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Server not found")

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
                "ssh_auth_method": server.get("ssh_auth_method"),
                "ssh_key": server.get("ssh_key"),
                "ssh_password": server.get("ssh_password"),
            }
        )
        return {"status": "online", "server": server}
    except:
        return {"status": "offline", "server": server}


@router.get("/{server_id}/state")
async def get_filesystem_state(server_id: str, current_user: dict = Depends(get_current_user)):

    if supabase:
        server_response = (
            supabase.table("servers")
            .select("id")
            .eq("id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )

        if not server_response.data:
            raise HTTPException(status_code=404, detail="Server not found")

    else:
        server = LOCAL_SERVERS.get(server_id)
        if not server or server["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Server not found")

    return get_server_state(server_id)
