from fastapi import APIRouter, Depends, HTTPException, Request
from config import supabase, openai_client, openai_model, call_openai, async_db
from models import Server
from routers.auth import get_current_user
from services.execution import ExecutionSandbox
from services.state_tracker import clear_server_state, get_server_state
from security.validators import sanitize_command, validate_ssh_config
from security.crypto import mask_ssh_key, mask_sensitive_value
from security.audit import log_security_event, SecurityEventType
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Literal, Any, Optional
from uuid import uuid4
from datetime import datetime, timezone
from utils.cache import LRUCache

router = APIRouter(prefix="/servers", tags=["servers"])

# Use LRU cache instead of unbounded dictionary to prevent memory leak
# Maximum 10,000 servers in local fallback mode
LOCAL_SERVERS = LRUCache[str, dict](max_size=10_000)

class CreateServerRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    host: str = Field(min_length=1, max_length=255)
    ssh_user: str = Field(min_length=1, max_length=64)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_auth_method: Literal["private_key", "password"] = "private_key"
    ssh_key: str | None = Field(default=None, min_length=100)
    ssh_password: str | None = Field(default=None, min_length=6)
    
    @validator("host")
    def validate_host_format(cls, v):
        """Validate host format to prevent injection"""
        import re
        if not re.match(r"^[a-zA-Z0-9.-]+$", v):
            raise ValueError("Host can only contain alphanumeric characters, dots, and hyphens")
        return v
    
    @validator("ssh_user")
    def validate_username_format(cls, v):
        """Validate username format"""
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain alphanumeric characters, underscores, and hyphens")
        return v

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


def _server_to_config(server: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "host": server["host"],
        "port": int(server.get("ssh_port") or 22),
        "username": server["ssh_user"],
        "ssh_auth_method": server.get("ssh_auth_method"),
        "ssh_key": server.get("ssh_key"),
        "ssh_password": server.get("ssh_password"),
    }


async def _safe_delete_by_server(table: str, server_id: str, user_id: str) -> None:
    if not supabase:
        return
    try:
        await async_db(
            lambda: supabase.table(table)
            .delete()
            .eq("server_id", server_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as e:
        print(f"servers.delete: cleanup warning for {table}: {e}")


async def _safe_delete_by_chat_ids(table: str, chat_ids: List[str]) -> None:
    if not supabase or not chat_ids:
        return
    for chat_id in chat_ids:
        try:
            await async_db(
                lambda chat_id=chat_id: supabase.table(table).delete().eq("chat_id", chat_id).execute()
            )
        except Exception as e:
            print(f"servers.delete: cleanup warning for {table} (chat_id={chat_id}): {e}")

@router.get("/", response_model=List[Server])
async def get_servers(current_user: dict = Depends(get_current_user)):
    if supabase:
        response = await async_db(
            lambda: supabase.table("servers").select("*").eq("user_id", current_user["id"]).execute()
        )
        return response.data

    # Filter servers from LRU cache
    return [
        server
        for server in LOCAL_SERVERS.values()
        if server["user_id"] == current_user["id"]
    ]


@router.get("/{server_id}", response_model=Server)
async def get_server(server_id: str, current_user: dict = Depends(get_current_user)):
    if supabase:
        response = await async_db(
            lambda: supabase.table("servers")
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
async def create_server(
    request: CreateServerRequest,
    current_user: dict = Depends(get_current_user),
    http_request: Request = None,
):
    """Create a new server with security validation"""
    # Validate SSH configuration
    server_config = _server_to_config({
        "host": request.host,
        "ssh_port": request.ssh_port,
        "ssh_user": request.ssh_user,
        "ssh_auth_method": request.ssh_auth_method,
        "ssh_key": request.ssh_key,
        "ssh_password": request.ssh_password,
    })
    
    is_valid, error_msg = validate_ssh_config(server_config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid SSH configuration: {error_msg}")
    
    server_data = _build_server_payload(request, current_user)
    
    # Get client IP for audit logging
    ip_address = None
    if http_request:
        ip_address = (
            http_request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (http_request.client.host if http_request.client else None)
        )

    if supabase:
        payload = {k: v for k, v in server_data.items() if k != "id"}
        try:
            response = await async_db(
                lambda: supabase.table("servers").insert(payload).execute()
            )
            created_server = response.data[0]
            
            # Log successful creation
            log_security_event(
                SecurityEventType.CONFIG_SERVER_CREATED,
                user_id=current_user["id"],
                resource_type="server",
                resource_id=created_server["id"],
                details={"host": request.host, "name": request.name},
                ip_address=ip_address,
                severity="info",
            )
            
            return created_server
        except Exception:
            # Retry for legacy schema that doesn't have ssh_auth_method/ssh_password.
            response = await async_db(
                lambda: supabase.table("servers").insert(_legacy_server_payload(server_data)).execute()
            )
            created_server = response.data[0]
            
            log_security_event(
                SecurityEventType.CONFIG_SERVER_CREATED,
                user_id=current_user["id"],
                resource_type="server",
                resource_id=created_server["id"],
                details={"host": request.host, "name": request.name},
                ip_address=ip_address,
                severity="info",
            )
            
            return created_server

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
            response = await async_db(
                lambda: supabase.table("servers")
                .update(server_data)
                .eq("id", server_id)
                .eq("user_id", current_user["id"])
                .execute()
            )
        except Exception:
            response = await async_db(
                lambda: supabase.table("servers")
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
    # Update the server data
    local_server.update(server_data)
    LOCAL_SERVERS.set(server_id, local_server)
    return local_server

@router.delete("/{server_id}")
async def delete_server(server_id: str, current_user: dict = Depends(get_current_user)):
    if supabase:
        server_response = await async_db(
            lambda: supabase.table("servers")
            .select("id")
            .eq("id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not server_response.data:
            raise HTTPException(status_code=404, detail="Server not found")

        chats_response = await async_db(
            lambda: supabase.table("chats")
            .select("id")
            .eq("server_id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        chat_ids = [str(row.get("id")) for row in (chats_response.data or []) if row.get("id")]

        # Remove rows that are chat-bound first.
        await _safe_delete_by_chat_ids("messages", chat_ids)
        await _safe_delete_by_chat_ids("tasks", chat_ids)
        await _safe_delete_by_chat_ids("actions", chat_ids)
        await _safe_delete_by_chat_ids("workspaces", chat_ids)
        await _safe_delete_by_chat_ids("agent_logs", chat_ids)

        # Remove rows bound to this server.
        await _safe_delete_by_server("deployments", server_id, current_user["id"])
        await _safe_delete_by_server("pipelines", server_id, current_user["id"])
        await _safe_delete_by_server("databases", server_id, current_user["id"])
        await _safe_delete_by_server("chats", server_id, current_user["id"])

        # Tables that may not have user_id in all schemas are cleaned best-effort.
        try:
            await async_db(lambda: supabase.table("server_secrets").delete().eq("server_id", server_id).execute())
        except Exception as e:
            print(f"servers.delete: cleanup warning for server_secrets: {e}")
        try:
            await async_db(lambda: supabase.table("server_logs").delete().eq("server_id", server_id).execute())
        except Exception as e:
            print(f"servers.delete: cleanup warning for server_logs: {e}")

        await async_db(
            lambda: supabase.table("servers").delete().eq("id", server_id).eq("user_id", current_user["id"]).execute()
        )
        clear_server_state(server_id, chat_ids)
    else:
        local_server = LOCAL_SERVERS.get(server_id)
        if not local_server or local_server["user_id"] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Server not found")
        LOCAL_SERVERS.delete(server_id)
        clear_server_state(server_id)
    return {"message": "Server deleted"}

@router.post("/{server_id}/deploy")
async def deploy_code(server_id: str, request: DeploymentRequest, current_user: dict = Depends(get_current_user)):
    """Deploy code to a server using AI assistance"""
    if supabase:
        server_response = await async_db(
            lambda: supabase.table("servers")
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
            response = await call_openai(
                model=openai_model,
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
            result = await async_db(
                lambda: supabase.table("deployments").insert(deployment_data).execute()
            )
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
async def execute_command(
    server_id: str,
    request: ExecuteCommandRequest,
    current_user: dict = Depends(get_current_user),
    http_request: Request = None,
):
    """Execute a command on a server with comprehensive security checks"""
    if supabase:
        server_response = await async_db(
            lambda: supabase.table("servers")
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

    # Validate command before execution
    is_safe, sanitized_cmd, error_msg = sanitize_command(request.command, allow_operators=False)
    if not is_safe:
        raise HTTPException(
            status_code=400,
            detail=f"Command validation failed: {error_msg}"
        )
    
    # Get client IP for audit logging
    ip_address = None
    if http_request:
        ip_address = (
            http_request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (http_request.client.host if http_request.client else None)
        )
    
    sandbox = ExecutionSandbox()
    
    try:
        result = await sandbox.execute_action(
            {
                "action": "run_command",
                "command": sanitized_cmd,
                "chat_id": f"direct_{server_id}_{current_user['id']}",
                "timeout": request.timeout,
            },
            _server_to_config(server),
            user_id=current_user["id"],
            ip_address=ip_address,
        )
        return result
    except Exception as e:
        log_security_event(
            SecurityEventType.COMMAND_FAILED,
            user_id=current_user["id"],
            resource_type="server",
            resource_id=server_id,
            details={"error": str(e)},
            ip_address=ip_address,
            severity="error",
        )
        return {
            "status": "error",
            "message": str(e),
            "output": ""
        }

@router.get("/{server_id}/status")
async def get_server_status(server_id: str, current_user: dict = Depends(get_current_user)):
    """Get server status"""

    if supabase:
        server_response = await async_db(
            lambda: supabase.table("servers")
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
    server_config = _server_to_config(server)

    try:
        result = await sandbox._run_ssh_command("echo online", server_config, timeout=10)
    except Exception as e:
        return {"status": "offline", "server": server, "error": str(e)}

    if result.get("status") == "success" and result.get("exit_status") == 0:
        return {"status": "online", "server": server}

    return {
        "status": "offline",
        "server": server,
        "error": result.get("error") or result.get("output") or "SSH check failed",
    }


@router.get("/{server_id}/state")
async def get_filesystem_state(server_id: str, current_user: dict = Depends(get_current_user)):

    if supabase:
        server_response = await async_db(
            lambda: supabase.table("servers")
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
