from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from config import supabase
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr

class SessionResponse(BaseModel):
    user_id: str
    email: str
    created_at: str

@router.post("/login")
async def login(request: LoginRequest):
    """Send magic link login to user email"""
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Database not configured. Please contact support."
        )
    
    try:
        response = supabase.auth.sign_in_with_otp({"email": request.email})
        if not response or response.status_code != 200:
            raise HTTPException(
                status_code=400, 
                detail="Failed to send magic link. Please try again."
            )
        return {
            "message": "Magic link sent successfully",
            "email": request.email,
            "info": "Check your email for the login link"
        }
    except Exception as e:
        # Log the error but don't expose details
        print(f"Login error for {request.email}: {e}")
        raise HTTPException(
            status_code=400, 
            detail="Failed to process login request"
        )

@router.get("/session", response_model=SessionResponse)
async def get_session():
    """Get current user session"""
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Database not configured"
        )
    
    try:
        session = supabase.auth.get_session()
        if not session or not session.user:
            raise HTTPException(
                status_code=401, 
                detail="Not authenticated. Please login first."
            )
        
        user = session.user
        return SessionResponse(
            user_id=str(user.id),
            email=user.email or "",
            created_at=str(user.created_at)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Session error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve session"
        )

async def get_current_user(
    supabase_client: Optional[Client] = Depends(lambda: supabase)
) -> dict:
    """Dependency to get current authenticated user"""
    if not supabase_client:
        raise HTTPException(
            status_code=500, 
            detail="Database not configured"
        )
    
    try:
        session = supabase_client.auth.get_session()
        if not session or not session.user:
            raise HTTPException(
                status_code=401, 
                detail="Not authenticated"
            )
        
        user = session.user
        return {
            "id": str(user.id),
            "email": user.email or "",
            "created_at": str(user.created_at)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(
            status_code=401, 
            detail="Authentication failed"
        )

@router.post("/logout")
async def logout():
    """Logout current user"""
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Database not configured"
        )
    
    try:
        # Client-side logout is handled in frontend
        # This endpoint can be used for server-side cleanup if needed
        return {"message": "Logged out successfully"}
    except Exception as e:
        print(f"Logout error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Logout failed"
        )