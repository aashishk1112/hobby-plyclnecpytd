import httpx
import json
import time

API_BASE = "http://localhost:8001"

def test_flow():
    print("--- Starting Subscription Flow Verification ---")
    
    # Using default local-test-user (no header required when MOCK_AUTH=True)
    headers = {}
    
    # 2. Add first two wallets (Success)
    print("\nAdding first two wallets...")
    ts = int(time.time())
    for i in range(1, 3):
        addr = f"0x{ts:08x}{i:032x}"
        resp = httpx.post(f"{API_BASE}/wallets/add?address={addr}", headers=headers)
        print(f"Add {addr}: {resp.status_code} - {resp.json()}")
        assert resp.status_code == 200

    # 3. Add third wallet (Expect 402 Limit Reached)
    print("\nAdding third wallet (expecting 402)...")
    addr3 = f"0x{ts:08x}{3:032x}"
    resp = httpx.post(f"{API_BASE}/wallets/add?address={addr3}", headers=headers)
    print(f"Add {addr3}: {resp.status_code} - {resp.json()}")
    assert resp.status_code == 402

    # 4. Add duplicate wallet (Expect 400 Duplicate)
    print("\nAdding duplicate wallet (expecting 400)...")
    addr_dup = f"0x{ts:08x}{1:032x}"
    resp = httpx.post(f"{API_BASE}/wallets/add?address={addr_dup}", headers=headers)
    print(f"Add {addr_dup}: {resp.status_code} - {resp.json()}")
    assert resp.status_code == 400

    # 5. Simulate Payment via Stripe Webhook
    print("\nSimulating successful payment via Stripe Webhook...")
    stripe_webhook_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "session_test_123",
                "client_reference_id": "local-test-user",
                "payment_status": "paid"
            }
        }
    }
    # Using the Stripe webhook endpoint
    headers_stripe = {"Stripe-Signature": "mock_signature"}
    resp = httpx.post(f"{API_BASE}/stripe/webhook", json=stripe_webhook_payload, headers=headers_stripe)
    print(f"Stripe Webhook simulation: {resp.status_code} - {resp.json()}")
    assert resp.status_code == 200

    # 6. Add third wallet again (Success)
    print("\nAdding third wallet again (expecting 200 after payment)...")
    resp = httpx.post(f"{API_BASE}/wallets/add?address={addr3}", headers=headers)
    print(f"Add {addr3}: {resp.status_code} - {resp.json()}")
    assert resp.status_code == 200

    print("\n--- Verification Completed Successfully ---")

if __name__ == "__main__":
    test_flow()
