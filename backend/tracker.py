import asyncio
import json
import logging
import os
import time
import httpx
from trader import TradeExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolymarketTracker:
    def __init__(self, user_id: str, tracked_addresses: list, trade_history: list, stats: dict = None, category_filters: list = None):
        self.user_id = user_id
        self.tracked_addresses = [addr.lower() for addr in tracked_addresses]
        self.disabled_addresses = set() # Addresses to skip during monitoring
        self.trade_history = trade_history
        self.stats = stats if stats is not None else {"balance": 100.0, "initial_balance": 100.0}
        self.stats["balance"] = float(self.stats.get("balance", 100.0))
        self.balance_threshold = float(stats.get("balance_threshold", 0.0)) if stats else 0.0
        self.category_filters = category_filters if category_filters is not None else []
        self.balance_history = [{"timestamp": time.time(), "balance": self.stats["balance"]}]
        self.running = False
        self.trader = TradeExecutor()
        self.seen_trade_hashes = set()
        self.api_url = "https://data-api.polymarket.com/trades"

    async def poll_once(self):
        """Run a single polling cycle for Lambda."""
        logger.info(f"Running single poll for user: {self.user_id}")
        await self.monitor_loop()
        return True

    async def start(self):
        self.running = True
        logger.info("Polymarket Tracker started (Production Mode)")
        
        # Initial poll to populate seen_trade_hashes
        await self.monitor_loop(initial=True)
        
        while self.running:
            await self.monitor_loop()
            await asyncio.sleep(10) # Reduced to 10s for better responsiveness

    async def monitor_loop(self, initial=False):
        """
        Poll for new trades from tracked addresses using Polymarket Data API.
        """
        # Copy list and filter out disabled addresses
        addresses_to_check = [addr for addr in self.tracked_addresses if addr not in self.disabled_addresses]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for address in addresses_to_check:
                try:
                    logger.debug(f"Polling real trades for {address}...")
                    
                    params = {
                        "taker": address,
                        "limit": 5
                    }
                    
                    response = await client.get(self.api_url, params=params)
                    if response.status_code != 200:
                        logger.error(f"Failed to fetch trades for {address}: {response.status_code}")
                        continue
                        
                    trades = response.json()
                    if not isinstance(trades, list):
                        continue
                        
                    for trade in trades:
                        tx_hash = trade.get("transactionHash")
                        if not tx_hash:
                            continue
                        
                        market_title = trade.get("title", "Unknown Market").lower()
                        
                        # If this is a new trade (not seen before)
                        if tx_hash in self.seen_trade_hashes:
                            logger.debug(f"DEBUG: Skipping already seen trade {tx_hash}")
                            continue
                        
                        # Double check database for persistent seen (important for Lambda/restarts)
                        from db import is_trade_processed
                        if is_trade_processed(self.user_id, tx_hash):
                            logger.debug(f"DEBUG: Skipping already processed trade {tx_hash} (found in DB)")
                            self.seen_trade_hashes.add(tx_hash)
                            continue

                        self.seen_trade_hashes.add(tx_hash)
                            
                        # Apply category filter for execution only (not for initial seen population)
                        matching_filter = "All"
                        if self.category_filters:
                            market_slug = trade.get("slug", "").lower()
                            title_lower = market_title.lower()
                            matched_cat = None
                            
                            # Smart mapping for broad categories
                            SMART_MAPPING = {
                                "crypto": ["bitcoin", "btc", "eth", "ethereum", "solana", "sol", "crypto", "blockchain", "memecoin"],
                                "politics": ["trump", "biden", "harris", "election", "politics", "white house", "senate", "republican", "democrat"],
                                "sports": ["nba", "nfl", "soccer", "mlb", "tennis", "f1", "sports", "basketball", "football"],
                                "entertainment": ["oscars", "grammys", "movie", "celebrity", "entertainment", "hollywood"]
                            }

                            for cat in self.category_filters:
                                cat_lower = cat.lower()
                                # Check direct match
                                if cat_lower in title_lower or cat_lower in market_slug:
                                    matched_cat = cat
                                    break
                                
                                # Check smart mapping
                                if cat_lower in SMART_MAPPING:
                                    if any(keyword in title_lower or keyword in market_slug for keyword in SMART_MAPPING[cat_lower]):
                                        matched_cat = cat
                                        break
                            
                            if not matched_cat:
                                logger.info(f"FILTER: Skipping trade '{market_title}' (No match for active filters: {self.category_filters})")
                                continue
                            matching_filter = matched_cat

                        # Don't execute paper trades on initial historical fetch
                        if not initial:
                            logger.info(f"REAL trade detected for {address} in {trade.get('title')}!")
                            
                            side = trade.get("side", "BUY")
                            market_title = trade.get("title", "Unknown Market")
                            price = float(trade.get("price", 0))
                            amount = float(trade.get("size", 0))
                            total_cost = amount * price
                            timestamp_sec = trade.get("timestamp")
                            
                            formatted_time = time.strftime("%H:%M:%S", time.localtime(timestamp_sec)) if timestamp_sec else time.strftime("%H:%M:%S")
                            
                            # Check balance threshold
                            if self.stats["balance"] < self.balance_threshold:
                                logger.warning(f"THRESHOLD: Skipping trade execution. Balance ${self.stats['balance']:.2f} is below threshold ${self.balance_threshold:.2f}")
                                continue

                            # Update paper balance
                            if side == "BUY":
                                self.stats["balance"] -= total_cost
                            else:
                                self.stats["balance"] += total_cost

                            trade_data = {
                                "id": tx_hash,
                                "timestamp": formatted_time,
                                "wallet": address,
                                "market": market_title,
                                "side": side,
                                "amount": amount,
                                "price": price,
                                "total": total_cost,
                                "total_cost": total_cost,
                                "status": "executed",
                                "category": matching_filter
                            }
                            
                            # Execute paper trade replication
                            await self.trader.execute_trade(
                                token_id=trade.get("asset", "UNKNOWN"),
                                side=side,
                                amount=amount,
                                price=price
                            )
                            
                            # Record in history for UI
                            self.trade_history.insert(0, trade_data)
                            
                            # Persist to DynamoDB if we have user context
                            # For the global tracker instance in main.py, we might need a way to pass the user_id
                            # or handle it per-user. For now, we'll try to find the user_id from the session.
                            # In a multi-user setup, the tracker should probably be refactored to be user-aware.
                            # Using 'default-user' or the one from main.py
                            from db import save_trade, update_user_balance
                            trade_data["timestamp_raw"] = timestamp_sec or time.time()
                            save_trade(self.user_id, trade_data)
                            update_user_balance(self.user_id, self.stats["balance"])

                            # Add to balance history for chart
                            self.balance_history.append({"timestamp": time.time(), "balance": self.stats["balance"]})
                            if len(self.balance_history) > 100:
                                self.balance_history.pop(0)

                            if len(self.trade_history) > 50:
                                self.trade_history.pop()
                    
                except Exception as e:
                    logger.error(f"Error polling {address}: {str(e)}", exc_info=True)

    async def clear_cache(self):
        """Reset the seen trade cache to allow re-detecting recent items."""
        self.seen_trade_hashes.clear()
        self.balance_history = [{"timestamp": time.time(), "balance": self.stats["balance"]}]
        logger.info("Tracker seen_trade_hashes cache cleared")

    def stop(self):
        self.running = False
        logger.info("Polymarket Tracker stopped")

if __name__ == "__main__":
    # Test tracking with an empty list or specific address
    tracker = PolymarketTracker([], [])
    asyncio.run(tracker.start())
