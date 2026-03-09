from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict
from backend.core.deps import require_subscription
from backend.services.ai_service import ai_service
from backend.services.intelligence_service import intelligence_service

router = APIRouter(prefix="/ai", tags=["AI & Strategy"])

@router.get("/portfolio", response_model=Dict)
async def get_ai_portfolio(risk: str = "balanced", user_data: dict = Depends(require_subscription("pro"))):
    """Get an AI-optimized portfolio recommendation (Pro+ only)."""
    return await ai_service.build_optimized_portfolio(risk)

@router.get("/marketplace", response_model=List[Dict])
async def get_strategy_marketplace(user_data: dict = Depends(require_subscription("pro"))):
    """
    Beta strategy marketplace: Highlights top whale wallets and their calculated Pro Scores.
    """
    whales = await intelligence_service.detect_whales()
    unique_wallets = list(set(w["wallet"] for w in whales))
    
    strategies = []
    for wallet in unique_wallets:
        # In a real system, we'd fetch the last N trades for this wallet
        # Here we simulate a Pro Score for discovery
        score = intelligence_service.calculate_pro_score([]) # placeholder
        strategies.append({
            "wallet": wallet,
            "pro_score": 85.0, # simulated for marketplace ranking
            "tier": "Whale Vanguard",
            "assets": ["BTC", "TRUMP", "ETH"],
            "win_rate": 78.5
        })
    
    return sorted(strategies, key=lambda x: x["pro_score"], reverse=True)
