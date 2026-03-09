from fastapi import WebSocket
from typing import List, Dict
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # active_connections maps user_id to a list of their active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WebSocket. Active sessions: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket.")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            message_json = json.dumps(message)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.error(f"Failed to send WS message to {user_id}: {e}")

    async def broadcast(self, message: dict):
        message_json = json.dumps(message)
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.error(f"Failed to broadcast WS message to {user_id}: {e}")

manager = ConnectionManager()
