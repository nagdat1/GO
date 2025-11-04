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
from config import validate_config, WEBHOOK_PORT, DEBUG
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Validate configuration on startup
try:
    validate_config()
    logger.info("Configuration validated successfully")
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "TradingView Webhook to Telegram Bot is running"
    }), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Main webhook endpoint to receive signals from TradingView
    
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
        
        # Send message to Telegram
        if message:
            success = send_message(message)
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

