"""
TradingView Webhook to Telegram Bot
Main Flask application to receive webhooks from TradingView and send to Telegram
"""
from flask import Flask, request, jsonify
from telegram_bot import (
    send_message,
    format_buy_signal,
    format_sell_signal,
    format_tp1_hit,
    format_tp2_hit,
    format_tp3_hit,
    format_stop_loss_hit,
    format_position_closed
)
from config import WEBHOOK_PORT, DEBUG, get_config_status
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Check configuration status (without raising error)
from config import get_config_status
from telegram_bot import send_startup_message
import time

config_status = get_config_status()
if config_status["all_set"]:
    logger.info("Configuration validated successfully")
    # Send startup message after a short delay to ensure app is fully started
    def send_startup_delayed():
        time.sleep(2)  # Wait 2 seconds for app to fully start
        send_startup_message()
    
    # Send startup message in background
    import threading
    startup_thread = threading.Thread(target=send_startup_delayed, daemon=True)
    startup_thread.start()
else:
    logger.warning("⚠️ Configuration incomplete. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
    logger.warning(f"Telegram Bot Token: {'✓ Set' if config_status['telegram_bot_token'] else '✗ Missing'}")
    logger.warning(f"Telegram Chat ID: {'✓ Set' if config_status['telegram_chat_id'] else '✗ Missing'}")


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


@app.route('/webhook', methods=['POST'])
@app.route('/personal/<chat_id>/webhook', methods=['POST'])
def webhook(chat_id=None):
    """
    Main webhook endpoint to receive signals from TradingView
    
    Supports two formats:
    - /webhook (default, uses TELEGRAM_CHAT_ID from config)
    - /personal/<chat_id>/webhook (uses chat_id from URL)
    
    Expected JSON format:
    {
        "signal": "BUY" | "SELL" | "TP1_HIT" | "TP2_HIT" | "TP3_HIT" | "STOP_LOSS" | "CLOSE",
        "symbol": "BTCUSDT",
        "entry_price": 42850.50,
        "tp1": 43300.75,
        "tp2": 43750.25,
        "tp3": 44200.50,
        "stop_loss": 42150.00,
        "time": "2024-01-15 14:30",
        "timeframe": "15m",
        ...
    }
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            logger.warning("Received empty request")
            return jsonify({"error": "No data received"}), 400
        
        # Get signal type
        signal = data.get('signal', '').upper()
        
        logger.info(f"Received signal: {signal} for {data.get('symbol', 'N/A')}")
        
        # Validate configuration before processing
        config_status = get_config_status()
        if not config_status["all_set"]:
            logger.error("Cannot process webhook: Configuration incomplete")
            return jsonify({
                "status": "error",
                "message": "Configuration incomplete. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables."
            }), 500
        
        # Route to appropriate formatter based on signal type
        message = None
        
        if signal == 'BUY':
            message = format_buy_signal(data)
        elif signal == 'SELL':
            message = format_sell_signal(data)
        elif signal == 'TP1_HIT' or signal == 'TP1':
            message = format_tp1_hit(data)
        elif signal == 'TP2_HIT' or signal == 'TP2':
            message = format_tp2_hit(data)
        elif signal == 'TP3_HIT' or signal == 'TP3':
            message = format_tp3_hit(data)
        elif signal == 'STOP_LOSS' or signal == 'SL':
            message = format_stop_loss_hit(data)
        elif signal == 'CLOSE' or signal == 'POSITION_CLOSED':
            message = format_position_closed(data)
        else:
            logger.warning(f"Unknown signal type: {signal}")
            return jsonify({"error": f"Unknown signal type: {signal}"}), 400
        
        # Send message to Telegram (use chat_id from URL if provided)
        if message:
            success = send_message(message, chat_id=chat_id)
            if success:
                logger.info(f"Successfully sent {signal} signal to Telegram")
                return jsonify({
                    "status": "success",
                    "message": "Signal sent to Telegram"
                }), 200
            else:
                logger.error(f"Failed to send {signal} signal to Telegram")
                return jsonify({
                    "status": "error",
                    "message": "Failed to send message to Telegram"
                }), 500
        else:
            logger.error("Failed to format message")
            return jsonify({
                "status": "error",
                "message": "Failed to format message"
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Run the Flask app
    # In production, use gunicorn: gunicorn main:app
    app.run(
        host='0.0.0.0',
        port=WEBHOOK_PORT,
        debug=DEBUG
    )

