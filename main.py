"""
TradingView Webhook to Telegram Bot - نسخة مبسطة
"""
from flask import Flask, request, jsonify
from telegram_bot import (
    send_message,
    format_buy_signal,
    format_sell_signal,
    format_buy_reverse_signal,
    format_sell_reverse_signal,
    format_tp1_hit,
    format_tp2_hit,
    format_tp3_hit,
    format_stop_loss_hit
)
from config import WEBHOOK_PORT, DEBUG, get_config_status
import logging
import json
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Simple cache to prevent duplicate messages (last 5 minutes)
recent_messages = {}

def get_message_key(data: dict) -> str:
    """Generate a unique key for a message to detect duplicates"""
    signal = data.get('signal', '')
    symbol = data.get('symbol', '')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"{signal}_{symbol}_{timestamp}"

def is_recent_duplicate(message_key: str) -> bool:
    """Check if message was sent recently (within last 5 minutes)"""
    current_time = datetime.now()
    if message_key in recent_messages:
        last_sent = recent_messages[message_key]
        time_diff = (current_time - last_sent).total_seconds()
        if time_diff < 300:  # 5 minutes
            return True
    recent_messages[message_key] = current_time
    return False

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    config_status = get_config_status()
    return jsonify({
        "status": "ok",
        "message": "TradingView Webhook to Telegram Bot is running",
        "config": {
            "telegram_bot_token": "✓ Set" if config_status['telegram_bot_token'] else "✗ Missing",
            "telegram_chat_id": "✓ Set" if config_status['telegram_chat_id'] else "✗ Missing"
        }
    }), 200

@app.route('/webhook', methods=['POST', 'GET'])
@app.route('/personal/<chat_id>/webhook', methods=['POST', 'GET'])
def webhook(chat_id=None):
    """
    Main webhook endpoint - نسخة مبسطة
    يتوقع JSON بسيط مع signal واضح
    """
    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "message": "Webhook endpoint is active",
            "chat_id_from_url": chat_id
        }), 200
    
    try:
        # Get JSON data
        data = None
        try:
            if request.is_json:
                data = request.get_json(force=False)
            else:
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    data = json.loads(raw_data)
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return jsonify({"error": "Invalid JSON"}), 400
        
        if not data or not isinstance(data, dict):
            return jsonify({"error": "No valid data received"}), 400
        
        # Get signal type (required)
        signal = data.get('signal', '').upper()
        if not signal:
            return jsonify({"error": "Signal type is required"}), 400
        
        # Check for duplicates
        message_key = get_message_key(data)
        if is_recent_duplicate(message_key):
            logger.warning(f"⚠️ Duplicate message ignored: {message_key}")
            return jsonify({"status": "ignored", "message": "Duplicate"}), 200
        
        logger.info(f"✅ New signal: {signal} for {data.get('symbol', 'N/A')}")
        
        # Get target chat_id
        target_chat_id = chat_id
        if not target_chat_id:
            from config import TELEGRAM_CHAT_ID
            target_chat_id = TELEGRAM_CHAT_ID
        
        if not target_chat_id:
            return jsonify({"error": "No chat_id available"}), 500
        
        # Route to appropriate formatter
        message = None
        
        if signal == 'BUY' or signal == 'LONG':
            message = format_buy_signal(data)
        elif signal == 'SELL' or signal == 'SHORT':
            message = format_sell_signal(data)
        elif signal == 'BUY_REVERSE' or signal == 'LONG_REVERSE':
            message = format_buy_reverse_signal(data)
        elif signal == 'SELL_REVERSE' or signal == 'SHORT_REVERSE':
            message = format_sell_reverse_signal(data)
        elif signal == 'TP1_HIT' or signal == 'TP1':
            message = format_tp1_hit(data)
        elif signal == 'TP2_HIT' or signal == 'TP2':
            message = format_tp2_hit(data)
        elif signal == 'TP3_HIT' or signal == 'TP3':
            message = format_tp3_hit(data)
        elif signal == 'STOP_LOSS' or signal == 'SL':
            message = format_stop_loss_hit(data)
        else:
            return jsonify({"error": f"Unknown signal type: {signal}"}), 400
        
        # Send message
        if message:
            success = send_message(message, target_chat_id)
            if success:
                return jsonify({"status": "success", "signal": signal}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send to Telegram"}), 500
        else:
            return jsonify({"status": "error", "message": "Failed to format message"}), 500
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Startup message
from config import get_config_status
from telegram_bot import send_startup_message
import time
import os

config_status = get_config_status()
if config_status["all_set"]:
    logger.info("Configuration validated successfully")
    time.sleep(2)
    send_startup_message()
else:
    logger.warning("⚠️ Configuration incomplete")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=WEBHOOK_PORT, debug=DEBUG)
