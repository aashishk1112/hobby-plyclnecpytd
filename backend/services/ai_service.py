import logging
from typing import List, Dict
from backend.services.intelligence_service import intelligence_service

logger = logging.getLogger(__name__)

class AIService:
    async def build_optimized_portfolio(self, risk_level: str = "balanced") -> Dict:
        """
        Analyze current market intelligence to suggest an optimized portfolio.
        Risk levels: 'conservative', 'balanced', 'aggressive'
        """
        whales = await intelligence_service.detect_whales()
        heatmap = await intelligence_service.get_retail_heatmap()
        
        # Scoring markets based on Whale Conviction vs Retail Crowdedness
        recommendations = []
        for w in whales:
            market = w["market"]
            confidence = w["confidence"]
            
            # Find if this market is 'crowded' (retail heavy)
            crowdedness = next((h["retail_ratio"] for h in heatmap if h["market"] == market), 0.3)
            
            # Institutional Conviction Score
            score = confidence * (1 - crowdedness)
            
            recommendations.append({
                "market": market,
                "score": round(score, 2),
                "reason": f"High institutional conviction found. {w['classification']} activity detected.",
                "allocation": 0 # to be calculated
            })
        
        # Sort and limit
        recommendations = sorted(recommendations, key=lambda x: x["score"], reverse=True)[:5]
        
        # Simple allocation logic
        total_score = sum(r["score"] for r in recommendations)
        if total_score > 0:
            for r in recommendations:
                r["allocation"] = round((r["score"] / total_score) * 100, 2)
        
        return {
            "portfolio_type": "Whale-Follower Alpha",
            "risk_logic": risk_level,
            "top_assets": recommendations,
            "total_conviction": round(total_score, 2)
        }

ai_service = AIService()
