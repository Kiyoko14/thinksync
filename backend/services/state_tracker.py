from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

from config import redis_client


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


_LOCAL_SERVER_STATES: Dict[str, ServerState] = {}
_LOCAL_CHAT_CONTEXT: Dict[str, ChatContext] = {}
_LOCAL_COMMAND_HISTORY: Dict[str, List[dict]] = {}


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
    if server_id in _LOCAL_SERVER_STATES:
        return _LOCAL_SERVER_STATES[server_id]

    if redis_client:
        payload = redis_client.get(_state_key(server_id))
        if payload:
            decoded = json.loads(payload)
            state = ServerState(
                server_id=server_id,
                directories=set(decoded.get("directories", ["/"])),
                files=set(decoded.get("files", [])),
            )
            _LOCAL_SERVER_STATES[server_id] = state
            return state

    state = ServerState(server_id=server_id, directories={"/", "/home", "/home/ubuntu"}, files=set())
    _LOCAL_SERVER_STATES[server_id] = state
    return state


def _save_server_state(state: ServerState) -> None:
    _LOCAL_SERVER_STATES[state.server_id] = state
    if redis_client:
        redis_client.set(_state_key(state.server_id), json.dumps(state.to_dict()))


def get_chat_context(chat_id: str, server_id: str) -> ChatContext:
    if chat_id in _LOCAL_CHAT_CONTEXT:
        return _LOCAL_CHAT_CONTEXT[chat_id]

    if redis_client:
        payload = redis_client.get(_chat_key(chat_id))
        if payload:
            decoded = json.loads(payload)
            context = ChatContext(
                chat_id=chat_id,
                server_id=decoded.get("server_id", server_id),
                cwd=decoded.get("cwd", "/"),
            )
            _LOCAL_CHAT_CONTEXT[chat_id] = context
            return context

    context = ChatContext(chat_id=chat_id, server_id=server_id, cwd="/")
    _LOCAL_CHAT_CONTEXT[chat_id] = context
    return context


def _save_chat_context(context: ChatContext) -> None:
    _LOCAL_CHAT_CONTEXT[context.chat_id] = context
    if redis_client:
        redis_client.set(_chat_key(context.chat_id), json.dumps(context.to_dict()))


def get_command_history(chat_id: str) -> List[dict]:
    if chat_id in _LOCAL_COMMAND_HISTORY:
        return _LOCAL_COMMAND_HISTORY[chat_id]

    if redis_client:
        payload = redis_client.get(_history_key(chat_id))
        if payload:
            data = json.loads(payload)
            _LOCAL_COMMAND_HISTORY[chat_id] = data
            return data

    _LOCAL_COMMAND_HISTORY[chat_id] = []
    return _LOCAL_COMMAND_HISTORY[chat_id]


def append_command_history(chat_id: str, item: dict) -> None:
    history = get_command_history(chat_id)
    history.append(item)
    _LOCAL_COMMAND_HISTORY[chat_id] = history[-200:]
    if redis_client:
        redis_client.set(_history_key(chat_id), json.dumps(_LOCAL_COMMAND_HISTORY[chat_id]))


def get_server_state(server_id: str) -> dict:
    return _load_server_state(server_id).to_dict()


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
