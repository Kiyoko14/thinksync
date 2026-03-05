import paramiko
import os
from config import redis_client, supabase
import asyncio

class ExecutionSandbox:
    def __init__(self):
        self.banned_commands = ["rm -rf /", "mkfs", "shutdown", "reboot", "mount", "umount", "passwd", "useradd", "usermod", "chmod 777 /"]
    
    async def execute_action(self, action: dict, server_config: dict):
        # Rate limiting
        if redis_client:
            rate_key = f"rate:{action.get('chat_id')}"
            if redis_client.get(rate_key):
                return {"status": "rate_limited"}
            redis_client.set(rate_key, "1", ex=60)
        
        # Validate command
        if action["action"] == "run_command":
            if any(banned in action["command"] for banned in self.banned_commands):
                return {"status": "blocked", "reason": "banned command"}
        
        # For demo purposes, just return success
        return {"status": "success", "output": "Command executed successfully", "error": ""}

execution_sandbox = ExecutionSandbox()

async def execute_action(action: dict):
    if not supabase:
        return {"status": "error", "error": "Database not configured"}
    
    # Get server config from DB
    server_id = action.get("server_id")
    if not server_id:
        return {"status": "error", "error": "No server_id provided"}
    
    try:
        server_response = supabase.table("servers").select("*").eq("id", server_id).execute()
        if not server_response.data:
            return {"status": "error", "error": "Server not found"}
        server = server_response.data[0]
        
        return await execution_sandbox.execute_action(action, server)
    except Exception as e:
        return {"status": "error", "error": str(e)}