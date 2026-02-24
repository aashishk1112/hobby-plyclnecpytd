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
from db import get_user_data, update_user_data, add_wallet as db_add_wallet, remove_wallet as db_remove_wallet

from tracker import PolymarketTracker
import razorpay

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for trades
trade_history = []
category_filters = []

# Global# Trackers - initialized on startup
# In a real multi-user system, these would be per-user
tracker = PolymarketTracker("local-test-user", [], trade_history, {"balance": 100.0, "initial_balance": 100.0}, category_filters)

# Razorpay client initialization
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mock")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "mock_secret")
razor_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
# Load AWS Config for JWT verification
AWS_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", ".aws_config.json")
with open(AWS_CONFIG_PATH, "r") as f:
    aws_config = json.load(f)

REGION = aws_config.get("REGION", "us-east-1")
USER_POOL_ID = aws_config.get("USER_POOL_ID")
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT")

if USER_POOL_ID and not USER_POOL_ID.endswith("_dummy"):
    # Real Cognito User Pool - use official discovery URL
    JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
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
handler = Mangum(app)

async def get_current_user(request):
    """Extraction logic for user context from JWT."""
    auth_header = request.headers.get("Authorization")
    
    # Check if mock auth is enabled (default to False for production)
    is_mock = os.getenv("MOCK_AUTH", "False").lower() == "true"
    
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
            return payload.get("sub") or payload.get("username")
        except Exception as e:
            logger.error(f"JWT Verification failed: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    else:
        # Fallback to unverified decode for Local/Mock or if config is missing
        try:
            payload = jwt.get_unverified_claims(token)
            user_id = payload.get("sub") or payload.get("username")
            if not user_id and is_mock:
                return f"user-{token}"
            return user_id
        except Exception:
            if is_mock:
                return f"user-{token}"
            raise HTTPException(status_code=401, detail="Invalid token")

@app.middleware("http")
async def auth_middleware(request, call_next):
    # Exclude preflight and public routes from auth
    if request.method == "OPTIONS" or request.url.path in ["/", "/docs", "/openapi.json", "/health"]:
        return await call_next(request)
    
    try:
        user_id = await get_current_user(request)
        request.state.user_id = user_id
    except HTTPException as e:
        # If we return a response here, it MUST go through CORSMiddleware
        # So CORSMiddleware must be added AFTER this middleware is defined.
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": f"Internal server error: {str(e)}"})
        
    return await call_next(request)

# Add CORS Middleware last to ensure it wraps around everything (including auth error responses)
# However, to be extra safe with custom error responses in middlewares, 
# we'll ensure the headers are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# In-memory storage for trades (fetched by UI)
# trade_history = [] # Moved above tracker initialization

@app.get("/")
async def root():
    return {"status": "online", "message": "Polymarket Copy Trade Bot Backend (Simplified)"}

@app.get("/config")
async def get_config(request: Request):
    user_id = request.state.user_id
    data = get_user_data(user_id)
    if data is None:
        data = {"userId": user_id, "trackedWallets": [], "disabledWallets": [], "initialBalance": 100.0, "filters": []}

    # Sync tracker state for this specific user call
    tracker.tracked_addresses = data.get("trackedWallets", [])
    tracker.disabled_addresses = set(data.get("disabledWallets", []))
    # Only sync initial_balance from DB when tracker still has default (avoids overwriting
    # in-memory state after capital reset with stale/eventually-consistent DB data)
    default_initial = 100.0
    if tracker.stats.get("initial_balance", default_initial) == default_initial:
        tracker.stats["initial_balance"] = float(data.get("initialBalance", default_initial))
    # Never overwrite balance from DB; it is only updated by tracker and update_config

    return {
        "tracked_wallets": tracker.tracked_addresses,
        "disabled_wallets": list(tracker.disabled_addresses),
        "paper_trading": os.getenv("PAPER_TRADING", "True") == "True",
        "stats": {
            "balance": float(tracker.stats.get("balance", default_initial)),
            "initial_balance": float(tracker.stats.get("initial_balance", default_initial)),
        },
        "filters": data.get("filters", []),
        "balance_history": tracker.balance_history,
        "subscription_status": data.get("subscriptionStatus", "free"),
        "subscription_id": data.get("subscriptionId")
    }

@app.post("/config/update")
async def update_config(request: Request, initial_balance: Optional[float] = None):
    user_id = request.state.user_id
    data = get_user_data(user_id)
    if data is None:
        data = {"userId": user_id, "trackedWallets": [], "disabledWallets": [], "initialBalance": 100.0, "filters": []}

    if initial_balance is not None:
        initial_balance = float(initial_balance)
        data["initialBalance"] = initial_balance
        tracker.stats["initial_balance"] = initial_balance

        # Reset current balance and trade history when capital is re-applied
        tracker.stats["balance"] = initial_balance
        trade_history.clear()
        await tracker.clear_cache()

        update_user_data(user_id, data)
        logger.info(f"Re-initialized capital for {user_id} to: {initial_balance}. History cleared.")

    # Return explicit numbers so frontend always gets correct types
    return {
        "stats": {
            "balance": float(tracker.stats.get("balance", 100.0)),
            "initial_balance": float(tracker.stats.get("initial_balance", 100.0)),
        }
    }

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
        raise HTTPException(status_code=402, detail="Address limit reached. Please purchase an additional slot for $5.")
    
    result = db_add_wallet(user_id, address)
    if result == "duplicate":
        raise HTTPException(status_code=400, detail="Address is already being tracked.")
        
    if result:
        # Update active tracker
        if address not in tracker.tracked_addresses:
            tracker.tracked_addresses.append(address)
        logger.info(f"User {user_id} added wallet: {address}")
        return {"message": f"Added wallet {address}", "wallets": tracker.tracked_addresses}
    
    return {"message": "Failed to add wallet", "wallets": tracker.tracked_addresses}

@app.post("/razorpay/create-order")
async def create_razorpay_order(request: Request):
    """Create a $5 order for an additional address slot."""
    user_id = request.state.user_id
    try:
        amount = 500 # $5.00 in cents (or INR equivalent if configured, but using 500 for $5 logic)
        order_data = {
            "amount": amount * 100, # Razorpay expects sub-units
            "currency": "USD",
            "receipt": f"receipt_{user_id}_{int(os.times()[4])}",
            "notes": {
                "user_id": user_id,
                "type": "extra_slot"
            }
        }
        order = razor_client.order.create(data=order_data)
        return order
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment order")

@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    """Verify Razorpay payment and update user slots."""
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    try:
        # Verify webhook signature in a real scenario
        # razor_client.utility.verify_webhook_signature(payload, signature, WEBHOOK_SECRET)
        
        data = json.loads(payload)
        event = data.get("event")
        
        if event == "order.paid":
            order_id = data["payload"]["order"]["entity"]["id"]
            notes = data["payload"]["order"]["entity"].get("notes", {})
            user_id = notes.get("user_id")
            
            if user_id:
                user_data = get_user_data(user_id)
                if user_data:
                    user_data["extraSlots"] = user_data.get("extraSlots", 0) + 1
                    update_user_data(user_id, user_data)
                    logger.info(f"User {user_id} purchased an extra slot. Total extra: {user_data['extraSlots']}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Razorpay webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/wallets/remove")
async def remove_wallet(request: Request, address: str):
    user_id = request.state.user_id
    address = address.lower()
    
    if db_remove_wallet(user_id, address):
        if address in tracker.tracked_addresses:
            tracker.tracked_addresses.remove(address)
        logger.info(f"User {user_id} removed wallet: {address}")
        return {"message": f"Removed wallet {address}", "wallets": tracker.tracked_addresses}
    
    return {"message": "Failed to remove wallet", "wallets": tracker.tracked_addresses}

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
