from agents.agents import PlannerAgent, ActionAgent, BuilderAgent, DebuggerAgent, AuditorAgent
from config import redis_client, supabase
from services.execution import execute_action
import json
import asyncio
from typing import Optional

STATES = ["CREATED", "PLANNED", "ACTION_GENERATED", "BUILDING", "EXECUTING", "DEBUGGING", "AUDITING", "COMPLETED", "FAILED"]

class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.action_agent = ActionAgent()
        self.builder = BuilderAgent()
        self.debugger = DebuggerAgent()
        self.auditor = AuditorAgent()

    async def process_message(self, chat_id: str, message: str):
        if not supabase:
            return {"error": "Database not configured"}
        
        # Create task
        task_data = {
            "chat_id": chat_id,
            "state": "CREATED",
            "step": "planning",
            "attempts": 0
        }
        try:
            task_response = supabase.table("tasks").insert(task_data).execute()
            task_id = task_response.data[0]["id"]
            
            # Store in Redis if available
            if redis_client:
                try:
                    redis_client.set(f"task:{task_id}", json.dumps(task_data))
                except Exception as e:
                    print(f"Warning: Failed to store task in Redis: {e}")
            
            # Process through states
            await self.run_task(task_id, message)
            return {"task_id": task_id, "status": "initiated"}
        except Exception as e:
            print(f"Error creating task: {e}")
            return {"error": str(e)}

    async def run_task(self, task_id: str, message: str):
        """Run task with proper error handling"""
        if not redis_client:
            print("Warning: Redis not available, task monitoring disabled")
            return
        
        try:
            task_data = redis_client.get(f"task:{task_id}")
            if not task_data:
                print(f"Task {task_id} not found in Redis")
                return
                
            task = json.loads(task_data)
            
            if task["state"] == "CREATED":
                plan = await self.planner.create_plan(message)
                task["state"] = "PLANNED"
                redis_client.set(f"task:{task_id}", json.dumps(task))
                
            if task["state"] == "PLANNED":
                action = await self.action_agent.generate_action(plan)
                task["state"] = "ACTION_GENERATED"
                redis_client.set(f"task:{task_id}", json.dumps(task))
                
            if task["state"] == "ACTION_GENERATED":
                await self.builder.build(action)
                task["state"] = "BUILDING"
                redis_client.set(f"task:{task_id}", json.dumps(task))
                
            if task["state"] == "BUILDING":
                result = await execute_action(action)
                if result.get("status") == "success":
                    task["state"] = "EXECUTING"
                else:
                    task["state"] = "DEBUGGING"
                redis_client.set(f"task:{task_id}", json.dumps(task))
                
            if task["state"] == "EXECUTING":
                audit_passed = await self.auditor.audit(action)
                if audit_passed:
                    task["state"] = "AUDITING"
                else:
                    task["state"] = "FAILED"
                redis_client.set(f"task:{task_id}", json.dumps(task))
                
            if task["state"] == "AUDITING":
                task["state"] = "COMPLETED"
                redis_client.set(f"task:{task_id}", json.dumps(task))
        except Exception as e:
            print(f"Error in task processing: {e}")
            if redis_client:
                try:
                    task["state"] = "FAILED"
                    task["error"] = str(e)
                    redis_client.set(f"task:{task_id}", json.dumps(task))
                except:
                    pass

orchestrator = Orchestrator()

async def process_message(chat_id: str, message: str):
    """Entry point for message processing"""
    return await orchestrator.process_message(chat_id, message)