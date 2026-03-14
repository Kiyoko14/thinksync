from config import redis_client, openai_client, openai_model, supabase, call_openai
from agents.memory import agent_memory
import json
import re
import hashlib
from typing import Dict, List, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cache_key(prefix: str, payload: str) -> str:
    """Create a stable Redis key by hashing *payload*."""
    digest = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return f"{prefix}:{digest}"


def _get_cached(key: str) -> Optional[Dict]:
    """Return a cached dict from Redis, or None."""
    if not redis_client:
        return None
    try:
        raw = redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        print(f"Redis read error ({key}): {e}")
        return None


def _set_cached(key: str, value: Dict, ttl: int = 3600) -> None:
    """Store *value* in Redis with a TTL (seconds)."""
    if not redis_client:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except Exception as e:
        print(f"Redis write error ({key}): {e}")


def _save_agent_log(agent: str, input_hash: str, result: Dict) -> None:
    """Persist an agent result to Supabase for auditing and analytics."""
    if not supabase:
        return
    try:
        supabase.table("agent_logs").insert({
            "agent": agent,
            "input_hash": input_hash,
            "result": result,
        }).execute()
    except Exception as e:
        # Non-fatal — table may not exist in all deployments
        print(f"Supabase agent_logs insert warning: {e}")


class PlannerAgent:
    """AI Agent for creating comprehensive deployment and DevOps plans"""

    SYSTEM_PROMPT = """
You are an expert DevOps Planner Agent specializing in creating detailed, executable deployment plans.

Your responsibilities:
1. Analyze user requests for deployment, infrastructure setup, or DevOps tasks
2. Create step-by-step plans with clear, actionable steps
3. Consider security, scalability, and best practices
4. Include rollback strategies and error handling
5. Specify required tools, dependencies, and configurations

Always respond with a valid JSON object containing:
{
  "plan": [
    {
      "step": "step_number",
      "description": "clear_description",
      "action": "action_type",
      "target": "target_resource",
      "parameters": {},
      "rollback": "rollback_command",
      "timeout": 300
    }
  ],
  "estimated_time": "time_estimate",
  "risk_level": "low|medium|high",
  "prerequisites": ["list_of_requirements"],
  "success_criteria": ["list_of_success_indicators"]
}

Action types: create_directory, write_file, run_command, install_package, configure_service, deploy_application, test_deployment
"""

    async def create_plan(self, user_request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a comprehensive deployment plan.

        Memory usage (E1):
        - Retrieves conversation history from Redis/Supabase and injects it as
          additional context so the planner understands what happened before.
        - Retrieves up to 3 successful past experiences for similar requests
          from Supabase and injects them as learned examples.
        - Caches the resulting plan in Redis (1 h) to avoid repeated API calls.
        - Records the plan as an experience in Supabase for future retrieval.
        - Tracks call/hit counters in Redis for performance monitoring.
        - Publishes a 'plan_created' event to the Redis pub/sub channel.
        """
        try:
            agent_memory.inc_stat("planner", "calls")

            if not openai_client:
                return self._fallback_plan(user_request)

            # ── Cache lookup ──────────────────────────────────────────────
            cache_payload = json.dumps({"request": user_request, "env": (context or {}).get("environment", "production")}, sort_keys=True)
            ckey = _cache_key("plan", cache_payload)
            cached = _get_cached(ckey)
            if cached:
                print(f"PlannerAgent: cache hit ({ckey})")
                agent_memory.inc_stat("planner", "cache_hits")
                return cached

            # ── Memory retrieval ──────────────────────────────────────────
            chat_id = (context or {}).get("chat_id", "")
            task_id = (context or {}).get("task_id", "")

            conversation = agent_memory.get_conversation(chat_id, limit=6) if chat_id else []
            past_experiences = agent_memory.get_experiences("planner", user_request[:80])

            # Enhanced context for better planning
            enhanced_context = {
                "user_request": user_request,
                "available_servers": context.get("servers", []) if context else [],
                "current_environment": context.get("environment", "production") if context else "production",
                "technologies": self._extract_technologies(user_request),
                "complexity": self._assess_complexity(user_request),
                "previous_errors": (context or {}).get("previous_error"),
                "debug_fixes": (context or {}).get("debug_fixes", []),
            }

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
            ]

            # Inject conversation history so the planner is aware of context
            if conversation:
                messages.append({
                    "role": "user",
                    "content": f"Recent conversation context:\n{json.dumps(conversation, indent=2)}"
                })

            # Inject past successful experiences
            if past_experiences:
                messages.append({
                    "role": "user",
                    "content": (
                        "Past successful deployments for similar requests "
                        "(use as reference, adapt as needed):\n"
                        + json.dumps([e.get("payload") for e in past_experiences], indent=2)
                    )
                })

            messages.append({
                "role": "user",
                "content": f"Create a deployment plan for: {json.dumps(enhanced_context, indent=2)}"
            })

            response = await call_openai(
                model=openai_model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent planning
                max_tokens=2000
            )

            plan_text = (response.choices[0].message.content or "").strip()

            # Clean JSON response
            if plan_text.startswith("```json"):
                plan_text = plan_text[7:]
            if plan_text.endswith("```"):
                plan_text = plan_text[:-3]

            plan = json.loads(plan_text)

            # Validate plan structure
            if not self._validate_plan(plan):
                return self._fallback_plan(user_request)

            # ── Persist to Redis and Supabase ─────────────────────────────
            _set_cached(ckey, plan, ttl=3600)
            _save_agent_log("planner", ckey, plan)
            agent_memory.inc_stat("planner", "successes")

            # Record experience for future retrieval
            agent_memory.save_experience(
                chat_id=chat_id,
                task_id=task_id,
                agent="planner",
                request_pattern=user_request[:200],
                outcome="success",
                payload=plan,
            )

            # Publish event so subscribers can react in real time
            agent_memory.publish_event("plan_created", {
                "chat_id": chat_id,
                "task_id": task_id,
                "risk_level": plan.get("risk_level", "unknown"),
                "step_count": len(plan.get("plan", [])),
            })

            return plan

        except Exception as e:
            print(f"PlannerAgent error: {e}")
            agent_memory.inc_stat("planner", "failures")
            return self._fallback_plan(user_request)

    def _extract_technologies(self, request: str) -> List[str]:
        """Extract technology stack from user request"""
        technologies = []
        tech_patterns = {
            'python': r'\bpython\b|\bpip\b|\bflask\b|\bdjango\b|\bfastapi\b',
            'node': r'\bnode\b|\bnpm\b|\bexpress\b|\bnext\b|\breact\b',
            'docker': r'\bdocker\b|\bcontainer\b|\bimage\b',
            'kubernetes': r'\bk8s\b|\bkubernetes\b|\bhelm\b',
            'database': r'\bpostgres\b|\bmysql\b|\bmongo\b|\bsql\b',
            'nginx': r'\bnginx\b|\bapache\b',
            'git': r'\bgit\b|\bgithub\b|\bgitlab\b'
        }

        for tech, pattern in tech_patterns.items():
            if re.search(pattern, request, re.IGNORECASE):
                technologies.append(tech)

        return technologies

    def _assess_complexity(self, request: str) -> str:
        """Assess deployment complexity"""
        complexity_indicators = {
            'high': ['production', 'cluster', 'load balancer', 'monitoring', 'ci/cd'],
            'medium': ['database', 'multiple servers', 'configuration', 'security'],
            'low': ['single server', 'basic app', 'development']
        }

        for level, indicators in complexity_indicators.items():
            if any(indicator in request.lower() for indicator in indicators):
                return level

        return 'medium'

    def _validate_plan(self, plan: Dict) -> bool:
        """Validate plan structure"""
        required_keys = ['plan', 'estimated_time', 'risk_level', 'prerequisites', 'success_criteria']
        return all(key in plan for key in required_keys) and isinstance(plan['plan'], list)

    def _fallback_plan(self, user_request: str) -> Dict[str, Any]:
        """Fallback plan when AI is unavailable"""
        return {
            "plan": [
                {
                    "step": "1",
                    "description": "Analyze requirements",
                    "action": "run_command",
                    "target": "local",
                    "parameters": {"command": f"echo 'Planning deployment for: {user_request}'"},
                    "rollback": "echo 'No rollback needed'",
                    "timeout": 30
                },
                {
                    "step": "2",
                    "description": "Execute deployment",
                    "action": "run_command",
                    "target": "server",
                    "parameters": {"command": "echo 'Deployment completed'"},
                    "rollback": "echo 'Rolling back deployment'",
                    "timeout": 300
                }
            ],
            "estimated_time": "10 minutes",
            "risk_level": "low",
            "prerequisites": ["Server access", "Basic tools installed"],
            "success_criteria": ["Application running", "No errors in logs"]
        }


class ActionAgent:
    """AI Agent for generating specific executable actions from plans"""

    SYSTEM_PROMPT = """
You are an expert Action Generator Agent specializing in converting high-level plans into executable actions.

Your responsibilities:
1. Take deployment plans and break them into specific, executable actions
2. Generate proper commands, scripts, and configurations
3. Ensure actions are safe and follow security best practices
4. Include proper error handling and validation
5. Consider different environments (dev, staging, production)

Always respond with a valid JSON object containing:
{
  "actions": [
    {
      "id": "unique_action_id",
      "type": "action_type",
      "description": "human_readable_description",
      "command": "exact_command_to_execute",
      "parameters": {},
      "server_id": "target_server_id",
      "timeout": 60,
      "dependencies": ["action_ids_to_run_before"],
      "validation": "command_to_verify_success",
      "rollback": "command_to_undo_action"
    }
  ],
  "estimated_execution_time": "time_estimate",
  "parallel_execution": true|false,
  "requires_approval": true|false
}

Action types: run_command, create_file, modify_file, install_package, start_service, stop_service, backup_data, restore_data
"""

    async def generate_action(self, plan: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate executable actions from a plan.

        Memory usage (E1):
        - Checks Redis cache first (30 min TTL per plan hash).
        - Retrieves successful past action sets for similar plans from Supabase
          and injects them so the agent can reuse known-good action patterns.
        - Persists new results to Redis + Supabase.
        - Tracks call / cache-hit counters in Redis.
        - Publishes an 'actions_generated' event to the pub/sub channel.
        """
        try:
            agent_memory.inc_stat("action_agent", "calls")

            if not openai_client:
                return self._fallback_actions(plan)

            # ── Cache lookup ──────────────────────────────────────────────
            cache_payload = json.dumps({"plan": plan, "env": (context or {}).get("environment", "production")}, sort_keys=True)
            ckey = _cache_key("actions", cache_payload)
            cached = _get_cached(ckey)
            if cached:
                print(f"ActionAgent: cache hit ({ckey})")
                agent_memory.inc_stat("action_agent", "cache_hits")
                return cached

            # ── Memory retrieval ──────────────────────────────────────────
            chat_id = (context or {}).get("chat_id", "")
            task_id = (context or {}).get("task_id", "")
            plan_summary = str(plan.get("plan", []))[:120]
            past_experiences = agent_memory.get_experiences("action_agent", plan_summary)

            context_info: Dict[str, Any] = {
                "plan": plan,
                "environment": context.get("environment", "production") if context else "production",
                "available_servers": context.get("servers", []) if context else [],
                "security_level": context.get("security", "standard") if context else "standard",
                "previous_attempt": (context or {}).get("previous_attempt"),
                "debug_fixes": (context or {}).get("debug_fixes", []),
            }

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
            ]

            if past_experiences:
                messages.append({
                    "role": "user",
                    "content": (
                        "Previously successful action sets for similar plans "
                        "(reuse patterns where applicable):\n"
                        + json.dumps([e.get("payload") for e in past_experiences], indent=2)
                    )
                })

            messages.append({
                "role": "user",
                "content": f"Generate executable actions for this plan: {json.dumps(context_info, indent=2)}"
            })

            response = await call_openai(
                model=openai_model,
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )

            actions_text = (response.choices[0].message.content or "").strip()

            # Clean JSON response
            if actions_text.startswith("```json"):
                actions_text = actions_text[7:]
            if actions_text.endswith("```"):
                actions_text = actions_text[:-3]

            actions = json.loads(actions_text)

            # Validate actions
            if not self._validate_actions(actions):
                return self._fallback_actions(plan)

            # ── Persist to Redis and Supabase ─────────────────────────────
            _set_cached(ckey, actions, ttl=1800)
            _save_agent_log("action", ckey, actions)
            agent_memory.inc_stat("action_agent", "successes")

            agent_memory.save_experience(
                chat_id=chat_id,
                task_id=task_id,
                agent="action_agent",
                request_pattern=plan_summary,
                outcome="success",
                payload=actions,
            )

            agent_memory.publish_event("actions_generated", {
                "chat_id": chat_id,
                "task_id": task_id,
                "action_count": len(actions.get("actions", [])),
                "parallel": actions.get("parallel_execution", False),
            })

            return actions

        except Exception as e:
            print(f"ActionAgent error: {e}")
            agent_memory.inc_stat("action_agent", "failures")
            return self._fallback_actions(plan)

    def _validate_actions(self, actions: Dict) -> bool:
        """Validate actions structure"""
        return 'actions' in actions and isinstance(actions['actions'], list)

    def _fallback_actions(self, plan: Dict) -> Dict[str, Any]:
        """Fallback actions when AI is unavailable"""
        return {
            "actions": [
                {
                    "id": "fallback_action_1",
                    "type": "run_command",
                    "description": "Execute deployment command",
                    "command": "echo 'Executing deployment step'",
                    "parameters": {},
                    "server_id": "default",
                    "timeout": 60,
                    "dependencies": [],
                    "validation": "echo 'success'",
                    "rollback": "echo 'rollback completed'"
                }
            ],
            "estimated_execution_time": "2 minutes",
            "parallel_execution": False,
            "requires_approval": False
        }


class BuilderAgent:
    """AI Agent for building and deploying applications"""

    SYSTEM_PROMPT = """
You are an expert Builder Agent specializing in application deployment and infrastructure setup.

Your responsibilities:
1. Execute deployment actions safely and efficiently
2. Handle different deployment types (Docker, Kubernetes, bare-metal)
3. Monitor deployment progress and handle errors
4. Ensure proper configuration and environment setup
5. Validate deployment success and rollback if needed

You have access to:
- File system operations
- Command execution on remote servers
- Package installation and configuration
- Service management
- Database operations

Always provide detailed execution logs and status updates.
"""

    async def build(self, action: Dict[str, Any], server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a build/deployment action"""
        try:
            action_type = action.get('type', 'run_command')

            if action_type == 'run_command':
                return await self._execute_command(action, server_config)
            elif action_type in ('create_file', 'write_file'):
                return await self._create_file(action, server_config)
            elif action_type == 'modify_file':
                return await self._modify_file(action, server_config)
            elif action_type == 'install_package':
                return await self._install_package(action, server_config)
            elif action_type == 'start_service':
                return await self._start_service(action, server_config)
            elif action_type == 'stop_service':
                return await self._stop_service(action, server_config)
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported action type: {action_type}",
                    "output": ""
                }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "output": "",
                "rollback_needed": True
            }

    async def _execute_command(self, action: Dict, server_config: Dict) -> Dict[str, Any]:
        """Execute a command on a server"""
        from services.execution import ExecutionSandbox
        import shlex

        sandbox = ExecutionSandbox()
        base_command = action.get("command", "")
        workspace_path = action.get("workspace_path") or server_config.get("workspace_path")

        if workspace_path and base_command.strip():
            quoted_workspace = shlex.quote(str(workspace_path))
            command = f"mkdir -p {quoted_workspace} && cd {quoted_workspace} && {base_command}"
        else:
            command = base_command

        result = await sandbox.execute_action({
            "action": "run_command",
            "command": command,
            "chat_id": f"build_{action.get('id', 'unknown')}"
        }, server_config)

        success = result.get("status") == "success"
        return {
            "status": "success" if success else "error",
            "message": "Command executed successfully" if success else "Command failed",
            "output": result.get("output", ""),
            "exit_code": result.get("exit_status", result.get("exit_code", -1))
        }

    async def _create_file(self, action: Dict, server_config: Dict) -> Dict[str, Any]:
        """Create a file on a remote server via SSH.

        If the action already carries a ``command`` field the AI generated
        (e.g. a heredoc), that is used as-is.  Otherwise the file content is
        taken from ``action["parameters"]["content"]`` and written via a
        base64-encoded pipeline so that any special characters are handled
        safely.
        """
        import base64
        import os
        import shlex

        # Prefer an AI-generated command if present
        if action.get("command"):
            return await self._execute_command(action, server_config)

        file_path = (
            action.get("target")
            or action.get("parameters", {}).get("path", "")
        )
        content = action.get("parameters", {}).get("content", "")

        if not file_path:
            return {
                "status": "error",
                "message": "File path (target or parameters.path) is required for create_file",
                "output": "",
            }

        # Base64-encode the content to avoid any shell quoting/escaping issues
        content_b64 = base64.b64encode(content.encode("utf-8")).decode()
        # Safely quote the file path so special characters cannot break the command
        quoted_path = shlex.quote(file_path)
        dir_path = os.path.dirname(file_path)
        mkdir_part = f"mkdir -p {shlex.quote(dir_path)} && " if dir_path and dir_path != "/" else ""
        # Use double-quotes for the base64 payload (output is [A-Za-z0-9+/=] only,
        # but double-quotes are semantically cleaner inside a shell command).
        command = f'{mkdir_part}printf "%s" "{content_b64}" | base64 -d > {quoted_path}'

        result = await self._execute_command(
            {"command": command, "id": action.get("id")},
            server_config,
        )
        if result.get("status") == "success":
            result["message"] = f"File created: {file_path}"
        return result

    async def _modify_file(self, action: Dict, server_config: Dict) -> Dict[str, Any]:
        """Overwrite an existing file on a remote server (same as create_file)."""
        return await self._create_file(action, server_config)

    async def _install_package(self, action: Dict, server_config: Dict) -> Dict[str, Any]:
        """Install a package on a server"""
        package_name = action.get("parameters", {}).get("package", "")
        package_manager = action.get("parameters", {}).get("manager", "apt")

        commands = {
            "apt": f"apt update && apt install -y {package_name}",
            "yum": f"yum install -y {package_name}",
            "pip": f"pip install {package_name}",
            "npm": f"npm install {package_name}"
        }

        command = commands.get(package_manager, f"echo 'Unsupported package manager: {package_manager}'")

        return await self._execute_command({
            "command": command,
            "id": action.get("id")
        }, server_config)

    async def _start_service(self, action: Dict, server_config: Dict) -> Dict[str, Any]:
        """Start a service on a server"""
        service_name = action.get("parameters", {}).get("service", "")
        command = f"systemctl start {service_name} && systemctl enable {service_name}"

        return await self._execute_command({
            "command": command,
            "id": action.get("id")
        }, server_config)

    async def _stop_service(self, action: Dict, server_config: Dict) -> Dict[str, Any]:
        """Stop a service on a server"""
        service_name = action.get("parameters", {}).get("service", "")
        command = f"systemctl stop {service_name}"

        return await self._execute_command({
            "command": command,
            "id": action.get("id")
        }, server_config)

class DebuggerAgent:
    """AI Agent for debugging deployment issues and errors"""

    SYSTEM_PROMPT = """
You are an expert Debugger Agent specializing in troubleshooting deployment and infrastructure issues.

Your responsibilities:
1. Analyze error messages and logs
2. Identify root causes of deployment failures
3. Suggest specific fixes and workarounds
4. Provide preventive measures for future deployments
5. Generate rollback procedures when needed

Always respond with a valid JSON object containing:
{
  "analysis": "detailed_error_analysis",
  "root_cause": "identified_root_cause",
  "severity": "low|medium|high|critical",
  "fixes": [
    {
      "description": "fix_description",
      "commands": ["command1", "command2"],
      "priority": "high|medium|low",
      "estimated_time": "time_estimate"
    }
  ],
  "preventive_measures": ["measure1", "measure2"],
  "rollback_procedure": ["step1", "step2"],
  "recommendations": ["rec1", "rec2"]
}
"""

    async def debug(self, error: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Debug an error and provide solutions.

        Memory usage (E1):
        - Checks Redis cache (15 min) — identical errors in the same env are
          very likely to have the same root cause.
        - Queries Supabase ``agent_experiences`` for known fixes of similar
          errors and injects them, allowing the agent to self-heal faster on
          repeated issues without an OpenAI round-trip.
        - Records new fixes as experiences for future retrieval.
        - Tracks stats and publishes 'debug_completed' events.
        """
        try:
            agent_memory.inc_stat("debugger", "calls")

            if not openai_client:
                return self._fallback_debug(error)

            # ── Cache lookup ──────────────────────────────────────────────
            cache_payload = json.dumps({
                "error": error,
                "env": (context or {}).get("environment", "unknown"),
                "action_type": (context or {}).get("action_type", "unknown"),
            }, sort_keys=True)
            ckey = _cache_key("debug", cache_payload)
            cached = _get_cached(ckey)
            if cached:
                print(f"DebuggerAgent: cache hit ({ckey})")
                agent_memory.inc_stat("debugger", "cache_hits")
                return cached

            # ── Known-fix retrieval (long-term memory) ────────────────────
            chat_id = (context or {}).get("chat_id", "")
            task_id = (context or {}).get("task_id", "")
            known_fixes = agent_memory.get_experiences("debugger", error[:80])

            context_info: Dict[str, Any] = {
                "error_message": error,
                "environment": context.get("environment", "unknown") if context else "unknown",
                "action_type": context.get("action_type", "unknown") if context else "unknown",
                "server_info": context.get("server", {}) if context else {},
                "logs": context.get("logs", []) if context else [],
            }

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
            ]

            if known_fixes:
                messages.append({
                    "role": "user",
                    "content": (
                        "Known fixes that resolved similar errors in the past "
                        "(prefer these if they match the current situation):\n"
                        + json.dumps([f.get("payload") for f in known_fixes], indent=2)
                    )
                })

            messages.append({
                "role": "user",
                "content": f"Debug this error: {json.dumps(context_info, indent=2)}"
            })

            response = await call_openai(
                model=openai_model,
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )

            debug_text = (
                response.choices[0].message.content
                if response and response.choices
                else ""
            ).strip()

            # Clean JSON response
            if debug_text.startswith("```json"):
                debug_text = debug_text[7:]
            if debug_text.endswith("```"):
                debug_text = debug_text[:-3]

            debug_result = json.loads(debug_text)

            # Validate debug result
            if not self._validate_debug_result(debug_result):
                return self._fallback_debug(error)

            # ── Persist to Redis and Supabase ─────────────────────────────
            _set_cached(ckey, debug_result, ttl=900)
            _save_agent_log("debugger", ckey, debug_result)
            agent_memory.inc_stat("debugger", "successes")

            # Record as a known fix for future self-healing
            agent_memory.save_experience(
                chat_id=chat_id,
                task_id=task_id,
                agent="debugger",
                request_pattern=error[:200],
                outcome="success",
                payload=debug_result,
            )

            agent_memory.publish_event("debug_completed", {
                "chat_id": chat_id,
                "task_id": task_id,
                "severity": debug_result.get("severity", "unknown"),
                "root_cause": debug_result.get("root_cause", "")[:120],
            })

            return debug_result

        except Exception as e:
            print(f"DebuggerAgent error: {e}")
            agent_memory.inc_stat("debugger", "failures")
            return self._fallback_debug(error)

    def _validate_debug_result(self, result: Dict) -> bool:
        """Validate debug result structure"""
        required_keys = ['analysis', 'root_cause', 'severity', 'fixes']
        return all(key in result for key in required_keys)

    def _fallback_debug(self, error: str) -> Dict[str, Any]:
        """Fallback debug when AI is unavailable"""
        return {
            "analysis": f"Error occurred: {error}",
            "root_cause": "Unknown - manual investigation required",
            "severity": "medium",
            "fixes": [
                {
                    "description": "Check system logs for more details",
                    "commands": ["journalctl -u application", "tail -f /var/log/application.log"],
                    "priority": "high",
                    "estimated_time": "5 minutes"
                }
            ],
            "preventive_measures": ["Add proper error handling", "Implement monitoring"],
            "rollback_procedure": ["Stop the service", "Restore backup", "Restart with previous version"],
            "recommendations": ["Add logging", "Implement health checks", "Use configuration management"]
        }


class AuditorAgent:
    """AI Agent for security auditing and compliance checking"""

    SYSTEM_PROMPT = """
You are an expert Security Auditor Agent specializing in DevOps security and compliance.

Your responsibilities:
1. Audit commands, configurations, and deployments for security issues
2. Check for compliance with security best practices
3. Identify potential vulnerabilities and risks
4. Suggest security improvements and hardening measures
5. Ensure compliance with industry standards (OWASP, CIS, NIST)

Security checks include:
- Command injection prevention
- Privilege escalation risks
- Data exposure vulnerabilities
- Network security issues
- Configuration security
- Access control validation

Always respond with a valid JSON object containing:
{
  "audit_result": "pass|fail|warning",
  "risk_level": "low|medium|high|critical",
  "security_issues": [
    {
      "type": "vulnerability_type",
      "severity": "severity_level",
      "description": "detailed_description",
      "location": "where_issue_found",
      "remediation": "how_to_fix",
      "cve": "cve_id_if_applicable"
    }
  ],
  "compliance_score": 0-100,
  "recommendations": ["security_recommendation1", "security_recommendation2"],
  "approved": true|false
}
"""

    async def audit(self, action: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Audit an action for security and compliance.

        Memory usage (E1):
        - Caches results in Redis (2 hours) — identical actions in the same
          environment always receive the same audit decision.
        - Tracks call / cache-hit counters in Redis.
        - Publishes 'audit_completed' events to the pub/sub channel.
        """
        try:
            agent_memory.inc_stat("auditor", "calls")

            if not openai_client:
                return self._fallback_audit(action)

            # ── Cache lookup ──────────────────────────────────────────────
            cache_payload = json.dumps({
                "action": action,
                "env": (context or {}).get("environment", "production"),
            }, sort_keys=True)
            ckey = _cache_key("audit", cache_payload)
            cached = _get_cached(ckey)
            if cached:
                print(f"AuditorAgent: cache hit ({ckey})")
                agent_memory.inc_stat("auditor", "cache_hits")
                return cached

            audit_context = {
                "action": action,
                "environment": context.get("environment", "production") if context else "production",
                "user_permissions": context.get("permissions", "standard") if context else "standard",
                "compliance_requirements": context.get("compliance", ["basic_security"]) if context else ["basic_security"]
            }

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Audit this action for security: {json.dumps(audit_context, indent=2)}"}
            ]

            response = await call_openai(
                model=openai_model,
                messages=messages,
                temperature=0.1,
                max_tokens=1200
            )

            audit_text = (response.choices[0].message.content or "").strip()

            # Clean JSON response
            if audit_text.startswith("```json"):
                audit_text = audit_text[7:]
            if audit_text.endswith("```"):
                audit_text = audit_text[:-3]

            audit_result = json.loads(audit_text)

            # Validate audit result
            if not self._validate_audit_result(audit_result):
                return self._fallback_audit(action)

            # ── Persist to Redis and Supabase ─────────────────────────────
            _set_cached(ckey, audit_result, ttl=7200)
            _save_agent_log("auditor", ckey, audit_result)
            agent_memory.inc_stat("auditor", "successes")

            chat_id = (context or {}).get("chat_id", "")
            task_id = (context or {}).get("task_id", "")
            agent_memory.publish_event("audit_completed", {
                "chat_id": chat_id,
                "task_id": task_id,
                "approved": audit_result.get("approved", False),
                "risk_level": audit_result.get("risk_level", "unknown"),
                "compliance_score": audit_result.get("compliance_score", 0),
            })

            return audit_result

        except Exception as e:
            print(f"AuditorAgent error: {e}")
            agent_memory.inc_stat("auditor", "failures")
            return self._fallback_audit(action)

    def _validate_audit_result(self, result: Dict) -> bool:
        """Validate audit result structure"""
        required_keys = ['audit_result', 'risk_level', 'approved']
        return all(key in result for key in required_keys)

    def _fallback_audit(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback audit when AI is unavailable"""
        # Basic security checks
        command = action.get("command", "") if isinstance(action, dict) else str(action)
        approved = True
        issues = []

        # Check for dangerous commands
        dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'mkfs',
            r'shutdown',
            r'reboot',
            r'passwd',
            r'useradd',
            r'usermod',
            r'chmod\s+777',
            r'wget.*\|\s*sh',
            r'curl.*\|\s*sh'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                approved = False
                issues.append({
                    "type": "dangerous_command",
                    "severity": "high",
                    "description": f"Command contains dangerous pattern: {pattern}",
                    "location": "command",
                    "remediation": "Remove dangerous command or implement proper safeguards",
                    "cve": ""
                })

        return {
            "audit_result": "pass" if approved else "fail",
            "risk_level": "high" if not approved else "low",
            "security_issues": issues,
            "compliance_score": 80 if approved else 30,
            "recommendations": [
                "Implement command whitelisting",
                "Add manual approval for high-risk commands",
                "Use least privilege principle",
                "Regular security audits"
            ],
            "approved": approved
        }


class AutonomousDevOpsAgent:
    """Autonomous meta-agent that plans, executes, audits, and self-heals."""

    MAX_ATTEMPTS = 3

    def __init__(self):
        self.planner = PlannerAgent()
        self.action_agent = ActionAgent()
        self.builder = BuilderAgent()
        self.debugger = DebuggerAgent()
        self.auditor = AuditorAgent()

    async def run(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        history: List[Dict[str, Any]] = []
        last_error = ""
        chat_id = context.get("chat_id", "")
        task_id = context.get("task_id", "")

        # ── Initialise working memory for this task ────────────────────────
        agent_memory.set_working(task_id,
            status="running",
            attempt=0,
            user_request=user_request[:200],
            chat_id=chat_id,
        )
        agent_memory.inc_stat("autonomous", "calls")
        agent_memory.publish_event("task_started", {
            "chat_id": chat_id,
            "task_id": task_id,
            "request": user_request[:120],
        })

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            # Update working memory for each attempt
            agent_memory.set_working(task_id, attempt=attempt, stage="planning")

            try:
                plan = await self.planner.create_plan(user_request, context)
                agent_memory.set_working(task_id, stage="action_generation",
                                         plan_risk=plan.get("risk_level", "unknown"))

                action_bundle = await self.action_agent.generate_action(plan, context)
                actions = action_bundle.get("actions", []) if isinstance(action_bundle, dict) else []

                if not actions:
                    agent_memory.set_working(task_id, status="failed", error="no_actions")
                    agent_memory.publish_event("task_failed", {
                        "chat_id": chat_id, "task_id": task_id,
                        "reason": "No actions generated", "attempt": attempt,
                    })
                    return {
                        "status": "failed",
                        "attempt": attempt,
                        "error": "No actions generated",
                        "history": history,
                    }

                step_results: List[Dict[str, Any]] = []
                agent_memory.set_working(task_id, stage="executing",
                                         total_actions=len(actions))

                for idx, action in enumerate(actions):
                    agent_memory.set_working(task_id,
                        current_action=idx + 1,
                        action_type=action.get("type", "run_command"),
                    )

                    audit = await self.auditor.audit(action, context)
                    if not audit.get("approved", False):
                        step_results.append({
                            "action": action,
                            "audit": audit,
                            "result": {"status": "blocked", "reason": "audit_rejected"}
                        })
                        agent_memory.set_working(task_id, status="blocked")
                        agent_memory.publish_event("task_blocked", {
                            "chat_id": chat_id, "task_id": task_id,
                            "reason": "Action rejected by security auditor", "attempt": attempt,
                        })
                        return {
                            "status": "blocked",
                            "attempt": attempt,
                            "history": history + step_results,
                            "error": "Action rejected by security auditor",
                        }

                    build_result = await self.builder.build(
                        action,
                        {
                            **context.get("server_config", {}),
                            "workspace_path": context.get("workspace_path", "/"),
                        },
                    )
                    step_results.append({
                        "action": action,
                        "audit": audit,
                        "result": build_result,
                    })

                    if build_result.get("status") != "success":
                        last_error = build_result.get("message", "Unknown execution failure")
                        agent_memory.set_working(task_id, stage="debugging",
                                                 last_error=last_error[:200])

                        debug = await self.debugger.debug(last_error, {
                            "environment": context.get("environment", "production"),
                            "action_type": action.get("type", "run_command"),
                            "server": context.get("server_config", {}),
                            "logs": [build_result.get("output", "")],
                            "chat_id": chat_id,
                            "task_id": task_id,
                        })
                        history.extend(step_results)
                        history.append({"debug": debug, "attempt": attempt})

                        # Feed fixes into the next planning round for self-healing.
                        context = {
                            **context,
                            "previous_error": last_error,
                            "debug_fixes": debug.get("fixes", []),
                            "previous_attempt": attempt,
                        }
                        break
                else:
                    history.extend(step_results)

                    # Record the successful experience in long-term memory
                    agent_memory.save_experience(
                        chat_id=chat_id,
                        task_id=task_id,
                        agent="autonomous",
                        request_pattern=user_request[:200],
                        outcome="success",
                        payload={
                            "plan": plan,
                            "actions": actions,
                            "attempt": attempt,
                        },
                    )
                    agent_memory.set_working(task_id, status="completed", attempt=attempt)
                    agent_memory.inc_stat("autonomous", "successes")
                    agent_memory.publish_event("task_completed", {
                        "chat_id": chat_id, "task_id": task_id,
                        "attempt": attempt,
                        "action_count": len(actions),
                    })

                    return {
                        "status": "completed",
                        "attempt": attempt,
                        "plan": plan,
                        "actions": actions,
                        "history": history,
                    }

            except Exception as e:
                last_error = str(e)
                debug = await self.debugger.debug(last_error, {
                    "environment": context.get("environment", "production"),
                    "action_type": "orchestration",
                    "server": context.get("server_config", {}),
                    "logs": [],
                    "chat_id": chat_id,
                    "task_id": task_id,
                })
                history.append({"debug": debug, "attempt": attempt})

        # All attempts exhausted
        agent_memory.save_experience(
            chat_id=chat_id,
            task_id=task_id,
            agent="autonomous",
            request_pattern=user_request[:200],
            outcome="failure",
            payload={"error": last_error, "history_len": len(history)},
        )
        agent_memory.set_working(task_id, status="failed", error=last_error[:200])
        agent_memory.inc_stat("autonomous", "failures")
        agent_memory.publish_event("task_failed", {
            "chat_id": chat_id, "task_id": task_id,
            "reason": last_error or "Autonomous execution failed",
            "attempt": self.MAX_ATTEMPTS,
        })

        return {
            "status": "failed",
            "attempt": self.MAX_ATTEMPTS,
            "error": last_error or "Autonomous execution failed",
            "history": history,
        }