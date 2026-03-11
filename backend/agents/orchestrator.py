from agents.agents import PlannerAgent, ActionAgent, BuilderAgent, DebuggerAgent, AuditorAgent
from config import redis_client, supabase
from services.execution import execute_action
import json

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
        task = {"state": "CREATED"}

        def _persist_task_state(current_task: dict) -> None:
            if redis_client:
                redis_client.set(f"task:{task_id}", json.dumps(current_task))

        try:
            if redis_client:
                task_data = redis_client.get(f"task:{task_id}")
                if task_data:
                    task = json.loads(task_data)

            plan = await self.planner.create_plan(message)
            task["state"] = "PLANNED"
            _persist_task_state(task)

            action_bundle = await self.action_agent.generate_action(plan)
            action = (action_bundle.get("actions") or [{}])[0] if isinstance(action_bundle, dict) else {}
            task["state"] = "ACTION_GENERATED"
            _persist_task_state(task)

            await self.builder.build(action, {})
            task["state"] = "BUILDING"
            _persist_task_state(task)

            if action.get("server_id"):
                result = await execute_action(action)
                task["state"] = "EXECUTING" if result.get("status") == "success" else "DEBUGGING"
            else:
                task["state"] = "EXECUTING"
            _persist_task_state(task)

            audit_result = await self.auditor.audit(action)
            if isinstance(audit_result, dict) and audit_result.get("approved", False):
                task["state"] = "AUDITING"
                _persist_task_state(task)
                task["state"] = "COMPLETED"
            else:
                task["state"] = "FAILED"
            _persist_task_state(task)
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