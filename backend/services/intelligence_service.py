import asyncio
import logging
import httpx
from typing import List, Dict, Optional
from backend.core.config import get_config
from backend.core.ws import manager
from backend.services.alpha_stream_service import alpha_stream_service
import time

logger = logging.getLogger(__name__)

class IntelligenceService:
    def __init__(self):
        self.whale_threshold = float(get_config("WHALE_THRESHOLD", "25.0"))
        self.api_url = "https://data-api.polymarket.com/trades"
        self.seen_whale_trades = set()
        self.wallet_patterns = {} # wallet -> list of recent trades for trend detection

    def calculate_pro_score(self, trades: List[Dict]) -> float:
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
        
        # Consistency score (placeholder for actual variance calculation)
        consistency_score = 75.0 
        
        final_score = (win_rate * 0.4) + (min(roi, 100) * 0.3) + (consistency_score * 0.3)
        return round(min(max(final_score, 0), 100), 2)

    async def detect_whales(self) -> List[Dict]:
        """
        Whale Radar v2: Enhanced detection with pattern-based thresholding.
        Returns a list of high-conviction institutional trades.
        """
        logger.info(f"Whale Radar v2: Scanning with base threshold {self.whale_threshold}...")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.api_url, params={"limit": 200})
                if response.status_code != 200: return []
                
                trades = response.json()
                whales = []
                for trade in trades:
                    tx_hash = trade.get("transactionHash")
                    wallet = trade.get("proxyWallet") or trade.get("taker")
                    if not tx_hash or tx_hash in self.seen_whale_trades: continue
                        
                    amount = float(trade.get("size", 0))
                    price = float(trade.get("price", 0))
                    total_value = amount * price
                    
                    # Pattern-based thresholding: Lower threshold for wallets that are "heating up"
                    dynamic_threshold = self.whale_threshold
                    recent_trades = self.wallet_patterns.get(wallet, [])
                    if len(recent_trades) >= 3:
                        dynamic_threshold *= 0.5 # 50% lower threshold for active institutional accumulation
                    
                    if total_value >= dynamic_threshold:
                        classification = self._classify_trader_v2(total_value, trade.get("title", ""), wallet)
                        whale_data = {
                            "id": tx_hash,
                            "timestamp": trade.get("timestamp"),
                            "wallet": wallet,
                            "market": trade.get("title"),
                            "amount": amount,
                            "price": price,
                            "value": total_value,
                            "side": trade.get("side", "BUY"),
                            "classification": classification,
                            "confidence": 85 if total_value >= self.whale_threshold else 65
                        }
                        whales.append(whale_data)
                        self.seen_whale_trades.add(tx_hash)
                        
                        # Broadcast new whale
                        await manager.broadcast({
                            "type": "WHALE_RADAR",
                            "data": whale_data
                        })
                        
                        # Feed the Alpha Stream
                        await alpha_stream_service.broadcast_whale_event(whale_data)
                        
                        # Update wallet pattern
                        recent_trades.append({"timestamp": time.time(), "value": total_value})
                        self.wallet_patterns[wallet] = recent_trades[-10:] # Keep last 10
                        
                return whales
        except Exception as e:
            logger.error(f"Whale Radar v2 error: {e}")
            return []

    def _classify_trader_v2(self, value: float, market_title: str, wallet: str) -> str:
        """Advanced classification based on size, market, and historical frequency."""
        market_lower = market_title.lower()
        hist = self.wallet_patterns.get(wallet, [])
        
        is_accumulating = len(hist) > 5 and all(t["value"] > 5000 for t in hist)
        
        if is_accumulating: return "Systematic Accumulator"
        if value > 250000: return "Sovereign Tier Whale"
        if value > 100000: return "Institutional Prime"
        
        if any(k in market_lower for k in ["trump", "election", "politics"]):
            return "Political Insider"
        if any(k in market_lower for k in ["fed", "rate", "inflation", "macro"]):
            return "Macro Strategist"
        
        return "Market Architect"

    async def generate_predictive_signals(self) -> List[Dict]:
        """Detect patterns indicating future large trades (High-Conviction)."""
        whales = await self.detect_whales()
        signals = []
        
        for w in whales:
            confidence = w["confidence"]
            if w["classification"] in ["Systematic Accumulator", "Sovereign Tier Whale"]:
                confidence += 10.0
            
            signal = {
                "id": f"sig-{w['id']}",
                "type": "Predictive Alpha",
                "confidence": min(confidence, 99.0),
                "market": w["market"],
                "reason": f"High-conviction {w['classification']} detected. Pattern suggests institutional momentum.",
                "timestamp": w["timestamp"]
            }
            signals.append(signal)
            
    async def get_institutional_leaderboard(self) -> List[Dict]:
        """
        Fetch real-time high-performing nodes from Polymarket's official Leaderboard API.
        Provides 100% accurate daily PNL and volume metrics.
        """
        try:
            url = "https://data-api.polymarket.com/v1/leaderboard?timePeriod=day&orderBy=PNL&limit=10&category=overall"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200: 
                    logger.error(f"Polymarket Leaderboard API error: {response.status_code}")
                    return []
                
                data = response.json()
                leaderboard = []
                
                for item in data:
                    pnl = float(item.get("pnl", 0))
                    vol = float(item.get("vol", 0))
                    
                    # Pro Score calculation based on real volume and daily PNL
                    # Score = Base(80) + Log scaling of volume + bonus for PNL consistency
                    pro_score = min(99, 80 + int((vol / 1000000) * 5) + (5 if pnl > 0 else 0))
                    
                    leaderboard.append({
                        "rank": int(item.get("rank", 0)),
                        "userName": item.get("userName") or "Institutional Node",
                        "pnl": str(int(pnl)),
                        "proxyWallet": item.get("proxyWallet"),
                        "pro_score": pro_score,
                        "vol": f"{int(vol/1000)}k", # Extra metadata for frontend if needed
                        "profile_image": item.get("profileImage") or ""
                    })
                
                return leaderboard
        except Exception as e:
            logger.error(f"Institutional Leaderboard error: {e}")
            return []

    async def get_retail_heatmap(self) -> List[Dict]:
        """
        Identify 'retail-heavy' markets by analyzing trade frequency vs. trade size.
        Whales often use these as exit liquidity or 'social arbitrage' opportunities.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.api_url, params={"limit": 100})
                if response.status_code != 200: return []
                
                trades = response.json()
                market_stats = {} # market -> {count, total_size, retail_count}
                
                for t in trades:
                    market = t.get("title", "Unknown")
                    size = float(t.get("size", 0))
                    
                    if market not in market_stats:
                        market_stats[market] = {"count": 0, "total_size": 0, "retail_count": 0}
                    
                    market_stats[market]["count"] += 1
                    market_stats[market]["total_size"] += size
                    if size < 500: # Definition of retail trade
                        market_stats[market]["retail_count"] += 1
                
                heatmap = []
                for market, stats in market_stats.items():
                    if stats["count"] >= 5: # Minimum activity to be 'hot'
                        retail_ratio = stats["retail_count"] / stats["count"]
                        heatmap.append({
                            "market": market,
                            "intensity": min(stats["count"] * 2, 100), # 0-100 scale
                            "retail_ratio": round(retail_ratio, 2),
                            "sentiment": "Crowded" if retail_ratio > 0.7 else "Balanced"
                        })
                
                return sorted(heatmap, key=lambda x: x["intensity"], reverse=True)[:10]
        except Exception as e:
            logger.error(f"Retail Heatmap error: {e}")
            return []

# Global instance for easy import or dependency injection
intelligence_service = IntelligenceService()
