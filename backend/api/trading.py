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
    user_id: str = Depends(get_current_user)
):
    try:
        config_update = await request.json()
    except:
        config_update = {}
        
    data = get_user_data(user_id)
    
    # Update fields if provided
    if "initial_balance" in config_update:
        new_val = float(config_update["initial_balance"])
        data["initialBalance"] = new_val
        data["balance"] = new_val # Reset current balance to match initial
        clear_user_trades(user_id) # Clear history as promised in UI
        
    if "balance_threshold" in config_update:
        data["balanceThreshold"] = float(config_update["balance_threshold"])
        
    if "daily_pnl_threshold" in config_update:
        data["dailyPnlThreshold"] = float(config_update["daily_pnl_threshold"])
        
    if "trading_mode" in config_update:
        data["tradingMode"] = config_update["trading_mode"]
        
    if "polymarket_address" in config_update:
        data["polymarketAddress"] = config_update["polymarket_address"]

    update_user_data(user_id, data)
    return {"status": "success", "config": data, "stats": {"balance": data.get("balance"), "initial_balance": data.get("initialBalance")}}

@router.post("/wallets/add")
async def add_wallet_endpoint(address: str, user_id: str = Depends(get_current_user)):
    result = add_wallet(user_id, address.lower())
    if result == "duplicate":
        raise HTTPException(status_code=400, detail="Address already tracked")
    return {"status": "success", "result": result}
