from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import List, Optional
import os
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mangum import Mangum
import jwt as pyjwt # renamed to avoid conflict with jose.jwt
from jose import jwt
import json
import time
from db import get_user_data, update_user_data, add_wallet as db_add_wallet, terminate_wallet, clear_user_trades, update_user_balance

from tracker import PolymarketTracker
import stripe

from config_loader import get_config

# In-memory storage for trades
trade_history = []
category_filters = []

# Global# Trackers - initialized on startup
tracker = PolymarketTracker("local-test-user", [], trade_history, {"balance": 100.0, "initial_balance": 100.0}, category_filters)

# Stripe client initialization
STRIPE_SECRET_KEY = get_config("STRIPE_SECRET_KEY", "sk_test_mock")
STRIPE_WEBHOOK_SECRET = get_config("STRIPE_WEBHOOK_SECRET", "whsec_mock")
stripe.api_key = STRIPE_SECRET_KEY
FRONTEND_URL = get_config("FRONTEND_URL", "https://d3ukbv7x6b8vr.cloudfront.net")

REGION = get_config("AWS_REGION", "ap-south-1")
USER_POOL_ID = get_config("USER_POOL_ID")
LOCALSTACK_ENDPOINT = get_config("LOCALSTACK_ENDPOINT")

if USER_POOL_ID and not USER_POOL_ID.endswith("_dummy"):
    # Real Cognito User Pool - use official discovery URL
    # Extract region from USER_POOL_ID if possible (e.g. us-east-1_abc)
    pool_region = USER_POOL_ID.split("_")[0] if "_" in USER_POOL_ID else REGION
    JWKS_URL = f"https://cognito-idp.{pool_region}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
elif LOCALSTACK_ENDPOINT and USER_POOL_ID:
    # Use LocalStack for Cognito discovery
    JWKS_URL = f"{LOCALSTACK_ENDPOINT}/{USER_POOL_ID}/.well-known/jwks.json"
else:
    JWKS_URL = None
_jwks_cache = None

async def get_jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    if not JWKS_URL:
        return None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(JWKS_URL)
            if response.status_code == 200:
                _jwks_cache = response.json()
                return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Pclonecopy API")
# handler = Mangum(app) # Moved to bottom

async def get_current_user(request):
    """Extraction logic for user context from JWT."""
    auth_header = request.headers.get("Authorization")
    
    # Check if mock auth is enabled (default to False for production)
    is_mock = get_config("MOCK_AUTH", "False").lower() == "true"
    
    if not auth_header or not auth_header.startswith("Bearer "):
        if is_mock:
            return "local-test-user"
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.split(" ")[1]
    
    # Real verification
    if USER_POOL_ID and not is_mock:
        try:
            jwks = await get_jwks()
            if not jwks:
                logger.error("JWKS not found - check USER_POOL_ID and REGION")
                raise HTTPException(status_code=500, detail="Identity provider configuration error")
            
            # Verify the JWT using jose
            payload = jwt.decode(
                token, 
                jwks, 
                algorithms=['RS256'],
                options={
                    "verify_at_hash": False,
                    "verify_aud": False # In production, verify against App Client ID
                }
            )
            return {
                "sub": payload.get("sub"),
                "name": payload.get("name"),
                "picture": payload.get("picture"),
                "email": payload.get("email")
            }
        except Exception as e:
            logger.error(f"JWT Verification failed: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    else:
        # Fallback to unverified decode for Local/Mock or if config is missing
        try:
            payload = jwt.get_unverified_claims(token)
            user_id = payload.get("sub") or payload.get("username")
            if not user_id and is_mock:
                return {"sub": f"user-{token}", "name": f"Mock User {token}", "picture": None, "email": "mock@example.com"}
            return {
                "sub": user_id,
                "name": payload.get("name"),
                "picture": payload.get("picture"),
                "email": payload.get("email")
            }
        except Exception:
            if is_mock:
                return {"sub": f"user-{token}", "name": f"Mock User {token}", "picture": None, "email": "mock@example.com"}
            raise HTTPException(status_code=401, detail="Invalid token")

# CORS handling moved to standard CORSMiddleware below

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Exclude public routes and heartbeat from auth
    if request.method == "OPTIONS" or request.url.path in ["/", "/docs", "/openapi.json", "/health", "/healthz", "/stripe/webhook"]:
        return await call_next(request)
    
    try:
        user_info = await get_current_user(request)
        if isinstance(user_info, dict):
            request.state.user_id = user_info["sub"]
            request.state.user_name = user_info.get("name")
            request.state.user_picture = user_info.get("picture")
            request.state.user_email = user_info.get("email")
        else:
            request.state.user_id = user_info
            request.state.user_name = None
            request.state.user_picture = None
            request.state.user_email = None
    except HTTPException as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": f"Internal server error: {str(e)}"})
        
    return await call_next(request)

# Standard CORS Middleware - Added LAST to ensure it wraps all other middlewares/responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://d3ukbv7x6b8vr.cloudfront.net",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORS Middleware removed in favor of manual_cors_middleware above

# In-memory storage for trades (fetched by UI)
# trade_history = [] # Moved above tracker initialization

@app.get("/")
async def root():
    return {"status": "online", "message": "Polymarket Copy Trade Bot Backend (Simplified)"}

@app.get("/health")
@app.get("/healthz")
async def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/config")
async def get_config(request: Request):
    user_id = request.state.user_id
    data = get_user_data(user_id)
    if data is None:
        data = {"userId": user_id, "trackedWallets": [], "disabledWallets": [], "initialBalance": 100.0, "balanceThreshold": 0.0, "filters": []}

    # Update profile info if present in token but not in DB
    updated = False
    if request.state.user_name and data.get("name") != request.state.user_name:
        data["name"] = request.state.user_name
        updated = True
    if request.state.user_picture and data.get("picture") != request.state.user_picture:
        data["picture"] = request.state.user_picture
        updated = True
    if request.state.user_email and data.get("email") != request.state.user_email:
        data["email"] = request.state.user_email
        updated = True
    if updated:
        update_user_data(user_id, data)

    # Sync tracker state for this specific user call
    tracker.tracked_addresses = data.get("trackedWallets", [])
    tracker.disabled_addresses = set(data.get("disabledWallets", []))
    tracker.balance_threshold = float(data.get("balanceThreshold", 0.0))
    
    # Sync guard: Only sync stats from DB if we haven't recently reset them in memory.
    # This prevents eventual consistency issues from overwriting a fresh 100.0 reset with stale DB data.
    skip_db_sync = (time.time() - getattr(tracker, 'last_reset_at', 0)) < 10
    default_initial = 100.0
    
    if not skip_db_sync:
        if tracker.stats.get("initial_balance", default_initial) == default_initial:
            tracker.stats["initial_balance"] = float(data.get("initialBalance", default_initial))
        
        # Sync current balance from DB (survives cold starts)
        tracker.stats["balance"] = float(data.get("balance", tracker.stats.get("balance", default_initial)))

    return {
        "tracked_wallets": tracker.tracked_addresses,
        "disabled_wallets": list(tracker.disabled_addresses),
        "terminated_wallets": data.get("terminatedWallets", []),
        "paper_trading": get_config("PAPER_TRADING", "True").lower() == "true",
        "stats": {
            "balance": float(tracker.stats.get("balance", default_initial)),
            "initial_balance": float(tracker.stats.get("initial_balance", default_initial)),
        },
        "filters": data.get("filters", []),
        "balance_history": tracker.balance_history,
        "subscription_status": data.get("subscriptionStatus", "free"),
        "subscription_id": data.get("subscriptionId"),
        "extra_slots": data.get("extraSlots", 0),
        "balance_threshold": float(data.get("balanceThreshold", 0.0)),
        "user_profile": {
            "name": data.get("name"),
            "picture": data.get("picture"),
            "email": data.get("email")
        }
    }

@app.post("/config/update")
async def update_config(
    request: Request, 
    initial_balance: Optional[float] = None, 
    balance_threshold: Optional[float] = None,
    daily_pnl_threshold: Optional[float] = None,
    trading_mode: Optional[str] = None,
    polymarket_address: Optional[str] = None
):
    user_id = request.state.user_id
    data = get_user_data(user_id)
    if data is None:
        data = {"userId": user_id, "trackedWallets": [], "disabledWallets": [], "initialBalance": 100.0, "balanceThreshold": 0.0, "filters": []}

    updated = False
    if balance_threshold is not None:
        data["balanceThreshold"] = float(balance_threshold)
        tracker.balance_threshold = float(balance_threshold)
        updated = True
        logger.info(f"Updated balance threshold for {user_id} to: {balance_threshold}")

    if daily_pnl_threshold is not None:
        data["dailyPnlThreshold"] = float(daily_pnl_threshold)
        updated = True
        logger.info(f"Updated daily P&L threshold for {user_id} to: {daily_pnl_threshold}")

    if trading_mode is not None:
        data["tradingMode"] = trading_mode # 'paper' or 'live'
        updated = True
        logger.info(f"Updated trading mode for {user_id} to: {trading_mode}")

    if polymarket_address is not None:
        data["livePolymarketAddress"] = polymarket_address
        updated = True
        logger.info(f"Updated live polymarket address for {user_id} to: {polymarket_address}")

    if initial_balance is not None:
        initial_balance = float(initial_balance)
        data["initialBalance"] = initial_balance
        tracker.stats["initial_balance"] = initial_balance

        # Reset current balance and trade history when capital is re-applied
        tracker.stats["balance"] = initial_balance
        data["balance"] = initial_balance  # Persist reset balance to DB
        tracker.last_reset_at = time.time()  # Mark reset time for sync guard
        trade_history.clear()
        clear_user_trades(user_id) # Hard delete from DynamoDB
        await tracker.clear_cache()
        updated = True
        logger.info(f"Re-initialized capital for {user_id} to: {initial_balance}. History cleared from memory and DB.")

    if updated:
        update_user_data(user_id, data)

    # Return explicit numbers so frontend always gets correct types
    return {
        "stats": {
            "balance": float(tracker.stats.get("balance", 100.0)),
            "initial_balance": float(tracker.stats.get("initial_balance", 100.0)),
        },
        "config": data
    }

@app.get("/leaderboard")
async def get_leaderboard(request: Request):
    """Fetch top traders from Polymarket based on user's daily P&L threshold."""
    user_id = request.state.user_id
    user_data = get_user_data(user_id)
    threshold = user_data.get("dailyPnlThreshold", 1000.0)
    
    try:
        async with httpx.AsyncClient() as client:
            # Polymarket Data API for daily PnL
            url = "https://data-api.polymarket.com/v1/leaderboard?timePeriod=DAY&orderBy=PNL&limit=50"
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                all_traders = response.json()
                # Filter by user's daily P&L threshold and limit to top 10
                filtered = [
                    t for t in all_traders 
                    if float(t.get('pnl', 0)) >= threshold
                ][:10]
                return filtered
            else:
                logger.error(f"Failed to fetch Polymarket leaderboard: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return []

@app.post("/wallets/toggle")
async def toggle_wallet(request: Request, address: str):
    user_id = request.state.user_id
    address = address.lower()
    data = get_user_data(user_id)
    
    disabled = set(data.get("disabledWallets", []))
    if address in disabled:
        disabled.remove(address)
        status = "enabled"
    else:
        disabled.add(address)
        status = "disabled"
    
    data["disabledWallets"] = list(disabled)
    update_user_data(user_id, data)
    
    # Sync global tracker (if serving this user)
    tracker.disabled_addresses = disabled
    
    logger.info(f"Wallet {address} is now {status} for {user_id}")
    return {"address": address, "status": status, "disabled_wallets": list(disabled)}

@app.post("/trades/clear")
async def clear_trades():
    trade_history.clear()
    tracker.stats["balance"] = tracker.stats["initial_balance"]
    await tracker.clear_cache()
    logger.info("Cleared all trade history, reset balance, and cleared tracker cache")
    return {"message": "Trade history cleared and tracker reset"}

@app.post("/filters/add")
async def add_filter(category: str):
    category = category.lower()
    if category not in category_filters:
        category_filters.append(category)
        logger.info(f"Added category filter: {category}")
    return {"filters": category_filters}

@app.post("/filters/remove")
async def remove_filter(category: str):
    category = category.lower()
    if category in category_filters:
        category_filters.remove(category)
        logger.info(f"Removed category filter: {category}")
    return {"filters": category_filters}

@app.get("/available-categories")
async def get_available_categories():
    """Fetch real tags from Polymarket to provide as suggestions."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://gamma-api.polymarket.com/tags")
            if response.status_code == 200:
                tags = response.json()
                # Sort by popularity or just return a subset of common ones
                # For now, let's take a mix of top ones and common themes
                common_themes = ["crypto", "bitcoin", "ethereum", "solana", "politics", "elon", "trump", "sports", "nba", "nfl", "soccer"]
                
                # Extract labels and filter for ones that might be interesting
                all_tags = [t.get("label") for t in tags if t.get("label")]
                
                # Curate a list: priority for common themes, then alphabetical
                curated = [theme.title() for theme in common_themes if any(theme in t.lower() for t in all_tags)]
                
                # Add some real ones from the API too (limit to 30)
                additional = [t.get("label") for t in tags if t.get("label") and t.get("label").lower() not in common_themes][:20]
                
                return {"categories": sorted(list(set(curated + additional)))}
            else:
                # Fallback to hardcoded list if API fails
                return {"categories": ["Bitcoin", "Ethereum", "Crypto", "Politics", "Sports", "Donald Trump", "Elon Musk"]}
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}")
        return {"categories": ["Bitcoin", "Ethereum", "Crypto", "Politics", "Sports"]}

@app.post("/wallets/add")
async def add_wallet(request: Request, address: str):
    user_id = request.state.user_id
    address = address.lower()
    
    data = get_user_data(user_id)
    if not data:
        data = {"userId": user_id, "trackedWallets": [], "subscriptionStatus": "free", "extraSlots": 0}
        
    subscription_status = data.get("subscriptionStatus", "free")
    current_wallets = data.get("trackedWallets", [])
    extra_slots = data.get("extraSlots", 0)
    
    # Enforce limits: Free tier is 2 + extra_slots
    if subscription_status == "free" and len(current_wallets) >= (2 + extra_slots):
        # We only block IF it's a NEW wallet. Reactivation should be allowed even if at limit.
        if address not in current_wallets:
            raise HTTPException(status_code=402, detail="Address limit reached. Please purchase an additional slot for $5.")
    
    result = db_add_wallet(user_id, address)
    if result == "duplicate":
        raise HTTPException(status_code=400, detail="Address is already being tracked.")
    
    if result == "reactivated":
        # Remove from tracker's disabled list if present
        if address in tracker.disabled_addresses:
            tracker.disabled_addresses.remove(address)
        logger.info(f"User {user_id} reactivated wallet: {address}")
        return {"message": f"Reactivated wallet {address}", "wallets": tracker.tracked_addresses, "status": "reactivated"}
        
    if result:
        # Update active tracker
        if address not in tracker.tracked_addresses:
            tracker.tracked_addresses.append(address)
        # Ensure it's not in disabled list
        if address in tracker.disabled_addresses:
            tracker.disabled_addresses.remove(address)
            
        logger.info(f"User {user_id} added wallet: {address}")
        return {"message": f"Added wallet {address}", "wallets": tracker.tracked_addresses}
    
    return {"message": "Failed to add wallet", "wallets": tracker.tracked_addresses}

@app.post("/stripe/create-checkout-session")
async def create_stripe_checkout(request: Request):
    """Create a $5 Stripe Checkout session for an additional address slot."""
    user_id = request.state.user_id
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Add 1 Address Slot',
                        'description': 'Expand your terminal by one additional address slot',
                    },
                    'unit_amount': 500, # $5.00
                },
                'quantity': 1,
            }],
            mode='payment',
            client_reference_id=user_id,
            success_url=f"{FRONTEND_URL}/?payment=success",
            cancel_url=f"{FRONTEND_URL}/?payment=cancel",
            metadata={
                "user_id": user_id,
                "type": "extra_slot"
            }
        )
        return {"id": session.id, "url": session.url}
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment session")

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Verify Stripe payment and update user slots."""
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    
    if not sig_header:
        logger.warning("Missing Stripe-Signature header")
        raise HTTPException(status_code=400, detail="Missing signature")
    
    try:
        if STRIPE_WEBHOOK_SECRET == "whsec_mock":
            logger.warning("Using MOCK Stripe Webhook Secret (whsec_mock). Skipping signature verification for testing!")
            event = await request.json()
        else:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
    except ValueError as e:
        logger.error(f"Invalid Stripe payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing error")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        
        if user_id:
            user_data = get_user_data(user_id)
            if user_data:
                user_data["extraSlots"] = user_data.get("extraSlots", 0) + 1
                update_user_data(user_id, user_data)
                logger.info(f"User {user_id} purchased an extra slot via Stripe session {session['id']}. Total extra: {user_data['extraSlots']}")
            else:
                logger.error(f"User data not found for user_id: {user_id} during Stripe payment processing")
        else:
            logger.error(f"user_id missing in Stripe session metadata for session: {session['id']}")
            
    return {"status": "success"}

@app.post("/wallets/terminate")
async def terminate_wallet_endpoint(request: Request, address: str):
    user_id = request.state.user_id
    address = address.lower()
    
    if terminate_wallet(user_id, address):
        if address not in tracker.disabled_addresses:
            tracker.disabled_addresses.add(address)
        logger.info(f"User {user_id} terminated wallet: {address}")
        return {"message": f"Terminated wallet {address}", "wallets": tracker.tracked_addresses}
    
    return {"message": "Failed to terminate wallet", "wallets": tracker.tracked_addresses}

@app.get("/profiles/{address}")
async def get_profile(address: str):
    """Proxy to fetch Polymarket user profile data."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Polymarket Gamma API for public profiles
            response = await client.get(f"https://gamma-api.polymarket.com/public-profile?address={address}")
            if response.status_code == 200:
                data = response.json()
                return {
                    "username": data.get("name"),
                    "displayName": data.get("pseudonym"),
                    "bio": data.get("bio"),
                    "proxyWallet": data.get("proxyWallet"),
                    "image": data.get("profileImage")
                }
            else:
                return {}
    except Exception as e:
        logger.error(f"Error fetching profile for {address}: {e}")
        return {}

@app.get("/trades")
async def get_trades(request: Request):
    user_id = request.state.user_id
    from db import get_user_trades
    history = get_user_trades(user_id)
    if not history:
        return trade_history # Fallback to in-memory if DB is empty or fails
    return history

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

# Mangum handler for AWS Lambda (placed at bottom to ensure all routes are registered)
handler = Mangum(app)
