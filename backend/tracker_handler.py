import asyncio
import logging
from tracker import PolymarketTracker
from db import get_users, get_user_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run(event, context):
    """
    Lambda entry point for scheduled tracking.
    """
    logger.info("Starting scheduled tracker poll...")
    
    # In a real multi-user system, we iterate through all users
    # For now, we use our mock-user or a way to get active users
    
    user_ids = get_users() 
    if not user_ids:
        logger.info("No users found to poll.")
        return {"status": "success", "message": "No users found"}
    
    for user_id in user_ids:
        # Fetch user configuration
        data = get_user_data(user_id)
        if not data:
            continue
            
        # Initialize tracker for the user with their saved configuration
        tracker = PolymarketTracker(
            user_id=user_id,
            tracked_addresses=data.get("trackedWallets", []),
            trade_history=[], # History is in DB, tracker only needs it for in-memory display (not used in Lambda poll)
            stats={"balance": data.get("balance", 100.0), "initial_balance": data.get("initialBalance", 100.0)},
            category_filters=data.get("filters", [])
        )
        
        # Populate seen_trade_hashes from DB history to avoid double-processing (optional but good)
        # For simplicity in this poll, we'll let the tracker handle detection.
        # However, to be truly stateless, we need seen_trade_hashes to persist.
        # In a real system, we'd query the latest X trades from DB to populate seen_trade_hashes.
        
        # Run the poll cycle
        asyncio.run(tracker.poll_once())
        
    logger.info("Scheduled tracker poll completed.")
    return {
        "status": "success",
        "message": f"Processed {len(user_ids)} users"
    }
