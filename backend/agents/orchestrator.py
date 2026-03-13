from agents.agents import PlannerAgent, ActionAgent, BuilderAgent, DebuggerAgent, AuditorAgent, AutonomousDevOpsAgent
from config import redis_client, supabase
from services.execution import execute_action
import json

STATES = ["CREATED", "PLANNED", "ACTION_GENERATED", "BUILDING", "EXECUTING", "DEBUGGING", "AUDITING", "COMPLETED", "FAILED"]

# Redis TTL for task state (24 hours — keeps active tasks available but avoids
# unbounded memory growth on Upstash / managed Redis instances).
TASK_TTL_SECONDS = 86400


class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.action_agent = ActionAgent()
        self.builder = BuilderAgent()
        self.debugger = DebuggerAgent()
        self.auditor = AuditorAgent()
        self.autonomous = AutonomousDevOpsAgent()

    async def process_message(self, chat_id: str, message: str):
        if not supabase:
            return {"error": "Database not configured"}
        
        # Create task record in Supabase
        task_data = {
            "chat_id": chat_id,
            "state": "CREATED",
            "step": "planning",
            "attempts": 0
        }
        try:
            task_response = supabase.table("tasks").insert(task_data).execute()
            task_id = task_response.data[0]["id"]
            
            # Mirror task state into Redis for fast lookups (with TTL)
            if redis_client:
                try:
                    redis_client.setex(f"task:{task_id}", TASK_TTL_SECONDS, json.dumps(task_data))
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
            """Write task state to Redis (TTL-bounded) and Supabase."""
            if redis_client:
                try:
                    redis_client.setex(f"task:{task_id}", TASK_TTL_SECONDS, json.dumps(current_task))
                except Exception as e:
                    print(f"Warning: Redis task persist failed: {e}")
            if supabase:
                try:
                    supabase.table("tasks").update({
                        "state": current_task.get("state", "FAILED"),
                        "step": current_task.get("step", ""),
                    }).eq("id", task_id).execute()
                except Exception as e:
                    print(f"Warning: Supabase task update failed: {e}")

        try:
            # Prefer Redis for fast state read; fall back to default
            if redis_client:
                try:
                    task_data = redis_client.get(f"task:{task_id}")
                    if task_data:
                        task = json.loads(task_data)
                except Exception as e:
                    print(f"Warning: Redis task read failed: {e}")

            task["state"] = "PLANNED"
            _persist_task_state(task)

            auto_result = await self.autonomous.run(
                message,
                {
                    "environment": "production",
                    "task_id": task_id,
                },
            )

            status = auto_result.get("status")
            if status == "completed":
                task["state"] = "COMPLETED"
            elif status == "blocked":
                task["state"] = "AUDITING"
            else:
                task["state"] = "FAILED"

            task["autonomous_result"] = auto_result
            _persist_task_state(task)

            # Persist completed task history to Supabase for analytics
            if status == "completed" and supabase:
                try:
                    supabase.table("tasks").update({
                        "state": "COMPLETED",
                        "result": auto_result,
                    }).eq("id", task_id).execute()
                except Exception as e:
                    print(f"Warning: Supabase task completion update failed: {e}")

            # Keep compatibility with external executor for server-bound commands.
            if status == "completed":
                actions = auto_result.get("actions", [])
                for action in actions:
                    if action.get("server_id"):
                        result = await execute_action(action)
                        if result.get("status") != "success":
                            task["state"] = "DEBUGGING"
                            task["execution_error"] = result
                            _persist_task_state(task)
                            break
        except Exception as e:
            print(f"Error in task processing: {e}")
            try:
                task["state"] = "FAILED"
                task["error"] = str(e)
                _persist_task_state(task)
            except Exception:
                pass

orchestrator = Orchestrator()

async def process_message(chat_id: str, message: str):
    """Entry point for message processing"""
    return await orchestrator.process_message(chat_id, message)