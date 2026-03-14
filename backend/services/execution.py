from config import redis_client, supabase, SSH_CONCURRENCY
import asyncio
from typing import Dict, Any, Optional
import asyncssh

from security.validators import sanitize_command, validate_ssh_config, sanitize_log_output
from security.audit import log_security_event, SecurityEventType, check_rate_limit

# ── Concurrency limits ────────────────────────────────────────────────────────
# Each SSH connection consumes file descriptors and memory on both sides.
# Cap concurrent SSH sessions to prevent resource exhaustion under load.
# Controlled via the SSH_CONCURRENCY environment variable (default: 50).
_SSH_SEMAPHORE = asyncio.Semaphore(SSH_CONCURRENCY)

class ExecutionSandbox:
    """
    Secure execution sandbox for running commands on remote servers via SSH.
    
    Features:
    - Command validation and sanitization
    - Rate limiting per user/chat
    - Security audit logging
    - SSH connection pooling with semaphore
    - Comprehensive error handling
    """
    
    def __init__(self):
        # Deprecated: moved to security.validators module
        # Kept for backwards compatibility
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
    
    async def execute_action(
        self,
        action: Dict[str, Any],
        server_config: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute action with comprehensive safety checks.
        
        Args:
            action: Action dictionary with command and metadata
            server_config: SSH server configuration
            user_id: User ID for audit logging
            ip_address: Source IP for audit logging
            
        Returns:
            Dictionary with execution result
        """
        try:
            chat_id = action.get("chat_id", "unknown")
            
            # Rate limiting with Redis
            if redis_client and user_id:
                if not check_rate_limit(user_id, "command_execution", limit=30, window=60):
                    log_security_event(
                        SecurityEventType.COMMAND_BLOCKED,
                        user_id=user_id,
                        details={"reason": "rate_limit", "chat_id": chat_id},
                        ip_address=ip_address,
                        severity="warning",
                    )
                    return {
                        "status": "rate_limited",
                        "message": "Too many commands. Please wait before trying again."
                    }
            
            # Validate action type
            if action.get("action") == "run_command":
                command = action.get("command", "")
                
                # Validate command is not empty
                if not command.strip():
                    return {"status": "error", "reason": "empty command"}
                
                # Comprehensive command validation
                is_safe, sanitized_cmd, error_msg = sanitize_command(command, allow_operators=False)
                
                if not is_safe:
                    log_security_event(
                        SecurityEventType.COMMAND_BLOCKED,
                        user_id=user_id,
                        details={
                            "command": "***REDACTED***",
                            "reason": error_msg,
                            "chat_id": chat_id,
                        },
                        ip_address=ip_address,
                        severity="warning",
                    )
                    return {
                        "status": "blocked",
                        "reason": error_msg or "Command contains dangerous operations",
                        "command": "***REDACTED***"
                    }
                
                # Validate SSH configuration
                config_valid, config_error = validate_ssh_config(server_config)
                if not config_valid:
                    return {
                        "status": "error",
                        "reason": f"Invalid SSH configuration: {config_error}"
                    }
                
                # Execute the command
                timeout = int(action.get("timeout", 30))
                result = await self._run_ssh_command(
                    sanitized_cmd,
                    server_config,
                    timeout,
                    user_id=user_id,
                    ip_address=ip_address,
                )
                
                # Add timestamp
                result["timestamp"] = str(asyncio.get_event_loop().time())
                
                # Sanitize output for logging
                if result.get("output"):
                    result["output"] = sanitize_log_output(result["output"])
                if result.get("error"):
                    result["error"] = sanitize_log_output(result["error"])
                
                # Log successful execution
                if result.get("status") == "success":
                    log_security_event(
                        SecurityEventType.COMMAND_EXECUTED,
                        user_id=user_id,
                        details={
                            "chat_id": chat_id,
                            "exit_status": result.get("exit_status"),
                        },
                        ip_address=ip_address,
                        severity="info",
                    )
                else:
                    log_security_event(
                        SecurityEventType.COMMAND_FAILED,
                        user_id=user_id,
                        details={
                            "chat_id": chat_id,
                            "error": result.get("error", "Unknown error"),
                        },
                        ip_address=ip_address,
                        severity="warning",
                    )
                
                return result
            
            # Non-command actions are acknowledged as accepted.
            return {
                "status": "success",
                "output": "Action accepted",
                "error": "",
                "timestamp": str(asyncio.get_event_loop().time())
            }
            
        except Exception as e:
            log_security_event(
                SecurityEventType.COMMAND_FAILED,
                user_id=user_id,
                details={"error": str(e), "chat_id": action.get("chat_id")},
                ip_address=ip_address,
                severity="error",
            )
            return {"status": "error", "error": str(e)}

    async def _run_ssh_command(
        self,
        command: str,
        server_config: Dict[str, Any],
        timeout: int,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a command via SSH with comprehensive error handling.
        
        Args:
            command: The command to execute
            server_config: SSH configuration
            timeout: Command timeout in seconds
            user_id: User ID for logging
            ip_address: Source IP for logging
            
        Returns:
            Dictionary with execution result
        """
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
            "connect_timeout": 30,  # Add connection timeout
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
            try:
                private_key = asyncssh.import_private_key(ssh_key)
                connect_kwargs["client_keys"] = [private_key]
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Invalid SSH private key: {str(e)}",
                    "output": "",
                }

        # Acquire semaphore before opening the SSH connection so we never exceed
        # _SSH_SEMAPHORE concurrent SSH sessions under heavy load.
        async with _SSH_SEMAPHORE:
            try:
                async with asyncssh.connect(**connect_kwargs) as conn:
                    command_result = await conn.run(command, check=False, timeout=timeout)
                    return {
                        "status": "success" if command_result.exit_status == 0 else "error",
                        "output": command_result.stdout or "",
                        "error": command_result.stderr or "",
                        "exit_status": command_result.exit_status,
                    }
            except asyncio.TimeoutError:
                log_security_event(
                    SecurityEventType.COMMAND_FAILED,
                    user_id=user_id,
                    details={"reason": "timeout", "timeout": timeout},
                    ip_address=ip_address,
                    severity="warning",
                )
                return {
                    "status": "error",
                    "error": f"Command timed out after {timeout} seconds",
                    "output": "",
                }
            except asyncssh.PermissionDenied:
                return {
                    "status": "error",
                    "error": "SSH authentication failed. Check credentials.",
                    "output": "",
                }
            except asyncssh.ConnectionLost:
                return {
                    "status": "error",
                    "error": "SSH connection lost during command execution",
                    "output": "",
                }
            except (asyncssh.Error, OSError) as exc:
                error_msg = str(exc)
                # Don't expose sensitive details in error messages
                if "private key" in error_msg.lower() or "password" in error_msg.lower():
                    error_msg = "SSH authentication error"
                return {
                    "status": "error",
                    "error": error_msg,
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
        # Use async_db to avoid blocking the event loop
        from config import async_db
        server_response = await async_db(
            lambda: supabase.table("servers").select("*").eq("id", server_id).execute()
        )
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