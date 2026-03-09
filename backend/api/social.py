from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict
from backend.core.deps import get_current_user, require_subscription
from backend.services.social_service import social_service
from backend.services.billing_service import billing_service

router = APIRouter(prefix="/social", tags=["Social & Growth"])

@router.post("/follow/{target_id}")
async def follow_user(target_id: str, user_id: str = Depends(get_current_user)):
    """Follow another user to track their activity."""
    if social_service.follow_user(user_id, target_id):
        return {"status": "success", "message": f"Following {target_id}"}
    raise HTTPException(status_code=400, detail="Cannot follow user.")

@router.get("/heatmap")
async def get_heatmap(user_data: dict = Depends(require_subscription("pro"))):
    """Retrieve retail heatmap."""
    from backend.services.intelligence_service import intelligence_service
    return await intelligence_service.get_retail_heatmap()

@router.get("/feed")
async def get_feed(user_id: str = Depends(get_current_user)):
    """Institutional social feed."""
    return [
        {"user": "WhaleHunter_X", "action": "followed", "target": "Institutional_Prime", "time": "2m ago"},
        {"user": "Alpha_Node_1", "action": "replicated", "target": "0x32...1298", "time": "5m ago"},
        {"user": "Institutional_Prime", "action": "upgraded", "target": "Elite Tier", "time": "12m ago"},
    ]

@router.get("/leaderboard")
async def get_leaderboard():
    """Top performing nodes with real-time Polymarket profiles."""
    from backend.services.intelligence_service import intelligence_service
    return await intelligence_service.get_institutional_leaderboard()

@router.get("/available-categories")
async def get_categories():
    """List of available market categories for filtering."""
    return ["Politics", "Crypto", "Macro", "Science", "Sports"]

@router.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """Get a user's public profile."""
    profile = social_service.get_public_profile(user_id)
    if profile:
        return profile
    raise HTTPException(status_code=404, detail="Profile not found or private.")

@router.post("/referral/claim")
async def claim_referral(referrer_id: str, user_id: str = Depends(get_current_user)):
    """Claim a referral reward using a referrer's ID."""
    if billing_service.process_referral(referrer_id, user_id):
        return {"status": "success", "message": "Referral reward claimed! +1 Slot added."}
    raise HTTPException(status_code=400, detail="Referral failed.")
