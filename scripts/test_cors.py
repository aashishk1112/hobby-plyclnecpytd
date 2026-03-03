import requests
import sys

def test_cors(url):
    print(f"Testing CORS for {url}...")
    try:
        # Preflight request
        headers = {
            "Origin": "https://d3ukbv7x6b8vr.cloudfront.net",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type"
        }
        resp = requests.options(url, headers=headers)
        print(f"Preflight Status: {resp.status_code}")
        print(f"Access-Control-Allow-Origin: {resp.headers.get('Access-Control-Allow-Origin')}")
        print(f"Access-Control-Allow-Methods: {resp.headers.get('Access-Control-Allow-Methods')}")
        print(f"Access-Control-Allow-Headers: {resp.headers.get('Access-Control-Allow-Headers')}")
        
        # Real request (without valid token, should return 401 but still have CORS headers)
        headers = {
            "Origin": "https://d3ukbv7x6b8vr.cloudfront.net",
            "Authorization": "Bearer invalid-token"
        }
        resp = requests.get(url, headers=headers)
        print(f"GET Status: {resp.status_code}")
        print(f"Access-Control-Allow-Origin: {resp.headers.get('Access-Control-Allow-Origin')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001/config"
    test_cors(test_url)
