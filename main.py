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
import re
from datetime import datetime
import hashlib
import threading

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
    signal = data.get('signal', '').upper()
    symbol = data.get('symbol', '')
    time_str = data.get('time', '')
    
    # Round time to nearest minute to group similar messages
    if time_str:
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            time_minute = dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        time_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Create key: signal_symbol_time_minute
    key = f"{signal}_{symbol}_{time_minute}"
    return key

def is_recent_duplicate(key: str) -> bool:
    """Check if same signal was sent recently (within 5 minutes)"""
    current_time = datetime.now()
    
    # Clean old entries (older than 5 minutes)
    expired_keys = []
    for k, v in recent_messages.items():
        if (current_time - v).total_seconds() > 300:  # 5 minutes
            expired_keys.append(k)
    for k in expired_keys:
        del recent_messages[k]
    
    # Check if this key exists
    if key in recent_messages:
        logger.info(f"Duplicate detected: {key} (sent {(current_time - recent_messages[key]).total_seconds():.0f}s ago)")
        return True
    
    # Store this key
    recent_messages[key] = current_time
    return False

def parse_tradingview_text_alert(text: str) -> dict:
    """
    Parse TradingView text alert message to extract signal information
    
    Example input:
    "nagdat (Trailing, Open/Close, No Filtering, 7, 45, 10, 2, 10, 50, 30, 20, 10): تم تنفيذ الأمر buy @ 25319.53 على ACEUSDT. المركز الجديدة للإستراتيجية هو 0"
    
    Returns:
        dict: Parsed data or None if cannot parse
    """
    try:
        logger.info(f"Parsing text alert: {text[:200]}")
        
        # Extract signal type (buy/sell)
        signal_match = re.search(r'تم تنفيذ الأمر\s+(buy|sell|BUY|SELL)', text, re.IGNORECASE)
        if not signal_match:
            signal_match = re.search(r'(buy|sell|BUY|SELL)', text, re.IGNORECASE)
        if not signal_match:
            return None
        
        signal = signal_match.group(1).upper()
        
        # Extract price - look for @ followed by number, then space and "على" or end
        # Pattern: @ followed by optional whitespace, number with decimals, then space and "على"
        # This ensures we get the price right before the symbol
        price_match = re.search(r'@\s*([0-9]+(?:\.[0-9]+)?)\s+على', text)
        if not price_match:
            # Try alternative: @ number, then space and any word (symbol)
            price_match = re.search(r'@\s*([0-9]+(?:\.[0-9]+)?)\s+([A-Z0-9]+)', text)
            if price_match:
                # Verify it's a reasonable price (not too large, typically < 1000000 for crypto)
                price_str = price_match.group(1)
                try:
                    price_test = float(price_str)
                    if price_test > 10000000:  # Too large, probably wrong
                        logger.warning(f"Price {price_test} seems too large, trying different pattern")
                        price_match = None
                except:
                    price_match = None
        
        if not price_match:
            # Last resort: just @ followed by number
            price_match = re.search(r'@\s*([0-9]+(?:\.[0-9]+)?)', text)
        
        if price_match:
            price_str = price_match.group(1)
            try:
                price = float(price_str)
                # Sanity check: if price is too large, it's probably wrong
                if price > 10000000:
                    logger.warning(f"Price {price} seems incorrect, checking alternative extraction")
                    # Try to find a more reasonable price
                    # Look for numbers that are more reasonable (less than 1 million)
                    alt_match = re.findall(r'([0-9]+(?:\.[0-9]+)?)', text)
                    for num_str in alt_match:
                        try:
                            num = float(num_str)
                            if 0.001 < num < 1000000:  # Reasonable price range
                                price = num
                                logger.info(f"Using alternative price: {price}")
                                break
                        except:
                            continue
            except ValueError:
                logger.error(f"Could not convert price '{price_str}' to float")
                price = 0
        else:
            logger.error("Could not find price in text")
            price = 0
        
        # Extract symbol - look for "على" followed by symbol
        symbol_match = re.search(r'على\s+([A-Z0-9]+)', text)
        if not symbol_match:
            # Try alternative pattern
            symbol_match = re.search(r'on\s+([A-Z0-9]+)', text, re.IGNORECASE)
        if not symbol_match:
            # Try to find symbol at the end or after price
            symbol_match = re.search(r'@\s*[\d.]+.*?([A-Z0-9]{4,})', text)
        
        symbol = symbol_match.group(1) if symbol_match else "UNKNOWN"
        
        # Get current time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Parsed: signal={signal}, symbol={symbol}, price={price}")
        
        # For text alerts, we don't have TP/SL info, so we'll use basic format
        # But we should NOT send TP/SL estimates for text alerts - they're not real
        result = {
            "signal": signal,
            "symbol": symbol,
            "entry_price": price,
            "price": price,  # For CLOSE and SL signals
            "time": current_time,
            "timeframe": "N/A",
            # Don't add fake TP/SL - they will be calculated incorrectly
            # Only include if we have real data
        }
        
        logger.info(f"Parsed TradingView text alert: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error parsing TradingView text alert: {e}", exc_info=True)
        return None

# Check configuration status (without raising error)
from config import get_config_status
from telegram_bot import send_startup_message
import time
import os

# Flag to track if startup message was sent (prevents duplicate messages)
_startup_message_sent = False
_startup_message_lock = threading.Lock()

config_status = get_config_status()
if config_status["all_set"]:
    logger.info("Configuration validated successfully")
    
    # Use a file-based lock to prevent duplicate messages across workers
    # This ensures only one startup message is sent even with multiple workers
    startup_lock_file = '/tmp/startup_message_sent.lock'
    
    def send_startup_delayed():
        global _startup_message_sent
        
        # Check file lock first
        if os.path.exists(startup_lock_file):
            try:
                # Check if file is recent (less than 60 seconds old)
                file_age = time.time() - os.path.getmtime(startup_lock_file)
                if file_age < 60:
                    logger.info("Startup message already sent recently, skipping")
                    return
            except:
                pass
        
        time.sleep(3)  # Wait 3 seconds for app to fully start
        
        with _startup_message_lock:
            if not _startup_message_sent:
                try:
                    # Create lock file
                    with open(startup_lock_file, 'w') as f:
                        f.write(str(time.time()))
                    
                    if send_startup_message():
                        _startup_message_sent = True
                        logger.info("Startup message sent successfully")
                    else:
                        # Remove lock file if sending failed
                        if os.path.exists(startup_lock_file):
                            os.remove(startup_lock_file)
                except Exception as e:
                    logger.error(f"Error sending startup message: {e}")
                    if os.path.exists(startup_lock_file):
                        os.remove(startup_lock_file)
    
    # Send startup message in background
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


@app.route('/webhook', methods=['POST', 'GET'])
@app.route('/personal/<chat_id>/webhook', methods=['POST', 'GET'])
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
    # Handle GET requests (for testing)
    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "message": "Webhook endpoint is active",
            "chat_id_from_url": chat_id,
            "method": "Use POST to send signals"
        }), 200
    
    try:
        # Log request details for debugging
        logger.info(f"=== Webhook Request Received ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"URL: {request.url}")
        logger.info(f"Chat ID from URL: {chat_id}")
        logger.info(f"Content-Type: {request.headers.get('Content-Type', 'Not specified')}")
        
        data = None
        
        # Try to get data - TradingView sends as text/plain, not application/json
        # Method 1: Try to get raw data first (for text/plain content type)
        # TradingView now sends JSON directly from alert() function
        try:
            raw_data = request.get_data(as_text=True)
            logger.info(f"Raw data received (first 200 chars): {raw_data[:200] if raw_data else 'Empty'}")
            if raw_data:
                import json
                # Strip whitespace before/after JSON (TradingView might add extra spaces)
                raw_data_cleaned = raw_data.strip()
                # Try to parse JSON
                data = json.loads(raw_data_cleaned)
                logger.info("✅ Successfully parsed JSON from raw data")
                logger.info(f"Parsed JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse raw data as JSON: {e}")
            logger.info(f"Raw data preview: {raw_data[:100] if raw_data else 'Empty'}")
            # Try to parse as form data
            try:
                data = request.form.to_dict()
                if data:
                    logger.info("Parsed as form data instead")
            except:
                pass
        except Exception as e:
            logger.warning(f"Error reading raw data: {e}")
        
        # Method 2: Try to get JSON (if Content-Type is application/json)
        if not data:
            try:
                if request.is_json:
                    data = request.get_json(force=False)
                    logger.info("Successfully parsed JSON from request.get_json()")
            except Exception as e:
                logger.warning(f"Failed to get JSON: {e}")
        
        # Method 3: Try form data
        if not data:
            try:
                data = request.form.to_dict()
                if data:
                    logger.info("Parsed as form data")
            except Exception as e:
                logger.warning(f"Failed to get form data: {e}")
        
        # If we still don't have data, try to parse as TradingView text message
        if not data:
            try:
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    # Try to parse TradingView text alert message
                    parsed_data = parse_tradingview_text_alert(raw_data)
                    if parsed_data:
                        data = parsed_data
                        logger.info("Successfully parsed TradingView text alert")
                    else:
                        logger.warning(f"Could not parse text message: {raw_data[:100]}")
            except Exception as e:
                logger.warning(f"Error parsing text alert: {e}")
        
        if not data:
            logger.warning("Received empty request - no JSON, form, or raw data")
            raw_data_preview = request.get_data(as_text=True)[:200] if request.get_data() else "No data"
            return jsonify({
                "error": "No data received",
                "message": "Please send JSON data in the request body or use TradingView Alert with JSON format",
                "raw_data_preview": raw_data_preview,
                "tip": "In TradingView Alert, use JSON format in the message field. See TRADINGVIEW_ALERTS_SETUP.md"
            }), 400
        
        logger.info(f"Received data: {data}")
        
        # Check for duplicate messages (same signal, symbol, within same minute)
        message_key = get_message_key(data)
        if is_recent_duplicate(message_key):
            logger.warning(f"⚠️ Duplicate message ignored: {message_key}")
            return jsonify({
                "status": "ignored",
                "message": "Duplicate message - same signal already sent recently",
                "key": message_key
            }), 200
        
        logger.info(f"✅ New message: {message_key}")
        
        # Get signal type
        signal = data.get('signal', '')
        if isinstance(signal, str):
            signal = signal.upper()
        
        logger.info(f"Signal type: {signal}")
        logger.info(f"Symbol: {data.get('symbol', 'N/A')}")
        
        # Validate configuration before processing
        config_status = get_config_status()
        logger.info(f"Config status: {config_status}")
        
        # Determine target chat_id
        target_chat_id = chat_id
        if not target_chat_id and config_status.get('telegram_chat_id'):
            from config import TELEGRAM_CHAT_ID
            target_chat_id = TELEGRAM_CHAT_ID
        logger.info(f"Target chat_id: {target_chat_id}")
        
        if not config_status["telegram_bot_token"]:
            logger.error("TELEGRAM_BOT_TOKEN is not set")
            return jsonify({
                "status": "error",
                "message": "TELEGRAM_BOT_TOKEN is not configured"
            }), 500
        
        if not target_chat_id:
            logger.error("No chat_id available (neither from URL nor config)")
            return jsonify({
                "status": "error",
                "message": "No chat_id available. Please provide chat_id in URL or set TELEGRAM_CHAT_ID"
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
            logger.info(f"Formatted message length: {len(message)} characters")
            logger.info(f"Sending message to chat_id: {target_chat_id}")
            success = send_message(message, chat_id=target_chat_id)
            if success:
                logger.info(f"✅ Successfully sent {signal} signal to Telegram")
                return jsonify({
                    "status": "success",
                    "message": "Signal sent to Telegram",
                    "signal": signal,
                    "chat_id": target_chat_id
                }), 200
            else:
                logger.error(f"❌ Failed to send {signal} signal to Telegram")
                return jsonify({
                    "status": "error",
                    "message": "Failed to send message to Telegram. Check logs for details.",
                    "signal": signal
                }), 500
        else:
            logger.error("Failed to format message - message is None or empty")
            return jsonify({
                "status": "error",
                "message": "Failed to format message",
                "signal": signal
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
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

