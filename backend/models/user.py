from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal

class UserProfile(BaseModel):
    userId: str
    trackedWallets: List[str] = []
    disabledWallets: List[str] = []
    terminatedWallets: List[str] = []
    initialBalance: float = 100.0
    balance: float = 100.0
    balanceThreshold: float = 0.0
    dailyPnlThreshold: float = 1000.0
    tradingMode: str = "paper" # paper or live
    livePolymarketAddress: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    subscriptionStatus: str = "free" # free, pro, elite, cancelled
    subscriptionId: Optional[str] = None
    extraSlots: int = 0
    smartCopyRules: Dict[str, Any] = {}
    riskControls: Dict[str, Any] = {}
    allocationWeights: Dict[str, float] = {}

class Trade(BaseModel):
    userId: str
    id: str # txHash
    timestamp: str
    timestamp_raw: Optional[float] = None
    asset: str
    side: str # buy/sell
    amount: float
    price: float
    status: str # pending, completed, failed
    pnl: Optional[float] = None
    proxyWallet: Optional[str] = None

class SubscriptionTier(BaseModel):
    id: str
    name: str
    price: float
    features: List[str]
    maxSlots: int
