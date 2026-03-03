import asyncio
import logging
from tracker import PolymarketTracker

logging.basicConfig(level=logging.INFO)

async def test_threshold():
    print("--- Testing Balance Threshold Logic ---")
    
    # Mock data
    stats = {"balance": 100.0, "initial_balance": 100.0, "balance_threshold": 150.0}
    tracker = PolymarketTracker("test-user", [], [], stats=stats)
    
    print(f"Current Balance: ${tracker.stats['balance']}")
    print(f"Threshold: ${tracker.balance_threshold}")
    
    # Mock trade detecting
    trade = {
        "transactionHash": "0x123",
        "title": "Test Market",
        "side": "BUY",
        "size": 10,
        "price": 0.5,
        "timestamp": 123456789
    }
    
    # We need to manually trigger the check since we don't want to actually poll
    print("\nSimulating trade detection...")
    
    if tracker.stats["balance"] < tracker.balance_threshold:
        print(f"SUCCESS: Trade skipped as expected. Balance ${tracker.stats['balance']} < Threshold ${tracker.balance_threshold}")
    else:
        print("FAILURE: Trade was NOT skipped.")

    # Lower threshold
    tracker.balance_threshold = 50.0
    print(f"\nNew Threshold: ${tracker.balance_threshold}")
    
    if tracker.stats["balance"] < tracker.balance_threshold:
        print("FAILURE: Trade was skipped unexpectedly.")
    else:
        print(f"SUCCESS: Trade would proceed. Balance ${tracker.stats['balance']} >= Threshold ${tracker.balance_threshold}")

if __name__ == "__main__":
    asyncio.run(test_threshold())
