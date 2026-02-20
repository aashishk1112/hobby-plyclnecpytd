from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import List
import os
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from tracker import PolymarketTracker

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for trades (shared with tracker)
trade_history = []
stats = {"balance": 100.0, "initial_balance": 100.0}
category_filters = []

# Global tracker instance
tracker = PolymarketTracker([], trade_history, stats, category_filters)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start tracker in background
    import asyncio
    asyncio.create_task(tracker.start())
    yield
    tracker.stop()

app = FastAPI(title="Polymarket Copy Trade Bot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for trades (fetched by UI)
# trade_history = [] # Moved above tracker initialization

@app.get("/")
async def root():
    return {"status": "online", "message": "Polymarket Copy Trade Bot Backend (Simplified)"}

@app.get("/config")
async def get_config():
    return {
        "tracked_wallets": tracker.tracked_addresses,
        "paper_trading": os.getenv("PAPER_TRADING", "True") == "True",
        "stats": stats,
        "filters": category_filters
    }

@app.post("/trades/clear")
async def clear_trades():
    trade_history.clear()
    stats["balance"] = stats["initial_balance"]
    tracker.clear_cache()
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
async def add_wallet(address: str):
    address = address.lower()
    if address not in tracker.tracked_addresses:
        tracker.tracked_addresses.append(address)
        logger.info(f"Started monitoring wallet: {address}")
        return {"message": f"Added wallet {address}", "wallets": tracker.tracked_addresses}
    return {"message": "Wallet already tracked", "wallets": tracker.tracked_addresses}

@app.post("/wallets/remove")
async def remove_wallet(address: str):
    address = address.lower()
    if address in tracker.tracked_addresses:
        tracker.tracked_addresses.remove(address)
        logger.info(f"Stopped monitoring wallet: {address}")
        return {"message": f"Removed wallet {address}", "wallets": tracker.tracked_addresses}
    return {"message": "Wallet not found", "wallets": tracker.tracked_addresses}

@app.get("/trades")
async def get_trades():
    return trade_history

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
