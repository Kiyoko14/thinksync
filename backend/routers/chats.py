from datetime import datetime, timezone
import asyncio
import re
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import supabase, openai_client, call_openai, async_db
from models import Chat, Message
from routers.auth import get_current_user
from routers.servers import LOCAL_SERVERS
from services.state_tracker import (
    append_command_history,
    clear_chat_state,
    get_chat_context,
    get_command_history,
    initialize_chat_workspace,
    inspect_and_apply_command,
)

router = APIRouter(prefix="/chats", tags=["chats"])

LOCAL_CHATS: Dict[str, dict] = {}
LOCAL_MESSAGES: Dict[str, List[dict]] = {}
CHAT_CREATE_LOCK = asyncio.Lock()


class CreateChatRequest(BaseModel):
    server_id: str
    name: str = Field(min_length=2, max_length=120)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class ChatContextResponse(BaseModel):
    chat_id: str
    server_id: str
    cwd: str
    command_history: List[dict]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_chat_name(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def _workspace_slug(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", _canonical_chat_name(name).replace(" ", "_"))
    return cleaned.strip("_") or "chat"


async def _chat_name_exists(user_id: str, name: str) -> bool:
    candidate = _canonical_chat_name(name)
    if supabase:
        response = await async_db(
            lambda: supabase.table("chats")
            .select("name")
            .eq("user_id", user_id)
            .execute()
        )
        rows = response.data or []
        return any(_canonical_chat_name(str(row.get("name", ""))) == candidate for row in rows)

    for chat in LOCAL_CHATS.values():
        if chat["user_id"] == user_id:
            if _canonical_chat_name(chat["name"]) == candidate:
                return True
    return False


async def _safe_delete_by_chat_id(table: str, chat_id: str) -> None:
    if not supabase:
        return
    try:
        await async_db(lambda: supabase.table(table).delete().eq("chat_id", chat_id).execute())
    except Exception as e:
        print(f"chats.delete: cleanup warning for {table}: {e}")


async def _validate_server_access(server_id: str, current_user: dict) -> None:
    if supabase:
        response = await async_db(
            lambda: supabase.table("servers")
            .select("id")
            .eq("id", server_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Server not found")
        return

    local_server = LOCAL_SERVERS.get(server_id)
    if not local_server or local_server["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Server not found")


@router.get("/", response_model=List[Chat])
async def get_chats(
    server_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if supabase:
        def _query():
            q = supabase.table("chats").select("*").eq("user_id", current_user["id"])
            if server_id:
                q = q.eq("server_id", server_id)
            return q.order("created_at", desc=True).execute()
        response = await async_db(_query)
        return response.data

    result = [
        chat for chat in LOCAL_CHATS.values() if chat["user_id"] == current_user["id"]
    ]
    if server_id:
        result = [chat for chat in result if chat["server_id"] == server_id]
    return sorted(result, key=lambda item: item["created_at"], reverse=True)


@router.get("/{chat_id}", response_model=Chat)
async def get_chat(chat_id: str, current_user: dict = Depends(get_current_user)):
    if supabase:
        response = await async_db(
            lambda: supabase.table("chats")
            .select("*")
            .eq("id", chat_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Chat not found")
        return response.data[0]

    chat = LOCAL_CHATS.get(chat_id)
    if not chat or chat["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("/", response_model=Chat)
async def create_chat(request: CreateChatRequest, current_user: dict = Depends(get_current_user)):
    await _validate_server_access(request.server_id, current_user)

    normalized_name = _canonical_chat_name(request.name)
    if len(normalized_name) < 2:
        raise HTTPException(status_code=400, detail="Chat name must contain at least 2 non-space characters")

    async with CHAT_CREATE_LOCK:
        if await _chat_name_exists(current_user["id"], normalized_name):
            raise HTTPException(status_code=409, detail="A chat with this name already exists")

        workspace_path = f"/workspace/server_{request.server_id}/chat_{_workspace_slug(normalized_name)}"
        chat_data = {
            "id": str(uuid4()),
            "server_id": request.server_id,
            "user_id": current_user["id"],
            "name": " ".join(request.name.strip().split()),
            "workspace_path": workspace_path,
            "created_at": _now(),
        }

        if supabase:
            payload = {k: v for k, v in chat_data.items() if k != "id"}
            try:
                response = await async_db(
                    lambda: supabase.table("chats").insert(payload).execute()
                )
            except Exception as e:
                message = str(e).lower()
                if "duplicate" in message or "unique" in message:
                    raise HTTPException(status_code=409, detail="A chat with this name already exists")
                raise

            created_chat = response.data[0]
            initialize_chat_workspace(
                created_chat["id"],
                created_chat["server_id"],
                created_chat.get("workspace_path") or workspace_path,
            )
            return created_chat

        LOCAL_CHATS[chat_data["id"]] = chat_data
        LOCAL_MESSAGES[chat_data["id"]] = []
        initialize_chat_workspace(chat_data["id"], chat_data["server_id"], chat_data["workspace_path"])
        return chat_data


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, current_user: dict = Depends(get_current_user)):
    chat = await get_chat(chat_id, current_user)

    if supabase:
        # Best-effort cleanup for related rows even when some optional tables
        # are absent in a deployment schema.
        for table in ["messages", "tasks", "actions", "workspaces", "agent_logs"]:
            await _safe_delete_by_chat_id(table, chat_id)

        await async_db(
            lambda: supabase.table("chats")
            .delete()
            .eq("id", chat_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
    else:
        LOCAL_CHATS.pop(chat_id, None)

    LOCAL_MESSAGES.pop(chat_id, None)
    LOCAL_CHATS.pop(chat_id, None)

    clear_chat_state(chat_id)

    return {
        "message": "Chat deleted",
        "chat_id": chat_id,
        "server_id": chat["server_id"],
    }


@router.get("/{chat_id}/messages", response_model=List[Message])
async def get_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    await get_chat(chat_id, current_user)

    if supabase:
        response = await async_db(
            lambda: supabase.table("messages")
            .select("*")
            .eq("chat_id", chat_id)
            .order("created_at")
            .execute()
        )
        return response.data

    return LOCAL_MESSAGES.get(chat_id, [])


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: str,
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    chat = await get_chat(chat_id, current_user)
    initialize_chat_workspace(chat_id, chat["server_id"], chat.get("workspace_path") or "/")

    user_message = {
        "id": str(uuid4()),
        "chat_id": chat_id,
        "role": "user",
        "content": request.content,
        "created_at": _now(),
    }

    command = request.content.strip()
    inspection = inspect_and_apply_command(chat["server_id"], chat_id, command)

    inspection_summary = None
    if inspection.get("status") == "blocked":
        inspection_summary = f"[BLOCKED] {inspection.get('message', 'Command blocked')}"
    elif inspection.get("status") == "skipped":
        inspection_summary = "[INFO] This command was already applied; no duplicate changes made."
    elif inspection.get("status") == "success":
        created = inspection.get("created", [])
        if created:
            inspection_summary = f"[SUCCESS] Directories created: {', '.join(created)}"
        else:
            inspection_summary = inspection.get("message")

    history = get_command_history(chat_id)
    history_text = "\n".join(
        f"- {h['input']}" for h in history[-8:]
    ) if history else "None"

    context = get_chat_context(chat_id, chat.get("server_id", ""))
    cwd = context.cwd if context else "/"

    if openai_client:
        try:
            system_prompt = (
                "You are an expert AI DevOps assistant embedded in a server management platform. "
                "You help users manage Linux servers, debug issues, deploy code, write shell scripts, "
                "and explain infrastructure concepts. Be concise, accurate, and helpful. "
                "When a command is provided, explain what it does and any important caveats. "
                "When answering questions, be direct and technical. "
                f"Current working directory: {cwd}\n"
                f"Recent command history:\n{history_text}"
            )
            messages_for_ai = [{"role": "system", "content": system_prompt}]

            for hist in history[-5:]:
                messages_for_ai.append({"role": "user", "content": hist["input"]})
                if hist.get("result", {}).get("message"):
                    messages_for_ai.append({"role": "assistant", "content": hist["result"]["message"]})

            messages_for_ai.append({"role": "user", "content": command})
            if inspection_summary:
                messages_for_ai.append({
                    "role": "system",
                    "content": f"Local inspection result: {inspection_summary}"
                })

            ai_response = await call_openai(
                model="gpt-4o",
                messages=messages_for_ai,
                max_tokens=600,
                temperature=0.4,
            )
            assistant_text = (ai_response.choices[0].message.content if ai_response else None) or "Javob olinmadi."
        except Exception as e:
            print(f"OpenAI error: {e}")
            assistant_text = inspection_summary or "Xabar qabul qilindi."
    else:
        assistant_text = inspection_summary or "Xabar qabul qilindi. (OpenAI ulanmagan)"

    assistant_message = {
        "id": str(uuid4()),
        "chat_id": chat_id,
        "role": "assistant",
        "content": assistant_text,
        "created_at": _now(),
    }

    append_command_history(
        chat_id,
        {
            "input": request.content,
            "result": inspection,
            "created_at": _now(),
        },
    )

    if supabase:
        await async_db(
            lambda: supabase.table("messages").insert([user_message, assistant_message]).execute()
        )
    else:
        LOCAL_MESSAGES.setdefault(chat_id, []).extend([user_message, assistant_message])

    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "inspection": inspection,
    }


@router.get("/{chat_id}/context", response_model=ChatContextResponse)
async def get_chat_context_state(chat_id: str, current_user: dict = Depends(get_current_user)):
    chat = await get_chat(chat_id, current_user)
    workspace_path = chat.get("workspace_path") or "/"
    context = initialize_chat_workspace(chat_id, chat["server_id"], workspace_path)
    return ChatContextResponse(
        chat_id=chat_id,
        server_id=chat["server_id"],
        cwd=context.cwd,
        command_history=get_command_history(chat_id),
    )
