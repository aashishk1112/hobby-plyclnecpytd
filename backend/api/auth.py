from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.core.config import get_config
from backend.core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

class MockLoginRequest(BaseModel):
    username: str
    password: Optional[str] = None

@router.post("/mock/login")
async def mock_login(request: MockLoginRequest):
    """Generate a mock session/token for local development."""
    if get_config("MOCK_AUTH", "False").lower() != "true":
        raise HTTPException(status_code=403, detail="Mock auth is disabled.")
    
    # In a mock environment, we just return a stable user string as 'token'
    # The get_current_user dependency will treat this as the userId
    return {
        "access_token": f"mock-token-{request.username}",
        "token_type": "bearer",
        "user_id": f"user-{request.username}"
    }

@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user)):
    from backend.db import get_user_data
    return get_user_data(user_id)
