import logging
from typing import Dict, Optional
from backend.db import get_user_data, update_user_data
from backend.models.subscription import SubscriptionTier

logger = logging.getLogger(__name__)

SUBSCRIPTION_TIERS = {
    "free": SubscriptionTier(id="free", name="Free", price=0.0, features=["2 Tracked Wallets", "Standard Signals"], maxSlots=2),
    "pro": SubscriptionTier(id="pro", name="Pro", price=25.0, features=["10 Tracked Wallets", "Whale Radar", "Predictive Alpha"], maxSlots=10),
    "elite": SubscriptionTier(id="elite", name="Elite", price=99.0, features=["Unlimited Wallets", "Priority Alpha", "AI Portfolio Builder"], maxSlots=100)
}

class BillingService:
    @staticmethod
    def get_tier(tier_id: str) -> SubscriptionTier:
        return SUBSCRIPTION_TIERS.get(tier_id, SUBSCRIPTION_TIERS["free"])

    def upgrade_user(self, user_id: str, new_tier: str):
        if new_tier not in SUBSCRIPTION_TIERS:
            return False
        
        user_data = get_user_data(user_id)
        if user_data:
            user_data["subscriptionStatus"] = new_tier
            update_user_data(user_id, user_data)
            logger.info(f"User {user_id} upgraded to {new_tier}")
            return True
        return False

    def add_extra_slot(self, user_id: str):
        user_data = get_user_data(user_id)
        if user_data:
            user_data["extraSlots"] = user_data.get("extraSlots", 0) + 1
            update_user_data(user_id, user_data)
            logger.info(f"User {user_id} purchased an extra slot")
            return True
        return False

    def check_access(self, user_id: str, feature: str) -> bool:
        user_data = get_user_data(user_id)
        tier = self.get_tier(user_data.get("subscriptionStatus", "free"))
        
        # Simple feature matching for now
        if tier.id == "elite": return True
        if tier.id == "pro" and feature in ["Whale Radar", "Predictive Alpha"]: return True
        if tier.id == "free" and feature == "Standard Signals": return True
        return False

    def process_referral(self, referrer_id: str, referee_id: str):
        """Reward both the referrer and the referee with an extra slot."""
        # Reward Referrer
        referrer_data = get_user_data(referrer_id)
        if referrer_data:
            referrer_data["extraSlots"] = referrer_data.get("extraSlots", 0) + 1
            referrer_data["referralCount"] = referrer_data.get("referralCount", 0) + 1
            update_user_data(referrer_id, referrer_data)
            
        # Reward Referee
        referee_data = get_user_data(referee_id)
        if referee_data:
            referee_data["extraSlots"] = referee_data.get("extraSlots", 0) + 1
            referee_data["referredBy"] = referrer_id
            update_user_data(referee_id, referee_data)
            
        logger.info(f"Referral processed: {referrer_id} referred {referee_id}. Both received +1 slot.")
        return True

billing_service = BillingService()
