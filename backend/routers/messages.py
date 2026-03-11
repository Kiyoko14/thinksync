from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from routers.auth import get_current_user
from routers.chats import get_chat, get_messages, send_message

router = APIRouter(prefix="/messages", tags=["messages"])


class CreateMessageRequest(BaseModel):
    chat_id: str
    content: str = Field(min_length=1, max_length=5000)


@router.get("/")
async def list_messages(
    chat_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    return await get_messages(chat_id, current_user)


@router.post("/")
async def create_message(
    request: CreateMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    await get_chat(request.chat_id, current_user)
    return await send_message(request.chat_id, request, current_user)
