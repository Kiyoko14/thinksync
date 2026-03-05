from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from config import supabase
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str

@router.post("/login")
async def login(request: LoginRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    # Supabase magic link auth
    response = supabase.auth.sign_in_with_otp({"email": request.email})
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to send magic link")
    return {"message": "Magic link sent"}

@router.get("/session")
async def get_session():
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    # Get current session
    session = supabase.auth.get_session()
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session

async def get_current_user():
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    session = supabase.auth.get_session()
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = session.user
    return {"id": user.id, "email": user.email, "created_at": user.created_at}