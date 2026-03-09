import logging
from typing import List, Dict, Optional
from backend.db import get_user_data, update_user_data
from backend.core.ws import manager
import asyncio

logger = logging.getLogger(__name__)

class SocialService:
    def follow_user(self, follower_id: str, target_id: str) -> bool:
        """Add target_id to follower's 'following' and follower_id to target's 'followers'."""
        if follower_id == target_id:
            return False
            
        follower_data = get_user_data(follower_id)
        target_data = get_user_data(target_id)
        
        if not follower_data or not target_data:
            return False
            
        following = follower_data.get("following", [])
        if target_id not in following:
            following.append(target_id)
            follower_data["following"] = following
            update_user_data(follower_id, follower_data)
            
        followers = target_data.get("followers", [])
        if follower_id not in followers:
            followers.append(follower_id)
            target_data["followers"] = followers
            update_user_data(target_id, target_data)
            
        logger.info(f"User {follower_id} followed {target_id}")
        
        # Broadcast to target user and globally for the feed
        asyncio.create_task(manager.send_personal_message({
            "type": "SOCIAL_FOLLOW",
            "data": {"follower_id": follower_id, "message": f"User {follower_id} started following you!"}
        }, target_id))
        
        asyncio.create_task(manager.broadcast({
            "type": "SOCIAL_FEED_UPDATE",
            "data": {"user": follower_id, "action": "followed", "target": target_id}
        }))
        
        return True

    def get_public_profile(self, user_id: str) -> Optional[Dict]:
        """Retrieve a user's profile if it is marked as public."""
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get("isPublic", False):
            return None
            
        # Strip sensitive info
        profile = {
            "userId": user_data["userId"],
            "name": user_data.get("name"),
            "picture": user_data.get("picture"),
            "bio": user_data.get("bio", ""),
            "followerCount": len(user_data.get("followers", [])),
            "followingCount": len(user_data.get("following", [])),
            "subscriptionTier": user_data.get("subscriptionStatus", "free"),
            "tradingStats": {
                "balance": user_data.get("balance"),
                "totalPnl": user_data.get("totalPnl", 0) # Assumed field from db
            }
        }
        return profile

    def update_profile_settings(self, user_id: str, bio: str, is_public: bool):
        """Update a user's bio and visibility settings."""
        user_data = get_user_data(user_id)
        if user_data:
            user_data["bio"] = bio
            user_data["isPublic"] = is_public
            update_user_data(user_id, user_data)
            return True
        return False

social_service = SocialService()
