from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List, Optional, Dict
from backend.core.deps import get_current_user
from backend.services.trading_service import trading_service
from backend.db import get_user_data, update_user_data, add_wallet, terminate_wallet, clear_user_trades
from backend.models.user import UserProfile

router = APIRouter(prefix="/trading", tags=["Trading"])

@router.get("/config", response_model=Dict)
async def get_trading_config(user_id: str = Depends(get_current_user)):
    data = get_user_data(user_id)
    # Logic for syncing with active trackers
    return data

@router.post("/config/update")
async def update_trading_config(
    request: Request,
    user_id: str = Depends(get_current_user),
    config_update: Dict = {}
):
    data = get_user_data(user_id)
    # Update logic here...
    return {"status": "success", "config": data}

@router.post("/wallets/add")
async def add_wallet_endpoint(address: str, user_id: str = Depends(get_current_user)):
    result = add_wallet(user_id, address.lower())
    if result == "duplicate":
        raise HTTPException(status_code=400, detail="Address already tracked")
    return {"status": "success", "result": result}
