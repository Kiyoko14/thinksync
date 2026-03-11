from config import redis_client, supabase
import asyncio
from typing import Dict, Any

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
            
            # For demo purposes, return success with safety
            return {
                "status": "success", 
                "output": "Command executed successfully", 
                "error": "",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

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