from fastapi import APIRouter, Depends
from typing import List, Dict
from backend.services.intelligence_service import intelligence_service

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

@router.get("/whales", response_model=List[Dict])
async def get_whales():
    """Real-time whale radar."""
    return await intelligence_service.detect_whales()

from backend.core.deps import require_subscription

@router.get("/signals", response_model=List[Dict])
async def get_signals(user_data: dict = Depends(require_subscription("pro"))):
    """Predictive alpha signals (Pro+ only)."""
    return await intelligence_service.generate_predictive_signals()

@router.get("/heatmap", response_model=List[Dict])
async def get_heatmap(user_data: dict = Depends(require_subscription("pro"))):
    """Retail sentiment heatmap (Pro+ only)."""
    return await intelligence_service.get_retail_heatmap()

@router.get("/available-categories")
async def get_categories():
    """List of available market categories."""
    return ["Politics", "Crypto", "Macro", "Science", "Sports"]
