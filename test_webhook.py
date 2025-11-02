"""
Test webhook directly
"""
import requests
import json

# رابط Webhook
webhook_url = "https://go-production.up.railway.app/personal/8169000394/webhook"

print("=" * 60)
print("Testing Webhook")
print("=" * 60)

# بيانات التنبيه
test_data = {
    "message": "Test Alert from Python Script",
    "ticker": "BTC/USDT",
    "price": "50000",
    "comment": "Testing webhook functionality - This is a test alert!"
}

print(f"\nSending POST request to: {webhook_url}")
print(f"Data: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(
        webhook_url,
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get('status') == 'success':
            print("\nSUCCESS! Alert sent successfully!")
            print("Check your Telegram - you should receive the message")
        else:
            print(f"\nERROR: {result.get('message', 'Unknown error')}")
    else:
        print(f"\nHTTP Error: {response.status_code}")
        
except requests.exceptions.RequestException as e:
    print(f"\nConnection Error: {e}")
    print("\nPossible issues:")
    print("   1. Project is not running on Railway")
    print("   2. Wrong URL - check Railway Dashboard -> Settings -> Domains")
    print("   3. Network connectivity issue")

print("\n" + "=" * 60)
