from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from backend.core.config import get_config
from backend.api import intelligence, trading, billing, auth, ai, social
from backend.core.ws import manager
from backend.services.alpha_stream_service import alpha_stream_service
import asyncio

# Setup Logging
logging.basicConfig(level=get_config("LOG_LEVEL", "INFO"))
logger = logging.getLogger("Pclonecopy")

app = FastAPI(title="Pclonecopy Institutional API", version="2.0.0")

# Global Middleware: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        get_config("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Modular Routers
app.include_router(auth.router)
app.include_router(intelligence.router)
app.include_router(trading.router)
app.include_router(billing.router)
app.include_router(ai.router)
app.include_router(social.router)

@app.on_event("startup")
async def startup_event():
    # Start the Alpha Stream broadcast loop in the background
    asyncio.create_task(alpha_stream_service.start_broadcasting())
    logger.info("Alpha Stream broadcast loop started.")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive, can handle client messages here if needed
            data = await websocket.receive_text()
            # Echo or handle incoming WS messages
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "2.0.0",
        "environment": "local" if get_config("IS_LOCAL") == "True" else "production"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}

@app.post("/debug/reset")
async def debug_reset():
    """Reset the mock database for E2E tests."""
    from backend.db import reset_mock_db
    reset_mock_db()
    return {"status": "reset_complete"}

@app.post("/debug/reload")
async def debug_reload():
    """Force reload of local DB from disk."""
    from backend.db import _load_mock_db
    _load_mock_db()
    return {"status": "reload_complete"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(get_config("PORT", 8001)))
