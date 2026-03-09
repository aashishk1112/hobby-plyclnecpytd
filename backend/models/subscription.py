from pydantic import BaseModel
from typing import List

class SubscriptionTier(BaseModel):
    id: str # free, pro, elite
    name: str
    price: float
    features: List[str]
    maxSlots: int
