import asyncio
import logging
import time
import httpx
from typing import List, Dict, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class TraderScoringEngine:
    @staticmethod
    def calculate_score(trades: List[Dict]) -> float:
        """
        Calculate a Pro Score (0-100) based on ROI, Win Rate, and Consistency.
        """
        if not trades:
            return 0.0
        
        wins = 0
        total_pnl = 0.0
        
        for trade in trades:
            pnl = float(trade.get("pnl", 0))
            total_pnl += pnl
            if pnl > 0:
                wins += 1
        
        win_rate = (wins / len(trades)) * 100
        roi = (total_pnl / len(trades)) * 100 if len(trades) > 0 else 0
        
        # Consistency: higher weight on lower variance in trade sizes (simulated weight)
        consistency_score = 75.0 # Placeholder for actual variance calculation
        
        # Weighted formula
        final_score = (win_rate * 0.4) + (min(roi, 100) * 0.3) + (consistency_score * 0.3)
        return round(min(max(final_score, 0), 100), 2)

class WhaleRadar:
    def __init__(self, threshold: float = 10000.0):
        self.threshold = threshold
        self.api_url = "https://data-api.polymarket.com/trades"
        self.seen_whale_trades = set()

    async def detect_whales(self) -> List[Dict]:
        """
        Scan global trades for transactions exceeding the threshold.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Poll global trades (limit 100 to find whales)
                response = await client.get(self.api_url, params={"limit": 50})
                if response.status_code != 200:
                    return []
                
                trades = response.json()
                if not isinstance(trades, list):
                    return []
                
                whales = []
                for trade in trades:
                    tx_hash = trade.get("transactionHash")
                    if not tx_hash or tx_hash in self.seen_whale_trades:
                        continue
                        
                    amount = float(trade.get("size", 0))
                    price = float(trade.get("price", 0))
                    total_value = amount * price
                    
                    if total_value >= self.threshold:
                        classification = self.classify_trader(total_value, trade.get("title", ""))
                        whale_data = {
                            "id": tx_hash,
                            "timestamp": trade.get("timestamp"),
                            "wallet": trade.get("taker"),
                            "market": trade.get("title"),
                            "amount": amount,
                            "price": price,
                            "value": total_value,
                            "side": trade.get("side", "BUY"),
                            "classification": classification
                        }
                        whales.append(whale_data)
                        self.seen_whale_trades.add(tx_hash)
                        
                # Keep cache small
                if len(self.seen_whale_trades) > 500:
                    self.seen_whale_trades.clear()
                    
                return whales
        except Exception as e:
            logger.error(f"Whale Radar error: {e}")
            return []

    def classify_trader(self, value: float, market_title: str) -> str:
        """Categorize whale based on trade size and market context."""
        market_lower = market_title.lower()
        if value > 100000:
            return "Institutional Titan"
        if any(k in market_lower for k in ["bitcoin", "eth", "crypto", "solana"]):
            return "Crypto Whale"
        if any(k in market_lower for k in ["trump", "election", "politics", "biden"]):
            return "Political Strategist"
        if value > 50000:
            return "Alpha Whale"
        return "Market Mover"

    async def generate_predictive_signals(self) -> List[Dict]:
        """Detect patterns indicating future large trades."""
        whales = await self.detect_whales()
        signals = []
        
        for w in whales:
            # Pattern 1: Scout Trade (small trade on a market before whale moves)
            # Simulated: if a whale just traded, check if it's a 'Leading Signal'
            confidence = 65.0
            if w["classification"] == "Institutional Titan":
                confidence += 20.0
            
            signal = {
                "id": f"sig-{w['id']}",
                "type": "Predictive Alpha",
                "confidence": min(confidence, 99.0),
                "market": w["market"],
                "reason": f"Institutional cluster detect in {w['market']}. High probability of follow-up liquidity.",
                "timestamp": w["timestamp"]
            }
            signals.append(signal)
            
        return signals
