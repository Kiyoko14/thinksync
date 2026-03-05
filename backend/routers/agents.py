from fastapi import APIRouter
from agents.orchestrator import process_message

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/process/{chat_id}")
async def process_chat_message(chat_id: str, message: str):
    await process_message(chat_id, message)
    return {"status": "processed"}