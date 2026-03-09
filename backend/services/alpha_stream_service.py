import asyncio
import random
import time
import logging
from typing import List, Dict
from backend.core.ws import manager

logger = logging.getLogger(__name__)

class AlphaStreamService:
    def __init__(self):
        self.is_running = False
        self.mock_users = ["WhaleHunter_X", "Alpha_Node_1", "Institutional_Prime", "Macro_Strategist", "Liquid_Alpha", "Sovereign_Node"]
        self.actions = ["followed", "replicated", "upgraded", "analyzed", "signaled"]
        self.targets = ["Institutional_Prime", "Retail_Heatmap", "Elite Tier", "0x32...1298", "Tesla Market", "Trump Election"]

    async def start_broadcasting(self):
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Alpha Stream Service started.")
        
        while self.is_running:
            try:
                # Randomly decide to send a simulated event or wait
                if random.random() < 0.3: # 30% chance every loop
                    event = self._generate_simulated_event()
                    await manager.broadcast({
                        "type": "ALPHA_STREAM_UPDATE",
                        "data": event
                    })
                
                await asyncio.sleep(random.randint(5, 15)) # Random delay between events
            except Exception as e:
                logger.error(f"Alpha Stream error: {e}")
                await asyncio.sleep(30)

    def _generate_simulated_event(self) -> Dict:
        user = random.choice(self.mock_users)
        action = random.choice(self.actions)
        target = random.choice(self.targets)
        
        return {
            "user": user,
            "action": action,
            "target": target,
            "time": "Just now",
            "type": "SOCIAL"
        }

    async def broadcast_whale_event(self, whale_data: Dict):
        """Bridge real whale radar events into the alpha stream."""
        wallet = whale_data.get('wallet') or '0xUnknown'
        logger.info(f"ALPHA_STREAM: Broadcasting whale event for wallet: {wallet}")
        event = {
            "user": wallet,
            "action": "accumulated",
            "target": f"{whale_data.get('market', 'Unknown')}",
            "time": "Just now",
            "value": whale_data.get("value"),
            "wallet": wallet,
            "type": "WHALE"
        }
        await manager.broadcast({
            "type": "ALPHA_STREAM_UPDATE",
            "data": event
        })

alpha_stream_service = AlphaStreamService()
