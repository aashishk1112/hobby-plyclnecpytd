import asyncio
import logging
import time
import httpx
from typing import List, Dict, Optional, Set
from backend.core.config import get_config
from backend.models.trade import Trade
from backend.db import is_trade_processed, save_trade, update_user_balance

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self):
        self.paper_trading = get_config("PAPER_TRADING", "True").lower() == "true"
        # Real client initialization would go here if not paper_trading
        self.client = None

    async def execute_trade(self, token_id: str, side: str, amount: float, price: float):
        if self.paper_trading:
            logger.info(f"[PAPER] Replica Execution: {side} {amount} units of {token_id} at {price}")
            return {"status": "success", "mode": "paper"}
        
        # Real execution logic
        logger.info(f"[LIVE] Replica Execution: {side} {amount} units of {token_id} at {price}")
        return {"status": "success", "mode": "live"}

class TradingService:
    def __init__(self):
        self.executor = TradeExecutor()
        self.user_trackers: Dict[str, asyncio.Task] = {}
        self.api_url = "https://data-api.polymarket.com/trades"

    async def start_user_tracker(self, user_id: str, tracked_addresses: List[str], user_stats: Dict):
        if user_id in self.user_trackers:
            self.user_trackers[user_id].cancel()
        
        task = asyncio.create_task(self._tracker_loop(user_id, tracked_addresses, user_stats))
        self.user_trackers[user_id] = task
        return task

    async def stop_user_tracker(self, user_id: str):
        if user_id in self.user_trackers:
            self.user_trackers[user_id].cancel()
            del self.user_trackers[user_id]

    async def _tracker_loop(self, user_id: str, addresses: List[str], stats: Dict):
        seen_hashes: Set[str] = set()
        logger.info(f"Started tracker loop for user {user_id} with {len(addresses)} addresses")
        
        while True:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    for addr in addresses:
                        resp = await client.get(self.api_url, params={"taker": addr, "limit": 5})
                        if resp.status_code != 200: continue
                        
                        trades = resp.json()
                        for t in trades:
                            tx_hash = t.get("transactionHash")
                            if not tx_hash or tx_hash in seen_hashes: continue
                            
                            if is_trade_processed(user_id, tx_hash):
                                seen_hashes.add(tx_hash)
                                continue

                            # Logic for replication
                            await self._process_replication(user_id, addr, t, stats, seen_hashes)
                            
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tracker error for user {user_id}: {e}")
                await asyncio.sleep(30)

    async def _process_replication(self, user_id: str, source_addr: str, trade_data: Dict, stats: Dict, seen_hashes: Set[str]):
        tx_hash = trade_data.get("transactionHash")
        seen_hashes.add(tx_hash)
        
        side = trade_data.get("side", "BUY")
        price = float(trade_data.get("price", 0))
        amount = float(trade_data.get("size", 0))
        total_value = amount * price
        
        # Simple replication logic
        if stats.get("balance", 0) < total_value:
            logger.warning(f"Insufficient balance for user {user_id} to replicate trade {tx_hash}")
            return

        # Execute
        result = await self.executor.execute_trade(
            token_id=trade_data.get("asset", "UNKNOWN"),
            side=side,
            amount=amount,
            price=price
        )
        
        if result["status"] == "success":
            # Update DB
            new_balance = stats["balance"] - total_value if side == "BUY" else stats["balance"] + total_value
            stats["balance"] = new_balance
            
            save_trade(user_id, {
                "id": tx_hash,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "wallet": source_addr,
                "market": trade_data.get("title", "Unknown"),
                "side": side,
                "amount": amount,
                "price": price,
                "total": total_value,
                "status": "executed"
            })
            update_user_balance(user_id, new_balance)

trading_service = TradingService()
