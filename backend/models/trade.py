from pydantic import BaseModel
from typing import Optional

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
