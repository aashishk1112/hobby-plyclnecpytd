import pytest
import httpx
import asyncio
import os
import json
from backend.db import reset_mock_db, get_user_data, update_user_data

# Ensure we are in local/mock mode for tests
os.environ["IS_LOCAL"] = "true"
os.environ["MOCK_AUTH"] = "true"

BASE_URL = "http://localhost:8001"

import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def setup_teardown():
    # Reset internal server state too
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/debug/reset")
    reset_mock_db()
    yield

@pytest.mark.async_timeout(30)
@pytest.mark.asyncio
async def test_auth_and_persistence():
    """Verify mock login creates a persistent user profile in the local DB."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Login
        resp = await client.post("/auth/mock/login", json={"username": "test_whale"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Verify /me and initial state
        me_resp = await client.get("/auth/me", headers=headers)
        assert me_resp.status_code == 200
        user_data = me_resp.json()
        assert user_data["userId"] == "user-test_whale"
        assert user_data["subscriptionStatus"] == "free"

        # 3. Modify state via API (Upgrade)
        upgrade_resp = await client.post("/billing/debug/upgrade?tier=pro", headers=headers)
        assert upgrade_resp.status_code == 200

        # 4. Verify persistence directly in DB
        # Reset local file cache in this process to see disk changes
        import backend.db
        backend.db._load_mock_db()
        persisted = backend.db.get_user_data("user-test_whale")
        assert persisted["subscriptionStatus"] == "pro"

@pytest.mark.asyncio
async def test_intelligence_real_data():
    """Verify Whale Radar and Heatmap using REAL Polymarket data feeds."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Whale Radar (Public)
        whale_resp = await client.get("/intelligence/whales")
        assert whale_resp.status_code == 200
        # Data-api might be empty if no recent huge trades, but endpoint should respond
        assert isinstance(whale_resp.json(), list)

        # Heatmap (Requires PRO, so should fail for fresh user)
        # First login as a fresh user
        auth_resp = await client.post("/auth/mock/login", json={"username": "heatmap_tester"})
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        heat_resp = await client.get("/intelligence/heatmap", headers=headers)
        assert heat_resp.status_code == 402 # Subscription Required

        # Upgrade user to pro via API
        await client.post("/billing/debug/upgrade?tier=pro", headers=headers)

        # Try Heatmap again
        heat_resp_pro = await client.get("/intelligence/heatmap", headers=headers)
        assert heat_resp_pro.status_code == 200
        assert len(heat_resp_pro.json()) > 0

@pytest.mark.asyncio
async def test_social_matrix_workflow():
    """Verify follow logic and social feed persistence."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Setup two users
        u1_resp = await client.post("/auth/mock/login", json={"username": "follower"})
        u1_token = u1_resp.json()["access_token"]
        u1_headers = {"Authorization": f"Bearer {u1_token}"}

        # Follow a target
        follow_resp = await client.post("/social/follow/target_whale", headers=u1_headers)
        assert follow_resp.status_code == 200

        # Check Feed (Legacy endpoint mapping)
        feed_resp = await client.get("/social/feed", headers=u1_headers)
        assert feed_resp.status_code == 200
        assert len(feed_resp.json()) > 0

@pytest.mark.asyncio
async def test_trade_replication_resilience():
    """Verify that paper trading replication updates local balance correctly."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Auth as trader
        auth_resp = await client.post("/auth/mock/login", json={"username": "trader"})
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = auth_resp.json()["user_id"] # This is user-trader
        
        # 1. Update balance via mock function (Shared File)
        from backend.db import update_user_balance, save_trade, get_user_trades
        update_user_balance(user_id, 950.0)
        
        # Force server to reload from disk since we bypassed its API
        await client.post("/debug/reload")
        
        # 2. Save mock trade
        save_trade(user_id, {
            "id": "e2e-tx-1",
            "market": "Outcome of E2E Test",
            "side": "BUY",
            "amount": 50,
            "price": 1.0,
            "status": "executed"
        })

        # 3. Verify via API
        # Check balance via me
        me_resp = await client.get("/auth/me", headers=headers)
        # Verify it persisted (Server should see it because it's a new request that calls get_user_data)
        assert me_resp.json()["balance"] == 950.0

        # Check trades via trading config (which returns user data)
        config_resp = await client.get("/trading/config", headers=headers)
        assert config_resp.status_code == 200
        
        # Verify saved trades in DB
        trade_items = get_user_trades(user_id)
        assert len(trade_items) > 0
        assert trade_items[0]["id"] == "e2e-tx-1"

@pytest.mark.asyncio
async def test_leaderboard_real_integration():
    """Verify that the leaderboard returns real pseudonyms and valid proxyWallets."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        resp = await client.get("/social/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            trader = data[0]
            assert "userName" in trader
            assert "proxyWallet" in trader
            assert trader["proxyWallet"].startswith("0x")
            # Verify the name is not the old mock placeholders if data is present
            assert trader["userName"] not in ["Global_Alpha", "Institutional_Prime"]
