from fastapi import APIRouter, Depends, Header, HTTPException
from supabase import Client
from config import supabase
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Optional
from uuid import uuid4
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginResponse(BaseModel):
    token: str
    user: dict

class SessionResponse(BaseModel):
    user_id: str
    email: str
    created_at: str


LOCAL_SESSIONS: Dict[str, dict] = {}


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    return authorization[len(prefix):].strip()

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Password-based login with local fallback session support."""
    if supabase:
        try:
            response = supabase.auth.sign_in_with_password(
                {"email": request.email, "password": request.password}
            )
            session = getattr(response, "session", None)
            user = getattr(response, "user", None)

            if not session or not user:
                raise HTTPException(status_code=401, detail="Invalid email or password")

            return LoginResponse(
                token=session.access_token,
                user={
                    "id": str(user.id),
                    "email": user.email or request.email,
                    "created_at": str(user.created_at),
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Supabase login error for {request.email}: {e}")

    token = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": f"local-{request.email}",
        "email": request.email,
        "created_at": now,
    }
    LOCAL_SESSIONS[token] = user
    return LoginResponse(token=token, user=user)

@router.get("/session", response_model=SessionResponse)
async def get_session(authorization: Optional[str] = Header(default=None)):
    """Get current user session"""
    token = _extract_token(authorization)
    if token and token in LOCAL_SESSIONS:
        local_user = LOCAL_SESSIONS[token]
        return SessionResponse(
            user_id=local_user["id"],
            email=local_user["email"],
            created_at=local_user["created_at"],
        )

    if not supabase:
        raise HTTPException(status_code=401, detail="Not authenticated")

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
    authorization: Optional[str] = Header(default=None),
    supabase_client: Optional[Client] = Depends(lambda: supabase),
) -> dict:
    """Dependency to get current authenticated user"""
    token = _extract_token(authorization)
    if token and token in LOCAL_SESSIONS:
        return LOCAL_SESSIONS[token]

    if not supabase_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
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
async def logout(authorization: Optional[str] = Header(default=None)):
    """Logout current user"""
    token = _extract_token(authorization)
    if token and token in LOCAL_SESSIONS:
        del LOCAL_SESSIONS[token]
        return {"message": "Logged out successfully"}

    if not supabase:
        return {"message": "Logged out successfully"}

    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        print(f"Logout error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Logout failed"
        )