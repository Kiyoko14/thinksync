from config import redis_client, supabase
import asyncio
from typing import Dict, Any
import asyncssh

class ExecutionSandbox:
    def __init__(self):
        self.banned_commands = [
            "rm -rf /", 
            "mkfs", 
            "shutdown", 
            "reboot", 
            "mount", 
            "umount", 
            "passwd", 
            "useradd", 
            "usermod", 
            "chmod 777 /"
        ]
    
    async def execute_action(self, action: Dict[str, Any], server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action with safety checks"""
        try:
            # Rate limiting with Redis
            if redis_client:
                rate_key = f"rate:{action.get('chat_id')}"
                if redis_client.get(rate_key):
                    return {"status": "rate_limited", "message": "Too many requests"}
                redis_client.set(rate_key, "1", ex=60)
            
            # Validate command
            if action.get("action") == "run_command":
                command = action.get("command", "")
                if any(banned in command for banned in self.banned_commands):
                    return {
                        "status": "blocked", 
                        "reason": "banned command detected",
                        "command": "***REDACTED***"
                    }
                
                # Validate command is not empty
                if not command.strip():
                    return {"status": "error", "reason": "empty command"}

                timeout = int(action.get("timeout", 30))
                result = await self._run_ssh_command(command, server_config, timeout)
                result["timestamp"] = str(asyncio.get_event_loop().time())
                return result
            
            # Non-command actions are acknowledged as accepted.
            return {
                "status": "success", 
                "output": "Action accepted", 
                "error": "",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _run_ssh_command(self, command: str, server_config: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        host = server_config.get("host")
        username = server_config.get("username") or server_config.get("ssh_user")
        port = int(server_config.get("port") or server_config.get("ssh_port") or 22)
        auth_method = server_config.get("ssh_auth_method")
        ssh_key = server_config.get("ssh_key")
        ssh_password = server_config.get("ssh_password") or server_config.get("password")

        if not host or not username:
            return {
                "status": "error",
                "error": "Missing SSH connection fields: host or username",
                "output": "",
            }

        if auth_method not in {"private_key", "password"}:
            # Backward compatibility: old records only had ssh_key.
            auth_method = "private_key" if ssh_key else "password"

        connect_kwargs: Dict[str, Any] = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None,
        }

        if auth_method == "password":
            if not ssh_password:
                return {
                    "status": "error",
                    "error": "Password auth selected but ssh_password is empty",
                    "output": "",
                }
            connect_kwargs["password"] = ssh_password
        else:
            if not ssh_key:
                return {
                    "status": "error",
                    "error": "Private key auth selected but ssh_key is empty",
                    "output": "",
                }
            private_key = asyncssh.import_private_key(ssh_key)
            connect_kwargs["client_keys"] = [private_key]

        try:
            async with asyncssh.connect(**connect_kwargs) as conn:
                command_result = await conn.run(command, check=False, timeout=timeout)
                return {
                    "status": "success" if command_result.exit_status == 0 else "error",
                    "output": command_result.stdout,
                    "error": command_result.stderr,
                    "exit_status": command_result.exit_status,
                }
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error": f"Command timed out after {timeout} seconds",
                "output": "",
            }
        except (asyncssh.Error, OSError) as exc:
            return {
                "status": "error",
                "error": str(exc),
                "output": "",
            }

execution_sandbox = ExecutionSandbox()

async def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute action with database lookup and error handling"""
    if not action:
        return {"status": "error", "error": "No action provided"}
    
    if not supabase:
        return {
            "status": "error", 
            "error": "Database not configured"
        }
    
    # Get server config from DB
    server_id = action.get("server_id")
    if not server_id:
        return {"status": "error", "error": "No server_id in action"}
    
    try:
        server_response = supabase.table("servers").select("*").eq("id", server_id).execute()
        if not server_response.data:
            return {"status": "error", "error": "Server not found"}
        
        server = server_response.data[0]
        result = await execution_sandbox.execute_action(action, server)
        
        # Log execution result if Redis available
        if redis_client:
            try:
                log_key = f"execution_log:{action.get('chat_id')}:{action.get('id', 'unknown')}"
                redis_client.set(log_key, str(result), ex=3600)  # Keep for 1 hour
            except Exception as e:
                print(f"Warning: Failed to log execution: {e}")
        
        return result
    except Exception as e:
        print(f"Error executing action: {e}")
        return {"status": "error", "error": str(e)}