from agents.agents import PlannerAgent, ActionAgent, BuilderAgent, DebuggerAgent, AuditorAgent
from config import redis_client, supabase
from services.execution import execute_action
import json
import asyncio

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
        task_response = supabase.table("tasks").insert(task_data).execute()
        task_id = task_response.data[0]["id"]
        
        # Store in Redis
        if redis_client:
            redis_client.set(f"task:{task_id}", json.dumps(task_data))
        
        # Process through states
        await self.run_task(task_id, message)

    async def run_task(self, task_id: str, message: str):
        if not redis_client:
            return
        
        task = json.loads(redis_client.get(f"task:{task_id}"))
        
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
            if result["status"] == "success":
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

orchestrator = Orchestrator()

async def process_message(chat_id: str, message: str):
    await orchestrator.process_message(chat_id, message)