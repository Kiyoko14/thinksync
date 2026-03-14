"""
Security audit logging.

Provides structured logging for security-relevant events like:
- Authentication attempts
- Authorization failures  
- Sensitive data access
- Configuration changes
- Command execution
"""

import json
import time
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from config import redis_client, supabase


class SecurityEventType(str, Enum):
    """Types of security events to track."""
    
    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_INVALID = "auth.token.invalid"
    
    # Authorization events
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    AUTHZ_PRIVILEGE_ESCALATION = "authz.privilege.escalation"
    
    # Data access events
    DATA_SENSITIVE_ACCESS = "data.sensitive.access"
    DATA_EXPORT = "data.export"
    DATA_DELETION = "data.deletion"
    
    # Configuration changes
    CONFIG_SERVER_CREATED = "config.server.created"
    CONFIG_SERVER_UPDATED = "config.server.updated"
    CONFIG_SERVER_DELETED = "config.server.deleted"
    CONFIG_SECRET_CREATED = "config.secret.created"
    CONFIG_SECRET_UPDATED = "config.secret.updated"
    CONFIG_SECRET_DELETED = "config.secret.deleted"
    
    # Command execution
    COMMAND_EXECUTED = "command.executed"
    COMMAND_BLOCKED = "command.blocked"
    COMMAND_FAILED = "command.failed"
    
    # Deployment events
    DEPLOYMENT_CREATED = "deployment.created"
    DEPLOYMENT_EXECUTED = "deployment.executed"
    DEPLOYMENT_FAILED = "deployment.failed"
    
    # Security incidents
    INCIDENT_SUSPICIOUS_ACTIVITY = "incident.suspicious.activity"
    INCIDENT_RATE_LIMIT_EXCEEDED = "incident.rate_limit.exceeded"
    INCIDENT_INJECTION_ATTEMPT = "incident.injection.attempt"


def log_security_event(
    event_type: SecurityEventType,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    severity: str = "info",
) -> None:
    """
    Log a security-relevant event.
    
    Args:
        event_type: Type of security event
        user_id: ID of the user who triggered the event
        resource_type: Type of resource involved (server, secret, etc.)
        resource_id: ID of the specific resource
        details: Additional event details (will be JSON serialized)
        ip_address: Source IP address
        severity: Event severity (info, warning, error, critical)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    event = {
        "timestamp": timestamp,
        "event_type": event_type.value,
        "user_id": user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": ip_address,
        "severity": severity,
    }
    
    # Log to console (in production, use proper logging framework)
    print(f"[SECURITY] {json.dumps(event)}")
    
    # Store in Redis for real-time monitoring (with TTL)
    if redis_client:
        try:
            key = f"security:events:{user_id or 'system'}"
            redis_client.lpush(key, json.dumps(event))
            redis_client.ltrim(key, 0, 999)  # Keep last 1000 events
            redis_client.expire(key, 86400 * 7)  # 7 days
            
            # Also increment counters for monitoring
            counter_key = f"security:counters:{event_type.value}"
            redis_client.incr(counter_key)
            redis_client.expire(counter_key, 3600)  # 1 hour window
        except Exception as e:
            print(f"Failed to log to Redis: {e}")
    
    # Store in Supabase for long-term audit trail
    if supabase and severity in ["error", "critical"]:
        try:
            supabase.table("security_audit_log").insert({
                "timestamp": timestamp,
                "event_type": event_type.value,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": event.get("details"),
                "ip_address": ip_address,
                "severity": severity,
            }).execute()
        except Exception as e:
            print(f"Failed to log to Supabase: {e}")


def get_security_events(
    user_id: Optional[str] = None,
    limit: int = 100,
) -> list:
    """
    Retrieve recent security events from Redis.
    
    Args:
        user_id: Filter by user ID (None for all)
        limit: Maximum number of events to return
        
    Returns:
        List of security event dictionaries
    """
    if not redis_client:
        return []
    
    try:
        key = f"security:events:{user_id or 'system'}"
        raw_events = redis_client.lrange(key, 0, limit - 1)
        return [json.loads(e) for e in raw_events]
    except Exception as e:
        print(f"Failed to retrieve security events: {e}")
        return []


def get_security_stats() -> Dict[str, int]:
    """
    Get security event statistics from Redis.
    
    Returns:
        Dictionary mapping event types to counts
    """
    if not redis_client:
        return {}
    
    try:
        stats = {}
        for event_type in SecurityEventType:
            key = f"security:counters:{event_type.value}"
            count = redis_client.get(key)
            if count:
                stats[event_type.value] = int(count)
        return stats
    except Exception as e:
        print(f"Failed to retrieve security stats: {e}")
        return {}


def check_rate_limit(
    user_id: str,
    action: str,
    limit: int = 10,
    window: int = 60,
) -> bool:
    """
    Check if a user has exceeded rate limit for an action.
    
    Args:
        user_id: User ID
        action: Action identifier (e.g., "command_execution")
        limit: Maximum number of actions allowed
        window: Time window in seconds
        
    Returns:
        True if within limit, False if exceeded
    """
    if not redis_client:
        return True  # Allow if Redis unavailable
    
    try:
        key = f"rate_limit:{user_id}:{action}"
        current = redis_client.incr(key)
        
        if current == 1:
            redis_client.expire(key, window)
        
        if current > limit:
            log_security_event(
                SecurityEventType.INCIDENT_RATE_LIMIT_EXCEEDED,
                user_id=user_id,
                details={"action": action, "limit": limit, "window": window},
                severity="warning",
            )
            return False
        
        return True
    except Exception as e:
        print(f"Rate limit check failed: {e}")
        return True  # Allow on error
