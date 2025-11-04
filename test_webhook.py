"""
Test script for webhook endpoint
Usage: python test_webhook.py
"""
import requests
import json

# Webhook URL
WEBHOOK_URL = "https://go-production-e51a.up.railway.app/personal/8169000394/webhook"

# Test data
test_data = {
    "signal": "BUY",
    "symbol": "BTCUSDT",
    "entry_price": 42850.50,
    "tp1": 43300.75,
    "tp2": 43750.25,
    "tp3": 44200.50,
    "stop_loss": 42150.00,
    "time": "2024-01-15 14:30",
    "timeframe": "15m"
}

def test_webhook():
    """Test webhook endpoint"""
    print("🧪 Testing Webhook Endpoint...")
    print(f"URL: {WEBHOOK_URL}")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    print("-" * 50)
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test successful! Check your Telegram.")
        else:
            print("❌ Test failed!")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_webhook()

