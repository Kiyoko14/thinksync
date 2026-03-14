from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from config import redis_client
from utils.cache import LRUCache


@dataclass
class ServerState:
    server_id: str
    directories: Set[str]
    files: Set[str]

    def to_dict(self) -> dict:
        return {
            "server_id": self.server_id,
            "directories": sorted(self.directories),
            "files": sorted(self.files),
        }


@dataclass
class ChatContext:
    chat_id: str
    server_id: str
    cwd: str = "/"

    def to_dict(self) -> dict:
        return asdict(self)


# Use LRU caches instead of unbounded dictionaries to prevent memory leaks
# Maximum 1000 servers, 5000 chats, 5000 command histories in memory
_LOCAL_SERVER_STATES = LRUCache[str, ServerState](max_size=1000)
_LOCAL_CHAT_CONTEXT = LRUCache[str, ChatContext](max_size=5000)
_LOCAL_COMMAND_HISTORY = LRUCache[str, List[dict]](max_size=5000)


def _normalize(path: str) -> str:
    if not path:
        return "/"
    normalized = os.path.normpath(path)
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def _join(cwd: str, value: str) -> str:
    if value.startswith("/"):
        return _normalize(value)
    return _normalize(os.path.join(cwd, value))


def _state_key(server_id: str) -> str:
    return f"state:server:{server_id}"


def _chat_key(chat_id: str) -> str:
    return f"state:chat:{chat_id}"


def _history_key(chat_id: str) -> str:
    return f"state:history:{chat_id}"


def _load_server_state(server_id: str) -> ServerState:
    # Try LRU cache first
    cached_state = _LOCAL_SERVER_STATES.get(server_id)
    if cached_state:
        return cached_state

    # Try Redis
    if redis_client:
        try:
            payload = redis_client.get(_state_key(server_id))
            if payload:
                decoded = json.loads(payload)
                state = ServerState(
                    server_id=server_id,
                    directories=set(decoded.get("directories", ["/"])),
                    files=set(decoded.get("files", [])),
                )
                _LOCAL_SERVER_STATES.set(server_id, state)
                return state
        except Exception as e:
            print(f"Error loading server state from Redis: {e}")

    # Create default state
    state = ServerState(server_id=server_id, directories={"/", "/home", "/home/ubuntu"}, files=set())
    _LOCAL_SERVER_STATES.set(server_id, state)
    return state


def _save_server_state(state: ServerState) -> None:
    _LOCAL_SERVER_STATES.set(state.server_id, state)
    if redis_client:
        try:
            redis_client.set(_state_key(state.server_id), json.dumps(state.to_dict()))
        except Exception as e:
            print(f"Error saving server state to Redis: {e}")


def get_chat_context(chat_id: str, server_id: str) -> ChatContext:
    # Try LRU cache first
    cached_context = _LOCAL_CHAT_CONTEXT.get(chat_id)
    if cached_context:
        return cached_context

    # Try Redis
    if redis_client:
        try:
            payload = redis_client.get(_chat_key(chat_id))
            if payload:
                decoded = json.loads(payload)
                context = ChatContext(
                    chat_id=chat_id,
                    server_id=decoded.get("server_id", server_id),
                    cwd=decoded.get("cwd", "/"),
                )
                _LOCAL_CHAT_CONTEXT.set(chat_id, context)
                return context
        except Exception as e:
            print(f"Error loading chat context from Redis: {e}")

    # Create default context
    context = ChatContext(chat_id=chat_id, server_id=server_id, cwd="/")
    _LOCAL_CHAT_CONTEXT.set(chat_id, context)
    return context


def _save_chat_context(context: ChatContext) -> None:
    _LOCAL_CHAT_CONTEXT.set(context.chat_id, context)
    if redis_client:
        try:
            redis_client.set(_chat_key(context.chat_id), json.dumps(context.to_dict()))
        except Exception as e:
            print(f"Error saving chat context to Redis: {e}")


def get_command_history(chat_id: str) -> List[dict]:
    # Try LRU cache first
    cached_history = _LOCAL_COMMAND_HISTORY.get(chat_id)
    if cached_history:
        return cached_history

    # Try Redis
    if redis_client:
        try:
            payload = redis_client.get(_history_key(chat_id))
            if payload:
                data = json.loads(payload)
                _LOCAL_COMMAND_HISTORY.set(chat_id, data)
                return data
        except Exception as e:
            print(f"Error loading command history from Redis: {e}")

    # Create empty history
    empty_history: List[dict] = []
    _LOCAL_COMMAND_HISTORY.set(chat_id, empty_history)
    return empty_history


def append_command_history(chat_id: str, item: dict) -> None:
    history = get_command_history(chat_id).copy()  # Copy to avoid mutation
    history.append(item)
    # Keep only last 200 items to prevent unbounded growth
    trimmed_history = history[-200:]
    _LOCAL_COMMAND_HISTORY.set(chat_id, trimmed_history)
    
    if redis_client:
        try:
            redis_client.set(_history_key(chat_id), json.dumps(trimmed_history))
        except Exception as e:
            print(f"Error saving command history to Redis: {e}")


def get_server_state(server_id: str) -> dict:
    return _load_server_state(server_id).to_dict()


def initialize_chat_workspace(chat_id: str, server_id: str, workspace_path: str) -> ChatContext:
    """Ensure chat workspace exists in state and set chat cwd to that folder."""
    state = _load_server_state(server_id)
    workspace = _normalize(workspace_path)
    state.directories.add(workspace)
    _save_server_state(state)

    context = ChatContext(chat_id=chat_id, server_id=server_id, cwd=workspace)
    _save_chat_context(context)
    return context


def clear_chat_state(chat_id: str) -> None:
    """Remove in-memory and Redis-backed state for a chat."""
    _LOCAL_CHAT_CONTEXT.delete(chat_id)
    _LOCAL_COMMAND_HISTORY.delete(chat_id)
    if redis_client:
        try:
            redis_client.delete(_chat_key(chat_id), _history_key(chat_id))
        except Exception as e:
            print(f"Error deleting chat state from Redis: {e}")


def clear_server_state(server_id: str, chat_ids: Optional[Iterable[str]] = None) -> None:
    """Remove in-memory and Redis-backed state for a server and optionally its chats."""
    _LOCAL_SERVER_STATES.delete(server_id)
    if redis_client:
        try:
            redis_client.delete(_state_key(server_id))
        except Exception as e:
            print(f"Error deleting server state from Redis: {e}")

    if chat_ids:
        for chat_id in chat_ids:
            clear_chat_state(chat_id)


def _can_create_dir(state: ServerState, path: str) -> bool:
    return path not in state.directories


def inspect_and_apply_command(server_id: str, chat_id: str, command: str) -> Dict[str, Any]:
    state = _load_server_state(server_id)
    context = get_chat_context(chat_id, server_id)

    raw = command.strip()
    if not raw:
        return {"status": "error", "message": "empty command", "executed": False}

    parts = raw.split()
    cmd = parts[0]

    if cmd == "cd" and len(parts) >= 2:
        target = _join(context.cwd, parts[1])
        if target not in state.directories:
            return {
                "status": "blocked",
                "message": f"Directory does not exist: {target}",
                "executed": False,
                "state": state.to_dict(),
            }
        context.cwd = target
        _save_chat_context(context)
        append_command_history(chat_id, {"command": raw, "status": "success", "cwd": context.cwd})
        return {
            "status": "success",
            "message": f"Changed directory to {context.cwd}",
            "executed": True,
            "state": state.to_dict(),
            "context": context.to_dict(),
        }

    if cmd == "mkdir" and len(parts) >= 2:
        created: List[str] = []
        skipped: List[str] = []
        for target in parts[1:]:
            if target.startswith("-"):
                continue
            directory = _join(context.cwd, target)
            if _can_create_dir(state, directory):
                state.directories.add(directory)
                created.append(directory)
            else:
                skipped.append(directory)

        _save_server_state(state)
        _save_chat_context(context)

        status = "success" if created else "skipped"
        message = "Created directories" if created else "All directories already existed"
        append_command_history(
            chat_id,
            {
                "command": raw,
                "status": status,
                "created": created,
                "skipped": skipped,
                "cwd": context.cwd,
            },
        )
        return {
            "status": status,
            "message": message,
            "executed": bool(created),
            "created": created,
            "skipped": skipped,
            "state": state.to_dict(),
            "context": context.to_dict(),
        }

    if cmd == "touch" and len(parts) >= 2:
        created_files: List[str] = []
        skipped_files: List[str] = []
        for target in parts[1:]:
            file_path = _join(context.cwd, target)
            if file_path in state.files:
                skipped_files.append(file_path)
            else:
                state.files.add(file_path)
                created_files.append(file_path)

        _save_server_state(state)
        append_command_history(
            chat_id,
            {
                "command": raw,
                "status": "success",
                "created_files": created_files,
                "skipped_files": skipped_files,
                "cwd": context.cwd,
            },
        )
        return {
            "status": "success",
            "message": "Files updated",
            "executed": bool(created_files),
            "created_files": created_files,
            "skipped_files": skipped_files,
            "state": state.to_dict(),
            "context": context.to_dict(),
        }

    append_command_history(chat_id, {"command": raw, "status": "success", "cwd": context.cwd})
    return {
        "status": "success",
        "message": "Command accepted",
        "executed": True,
        "state": state.to_dict(),
        "context": context.to_dict(),
    }
