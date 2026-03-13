"""
AgentMemory — E1-level unified memory layer for all agents.

┌──────────────────┬────────────────────────────────────────────────┐
│  Short-term      │  Redis list    mem:conv:{chat_id}              │
│  (conversation)  │  Last 20 messages per chat, TTL 24 h           │
├──────────────────┼────────────────────────────────────────────────┤
│  Working memory  │  Redis hash    mem:work:{task_id}              │
│  (current task)  │  Live intermediate state, TTL 2 h              │
├──────────────────┼────────────────────────────────────────────────┤
│  Long-term       │  Supabase agent_experiences table              │
│  (experiences)   │  Successful / failed patterns for retrieval    │
├──────────────────┼────────────────────────────────────────────────┤
│  Metrics         │  Redis hash    mem:stats:{agent}               │
│                  │  Counters: calls, cache_hits, successes…       │
├──────────────────┼────────────────────────────────────────────────┤
│  Event stream    │  Redis pub/sub  agent:events                   │
│                  │  Real-time agent lifecycle events               │
└──────────────────┴────────────────────────────────────────────────┘
"""

from config import redis_client, supabase
import json
import time
from typing import Any, Dict, List, Optional

# ── TTLs ──────────────────────────────────────────────────────────────────────
_CONV_TTL = 86_400        # 24 h  — conversation window
_WORK_TTL = 7_200         # 2 h   — working memory per task
_STATS_TTL = 2_592_000    # 30 d  — agent performance metrics

_CONV_MAX_MESSAGES = 20   # keep last N messages per chat

AGENT_EVENTS_CHANNEL = "agent:events"

# Canonical list of agent names — used for stats queries and metrics.
KNOWN_AGENTS = ["planner", "action_agent", "debugger", "auditor", "autonomous"]


class AgentMemory:
    """
    Unified memory layer shared by all agents in the system.
    All methods are fail-safe: missing Redis/Supabase connections are handled
    gracefully so agents remain functional without any external store.
    """

    # ── Short-term / conversation memory ──────────────────────────────────────

    def remember_message(self, chat_id: str, role: str, content: str) -> None:
        """Append a message to the Redis conversation window for *chat_id*."""
        if not redis_client or not chat_id:
            return
        key = f"mem:conv:{chat_id}"
        entry = json.dumps({"role": role, "content": content, "ts": time.time()})
        try:
            pipe = redis_client.pipeline()
            pipe.rpush(key, entry)
            pipe.ltrim(key, -_CONV_MAX_MESSAGES, -1)
            pipe.expire(key, _CONV_TTL)
            pipe.execute()
        except Exception as e:
            print(f"AgentMemory.remember_message error: {e}")

    def get_conversation(self, chat_id: str, limit: int = 10) -> List[Dict]:
        """Return the most recent *limit* messages for this chat.

        Primary: Redis list.
        Fallback: Supabase ``messages`` table (already exists in the schema).
        """
        if redis_client and chat_id:
            try:
                raw = redis_client.lrange(f"mem:conv:{chat_id}", -limit, -1)
                if raw:
                    return [json.loads(r) for r in raw]
            except Exception as e:
                print(f"AgentMemory.get_conversation redis error: {e}")

        if supabase and chat_id:
            try:
                resp = (
                    supabase.table("messages")
                    .select("role,content,created_at")
                    .eq("chat_id", chat_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                msgs = resp.data or []
                return [{"role": m["role"], "content": m["content"]} for m in reversed(msgs)]
            except Exception as e:
                print(f"AgentMemory.get_conversation supabase error: {e}")

        return []

    # ── Working memory (per-task intermediate state) ──────────────────────────

    def set_working(self, task_id: str, **fields: Any) -> None:
        """Store arbitrary key-value pairs for the current task in a Redis hash."""
        if not redis_client or not task_id:
            return
        key = f"mem:work:{task_id}"
        try:
            string_fields = {
                k: json.dumps(v) if not isinstance(v, str) else v
                for k, v in fields.items()
            }
            pipe = redis_client.pipeline()
            pipe.hset(key, mapping=string_fields)
            pipe.expire(key, _WORK_TTL)
            pipe.execute()
        except Exception as e:
            print(f"AgentMemory.set_working error: {e}")

    def get_working(self, task_id: str) -> Dict[str, Any]:
        """Return all working-memory fields for this task."""
        if not redis_client or not task_id:
            return {}
        try:
            raw = redis_client.hgetall(f"mem:work:{task_id}")
            result: Dict[str, Any] = {}
            for k, v in raw.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            return result
        except Exception as e:
            print(f"AgentMemory.get_working error: {e}")
            return {}

    # ── Long-term memory / experience knowledge base ──────────────────────────

    def save_experience(
        self,
        chat_id: str,
        task_id: str,
        agent: str,
        request_pattern: str,
        outcome: str,
        payload: Dict,
    ) -> None:
        """Persist an experience (success / failure) to Supabase.

        The ``agent_experiences`` table must exist; if it doesn't, the error
        is caught and treated as non-fatal so existing deployments are unaffected.
        """
        if not supabase:
            return
        try:
            supabase.table("agent_experiences").insert({
                "chat_id": chat_id,
                "task_id": task_id,
                "agent": agent,
                "request_pattern": request_pattern,
                "outcome": outcome,   # "success" | "failure" | "partial"
                "payload": payload,
            }).execute()
        except Exception as e:
            print(f"AgentMemory.save_experience warning: {e}")

    def get_experiences(
        self,
        agent: str,
        request_pattern: str,
        limit: int = 3,
    ) -> List[Dict]:
        """Retrieve recent successful experiences that match the agent + pattern.

        Injected into agent prompts so that past knowledge informs new decisions.
        """
        if not supabase or not request_pattern:
            return []
        try:
            resp = (
                supabase.table("agent_experiences")
                .select("outcome,payload,request_pattern,created_at")
                .eq("agent", agent)
                .eq("outcome", "success")
                .ilike("request_pattern", f"%{request_pattern[:60]}%")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            print(f"AgentMemory.get_experiences error: {e}")
            return []

    # ── Metrics / performance tracking ────────────────────────────────────────

    def inc_stat(self, agent: str, field: str, amount: int = 1) -> None:
        """Increment a named counter for the given agent."""
        if not redis_client:
            return
        try:
            key = f"mem:stats:{agent}"
            redis_client.hincrby(key, field, amount)
            redis_client.expire(key, _STATS_TTL)
        except Exception as e:
            print(f"AgentMemory.inc_stat error: {e}")

    def get_stats(self, agent: str) -> Dict[str, int]:
        """Return all counters for the given agent."""
        if not redis_client:
            return {}
        try:
            raw = redis_client.hgetall(f"mem:stats:{agent}")
            return {k: int(v) for k, v in raw.items()}
        except Exception as e:
            print(f"AgentMemory.get_stats error: {e}")
            return {}

    # ── Event streaming (Redis pub/sub) ───────────────────────────────────────

    def publish_event(self, event_type: str, data: Dict) -> None:
        """Publish an agent lifecycle event to the Redis pub/sub channel.

        The channel name is ``agent:events``.  Any subscriber (e.g. a WebSocket
        gateway or monitoring tool) can receive these events in real time.
        """
        if not redis_client:
            return
        try:
            payload = json.dumps({"type": event_type, "ts": time.time(), **data})
            redis_client.publish(AGENT_EVENTS_CHANNEL, payload)
        except Exception as e:
            print(f"AgentMemory.publish_event error: {e}")


# Singleton — imported and shared by all agents in the system.
agent_memory = AgentMemory()
