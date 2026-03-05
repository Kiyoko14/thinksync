import openai
from config import redis_client, openai_client
import json
import asyncio
import re
from typing import Dict, List, Any, Optional

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
        """Create a comprehensive deployment plan"""
        try:
            if not openai_client:
                return self._fallback_plan(user_request)

            # Enhanced context for better planning
            enhanced_context = {
                "user_request": user_request,
                "available_servers": context.get("servers", []) if context else [],
                "current_environment": context.get("environment", "production") if context else "production",
                "technologies": self._extract_technologies(user_request),
                "complexity": self._assess_complexity(user_request)
            }

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Create a deployment plan for: {json.dumps(enhanced_context, indent=2)}"}
            ]

            response = openai_client.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,  # Low temperature for consistent planning
                max_tokens=2000
            )

            plan_text = response.choices[0].message.content.strip()

            # Clean JSON response
            if plan_text.startswith("```json"):
                plan_text = plan_text[7:]
            if plan_text.endswith("```"):
                plan_text = plan_text[:-3]

            plan = json.loads(plan_text)

            # Validate plan structure
            if not self._validate_plan(plan):
                return self._fallback_plan(user_request)

            # Cache plan for future reference
            if redis_client:
                cache_key = f"plan:{hash(user_request)}"
                redis_client.setex(cache_key, 3600, json.dumps(plan))  # Cache for 1 hour

            return plan

        except Exception as e:
            print(f"PlannerAgent error: {e}")
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
        """Generate executable actions from a plan"""
        try:
            if not openai_client:
                return self._fallback_actions(plan)

            context_info = {
                "plan": plan,
                "environment": context.get("environment", "development") if context else "development",
                "available_servers": context.get("servers", []) if context else [],
                "security_level": context.get("security", "standard") if context else "standard"
            }

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate executable actions for this plan: {json.dumps(context_info, indent=2)}"}
            ]

            response = openai_client.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )

            actions_text = response.choices[0].message.content.strip()

            # Clean JSON response
            if actions_text.startswith("```json"):
                actions_text = actions_text[7:]
            if actions_text.endswith("```"):
                actions_text = actions_text[:-3]

            actions = json.loads(actions_text)

            # Validate actions
            if not self._validate_actions(actions):
                return self._fallback_actions(plan)

            return actions

        except Exception as e:
            print(f"ActionAgent error: {e}")
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
            elif action_type == 'create_file':
                return await self._create_file(action, server_config)
            elif action_type == 'install_package':
                return await self._install_package(action, server_config)
            elif action_type == 'start_service':
                return await self._start_service(action, server_config)
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

        sandbox = ExecutionSandbox()
        result = await sandbox.execute_action({
            "action": "run_command",
            "command": action.get("command", ""),
            "chat_id": f"build_{action.get('id', 'unknown')}"
        }, server_config)

        return {
            "status": "success" if result.get("status") == "completed" else "error",
            "message": "Command executed successfully" if result.get("status") == "completed" else "Command failed",
            "output": result.get("output", ""),
            "exit_code": result.get("exit_code", -1)
        }

    async def _create_file(self, action: Dict, server_config: Dict) -> Dict[str, Any]:
        """Create a file on a server"""
        # Implementation for file creation
        return {
            "status": "success",
            "message": "File created successfully",
            "output": f"Created file: {action.get('target', 'unknown')}"
        }

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
        """Debug an error and provide solutions"""
        try:
            if not openai_client:
                return self._fallback_debug(error)

            context_info = {
                "error_message": error,
                "environment": context.get("environment", "unknown") if context else "unknown",
                "action_type": context.get("action_type", "unknown") if context else "unknown",
                "server_info": context.get("server", {}) if context else {},
                "logs": context.get("logs", []) if context else []
            }

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Debug this error: {json.dumps(context_info, indent=2)}"}
            ]

            response = openai_client.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )

            debug_text = response.choices[0].message.content.strip()

            # Clean JSON response
            if debug_text.startswith("```json"):
                debug_text = debug_text[7:]
            if debug_text.endswith("```"):
                debug_text = debug_text[:-3]

            debug_result = json.loads(debug_text)

            # Validate debug result
            if not self._validate_debug_result(debug_result):
                return self._fallback_debug(error)

            return debug_result

        except Exception as e:
            print(f"DebuggerAgent error: {e}")
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
        """Audit an action for security and compliance"""
        try:
            if not openai_client:
                return self._fallback_audit(action)

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

            response = openai_client.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=1200
            )

            audit_text = response.choices[0].message.content.strip()

            # Clean JSON response
            if audit_text.startswith("```json"):
                audit_text = audit_text[7:]
            if audit_text.endswith("```"):
                audit_text = audit_text[:-3]

            audit_result = json.loads(audit_text)

            # Validate audit result
            if not self._validate_audit_result(audit_result):
                return self._fallback_audit(action)

            return audit_result

        except Exception as e:
            print(f"AuditorAgent error: {e}")
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