from fastapi import Request, HTTPException, Depends
from jose import jwt
import httpx
import logging
from backend.core.config import get_config

logger = logging.getLogger(__name__)

USER_POOL_ID = get_config("USER_POOL_ID")
REGION = get_config("AWS_REGION", "ap-south-1")
LOCALSTACK_ENDPOINT = get_config("LOCALSTACK_ENDPOINT")

if USER_POOL_ID and not USER_POOL_ID.endswith("_dummy") and not USER_POOL_ID.endswith("_mock_id"):
    pool_region = USER_POOL_ID.split("_")[0] if "_" in USER_POOL_ID else REGION
    JWKS_URL = f"https://cognito-idp.{pool_region}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
elif LOCALSTACK_ENDPOINT and USER_POOL_ID and get_config("IS_LOCAL", "false").lower() == "true":
    JWKS_URL = f"{LOCALSTACK_ENDPOINT}/{USER_POOL_ID}/.well-known/jwks.json"
else:
    JWKS_URL = None

_jwks_cache = None

async def get_jwks():
    global _jwks_cache
    if _jwks_cache: return _jwks_cache
    if not JWKS_URL: return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(JWKS_URL)
            if resp.status_code == 200:
                _jwks_cache = resp.json()
                return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {JWKS_URL}: {e}")
    return None

async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    is_mock = get_config("MOCK_AUTH", "False").lower() == "true"
    
    if not auth_header or not auth_header.startswith("Bearer "):
        if is_mock: return "local-test-user"
        raise HTTPException(status_code=401, detail="Unauthorized: No Bearer token provided")
    
    token = auth_header.split(" ")[1]
    
    # Production Logic: Real Cognito JWT Validation
    if USER_POOL_ID and not is_mock:
        try:
            jwks = await get_jwks()
            if not jwks:
                logger.error("Identity provider configuration error: JWKS URL is missing or unreachable")
                raise HTTPException(status_code=500, detail="Identity provider configuration error")
            
            # Real validation using RS256
            payload = jwt.decode(token, jwks, algorithms=['RS256'], options={"verify_at_hash": False, "verify_aud": False})
            user_id = payload.get("sub") or payload.get("username")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: No subject claim found")
            return user_id
        except Exception as e:
            logger.error(f"Production JWT Verification failed: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
    # Fallback Logic: Mocking or Dev Testing
    else:
        try:
            if is_mock and token.startswith("mock-token-"):
                return f"user-{token.replace('mock-token-', '')}"
            
            # Unverified claims for quick dev check without JWKS
            payload = jwt.get_unverified_claims(token)
            user_id = payload.get("sub") or payload.get("username")
            if not user_id and is_mock: return f"user-{token}"
            return user_id
        except Exception:
            if is_mock: return f"user-{token}"
            raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_data(user_id: str = Depends(get_current_user)):
    from backend.db import get_user_data
    return get_user_data(user_id)

def require_subscription(required_tier: str):
    async def _check_tier(user_data: dict = Depends(get_current_user_data)):
        current_tier = user_data.get("subscriptionStatus", "free")
        # Elite > Pro > Free
        tiers = ["free", "pro", "elite"]
        if tiers.index(current_tier) < tiers.index(required_tier):
            raise HTTPException(
                status_code=402, 
                detail=f"Subscription required: {required_tier.title()} tier or higher is needed for this feature."
            )
        return user_data
    return _check_tier
