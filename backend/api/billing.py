from fastapi import APIRouter, Depends, Request, HTTPException
import stripe
from backend.core.config import get_config
from backend.core.deps import get_current_user
from backend.db import get_user_data, update_user_data

router = APIRouter(prefix="/billing", tags=["Billing"])

STRIPE_SECRET_KEY = get_config("STRIPE_SECRET_KEY", "sk_test_mock")
STRIPE_WEBHOOK_SECRET = get_config("STRIPE_WEBHOOK_SECRET", "whsec_mock")
stripe.api_key = STRIPE_SECRET_KEY
FRONTEND_URL = get_config("FRONTEND_URL", "http://localhost:3000")

@router.post("/stripe/create-checkout-session")
async def create_stripe_checkout(user_id: str = Depends(get_current_user)):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'Pro Subscription'}, 'unit_amount': 2500}, 'quantity': 1}],
            mode='subscription',
            client_reference_id=user_id,
            success_url=f"{FRONTEND_URL}/?payment=success",
            cancel_url=f"{FRONTEND_URL}/?payment=cancel",
        )
        return {"id": session.id, "url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/debug/upgrade")
async def debug_upgrade(tier: str, user_id: str = Depends(get_current_user)):
    from backend.services.billing_service import billing_service
    if billing_service.upgrade_user(user_id, tier):
        return {"status": "success", "new_tier": tier}
    return {"status": "error"}
