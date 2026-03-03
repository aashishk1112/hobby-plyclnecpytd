import httpx
import json
import hmac
import hashlib
import time

API_BASE = "http://localhost:8001"
WEBHOOK_SECRET = "razorpay_secret"

def test_signed_webhook():
    print("--- Testing Signed Razorpay Webhook ---")
    
    payload = {
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": f"order_{int(time.time())}",
                    "notes": {
                        "user_id": "local-test-user"
                    }
                }
            }
        }
    }
    
    body = json.dumps(payload)
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "X-Razorpay-Signature": signature,
        "Content-Type": "application/json"
    }
    
    print(f"Sending signed webhook to {API_BASE}/razorpay/webhook...")
    resp = httpx.post(f"{API_BASE}/razorpay/webhook", content=body, headers=headers)
    
    print(f"Response: {resp.status_code} - {resp.json()}")
    if resp.status_code == 200:
        print("✅ Webhook verified successfully!")
    else:
        print("❌ Webhook verification failed.")

def test_create_order():
    print("\n--- Testing Razorpay Order Creation ---")
    headers = {"Authorization": "Bearer mock_token"} # MOCK_AUTH=True will ignore this but it mimics real call
    resp = httpx.post(f"{API_BASE}/razorpay/create-order", headers=headers)
    print(f"Response: {resp.status_code} - {resp.json()}")
    if resp.status_code == 200:
        print("✅ Order created successfully!")
    else:
        print("❌ Order creation failed.")

if __name__ == "__main__":
    test_create_order()
    test_signed_webhook()
