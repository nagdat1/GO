"""
TradingView Webhook to Telegram Bot
Main Flask application to receive webhooks from TradingView and send to Telegram
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
    format_stop_loss_hit,
    format_position_closed
)
from config import WEBHOOK_PORT, DEBUG, get_config_status
import logging
import re
import json
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

# ═══════════════════════════════════════════════════════════════════════════
# 🧠 نظام الذاكرة لتتبع الصفقات المفتوحة وتحديد الإشارات العكسية
# ═══════════════════════════════════════════════════════════════════════════
# Memory system to track open positions and detect reverse signals
# Format: {symbol: {'signal_type': 'BUY'|'SELL', 'entry_price': float, 'tp1': float, 'tp2': float, 'tp3': float, 'stop_loss': float}}
open_positions = {}
_open_positions_lock = threading.Lock()

def get_open_position(symbol: str) -> dict:
    """
    Get the current open position data for a symbol
    Returns: dict with 'signal_type', 'entry_price', 'tp1', 'tp2', 'tp3', 'stop_loss' or None
    """
    with _open_positions_lock:
        return open_positions.get(symbol, None)

def set_open_position(symbol: str, signal_type: str, entry_price: float = None, tp1: float = None, tp2: float = None, tp3: float = None, stop_loss: float = None):
    """
    Set/open a new position for a symbol with TP/SL data
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        signal_type: 'BUY' or 'SELL'
        entry_price: Entry price
        tp1, tp2, tp3: Take profit levels
        stop_loss: Stop loss level
    """
    if signal_type not in ['BUY', 'SELL']:
        logger.warning(f"⚠️ Invalid signal type for position: {signal_type} (expected BUY or SELL)")
        return
    
    with _open_positions_lock:
        old_position = open_positions.get(symbol, None)
        open_positions[symbol] = {
            'signal_type': signal_type,
            'entry_price': entry_price,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'stop_loss': stop_loss
        }
        if old_position:
            logger.info(f"📝 Updated position for {symbol}: {old_position.get('signal_type')} → {signal_type}")
        else:
            logger.info(f"📝 Opened new position for {symbol}: {signal_type}")
        
        if entry_price or tp1 or stop_loss:
            logger.info(f"💾 Saved TP/SL data: entry={entry_price}, tp1={tp1}, tp2={tp2}, tp3={tp3}, sl={stop_loss}")

def clear_open_position(symbol: str):
    """
    Close/clear position for a symbol (when TP3 or STOP_LOSS is hit)
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
    """
    with _open_positions_lock:
        if symbol in open_positions:
            old_position = open_positions[symbol]
            old_signal_type = old_position.get('signal_type') if isinstance(old_position, dict) else old_position
            del open_positions[symbol]
            logger.info(f"🗑️ Closed position for {symbol}: {old_signal_type} (removed from memory)")
        else:
            logger.debug(f"⚠️ Attempted to clear position for {symbol} but no position found")

def detect_reverse_signal(symbol: str, incoming_signal: str) -> str:
    """
    Detect if an incoming signal is a REVERSE signal based on open position
    Args:
        symbol: Trading symbol
        incoming_signal: 'BUY' or 'SELL'
    Returns:
        'BUY_REVERSE', 'SELL_REVERSE', or original signal if not a reverse
    """
    if incoming_signal not in ['BUY', 'SELL']:
        # Not an entry signal, return as-is
        return incoming_signal
    
    current_position_data = get_open_position(symbol)
    
    if current_position_data is None:
        # No open position - this is a normal entry signal
        logger.info(f"✅ Normal {incoming_signal} signal for {symbol} (no open position)")
        return incoming_signal
    
    current_position = current_position_data.get('signal_type') if isinstance(current_position_data, dict) else current_position_data
    
    # Check if this is a reverse signal
    if current_position == 'BUY' and incoming_signal == 'SELL':
        # Had BUY position, new SELL signal → SELL_REVERSE
        logger.info(f"🔄 REVERSE detected for {symbol}: {current_position} → {incoming_signal} → SELL_REVERSE")
        return 'SELL_REVERSE'
    elif current_position == 'SELL' and incoming_signal == 'BUY':
        # Had SELL position, new BUY signal → BUY_REVERSE
        logger.info(f"🔄 REVERSE detected for {symbol}: {current_position} → {incoming_signal} → BUY_REVERSE")
        return 'BUY_REVERSE'
    else:
        # Same direction (BUY→BUY or SELL→SELL) - this shouldn't happen normally
        # but we'll treat it as a normal signal (maybe position was already closed)
        logger.warning(f"⚠️ Same direction signal for {symbol}: {current_position} → {incoming_signal} (treating as normal)")
        return incoming_signal

def detect_tp_sl_from_memory(symbol: str, current_price: float) -> str:
    """
    Detect if current price has hit TP or SL based on saved position data
    Args:
        symbol: Trading symbol
        current_price: Current price to check
    Returns:
        'TP1_HIT', 'TP2_HIT', 'TP3_HIT', 'STOP_LOSS', or None
    """
    position_data = get_open_position(symbol)
    if not position_data or not isinstance(position_data, dict):
        return None
    
    entry_price = position_data.get('entry_price')
    if not entry_price or entry_price <= 0:
        return None
    
    tp1 = position_data.get('tp1')
    tp2 = position_data.get('tp2')
    tp3 = position_data.get('tp3')
    stop_loss = position_data.get('stop_loss')
    
    # Calculate tolerance (0.5% of price movement)
    tolerance = abs(current_price - entry_price) * 0.005 if entry_price > 0 else current_price * 0.005
    
    # Check TP3 first (farthest)
    if tp3 and abs(current_price - tp3) <= tolerance:
        logger.info(f"🎯 Auto-detected TP3_HIT for {symbol}: price {current_price} reached TP3 {tp3}")
        return 'TP3_HIT'
    # Then TP2
    elif tp2 and abs(current_price - tp2) <= tolerance:
        logger.info(f"🎯 Auto-detected TP2_HIT for {symbol}: price {current_price} reached TP2 {tp2}")
        return 'TP2_HIT'
    # Then TP1
    elif tp1 and abs(current_price - tp1) <= tolerance:
        logger.info(f"🎯 Auto-detected TP1_HIT for {symbol}: price {current_price} reached TP1 {tp1}")
        return 'TP1_HIT'
    # Then Stop Loss
    elif stop_loss and abs(current_price - stop_loss) <= tolerance:
        logger.info(f"🛑 Auto-detected STOP_LOSS for {symbol}: price {current_price} hit SL {stop_loss}")
        return 'STOP_LOSS'
    
    return None

def get_message_key(data: dict) -> str:
    """Generate a unique key for a message to detect duplicates"""
    signal = data.get('signal', '')
    # Handle both string and int signal types
    if isinstance(signal, int):
        signal = str(signal)
    elif isinstance(signal, str):
        signal = signal.upper()
    else:
        signal = str(signal) if signal else ''
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
    "SIGNAL:BUY|SYMBOL:BTCUSDT|PRICE:50000|TIME:2024-01-15 14:30|TF:15m"
    
    Returns:
        dict: Parsed data or None if cannot parse
    """
    try:
        logger.info(f"Parsing text alert: {text[:200]}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🔍 Parse Smart Central Alert format: "SIGNAL_CODE:1|SYMBOL:BTCUSDT|PRICE:50000|..."
        # 🔍 Parse Central Alert format: "SIGNAL:BUY|SYMBOL:BTCUSDT|PRICE:50000|..."
        # ═══════════════════════════════════════════════════════════════════════
        
        # Signal Type Code mapping (from Pine Script indicator)
        # 1 = BUY, 2 = SELL, 3 = BUY_REVERSE, 4 = SELL_REVERSE, 5 = TP1, 6 = TP2, 7 = TP3, 8 = STOP_LOSS
        signal_code_map = {
            '1': 'BUY',
            '2': 'SELL',
            '3': 'BUY_REVERSE',
            '4': 'SELL_REVERSE',
            '5': 'TP1_HIT',
            '6': 'TP2_HIT',
            '7': 'TP3_HIT',
            '8': 'STOP_LOSS'
        }
        
        if ('SIGNAL_CODE:' in text or 'SIGNAL:' in text) and '|' in text:
            logger.info("🔍 Detected Smart Central Alert format (SIGNAL_CODE:...|...|...) or Central Alert format (SIGNAL:...|...|...)")
            result = {}
            
            # ═══════════════════════════════════════════════════════════════════════
            # 🔍 أولاً: حاول استخراج JSON من النص (إذا كان موجوداً)
            # ═══════════════════════════════════════════════════════════════════════
            # البحث عن JSON في النص (يبدأ بـ { وينتهي بـ })
            json_start = text.find('{')
            if json_start != -1:
                brace_count = 0
                json_end = -1
                for i in range(json_start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > json_start:
                    json_str = text[json_start:json_end]
                    # استبدال {{plot_22}} بـ null في JSON
                    json_str_cleaned = re.sub(r'\{\{plot[^}]+\}\}', 'null', json_str)
                    try:
                        json_data = json.loads(json_str_cleaned)
                        if isinstance(json_data, dict):
                            # استخراج البيانات من JSON
                            result.update(json_data)
                            logger.info(f"✅ Extracted data from JSON in text: {list(json_data.keys())}")
                    except:
                        pass
            
            # ═══════════════════════════════════════════════════════════════════════
            # 🔍 ثانياً: استخرج البيانات من alertcondition message (SIGNAL_CODE:...|...)
            # ═══════════════════════════════════════════════════════════════════════
            # Parse pipe-separated values
            # نبحث عن الجزء قبل JSON (alertcondition message)
            text_before_json = text[:json_start] if json_start != -1 else text
            
            parts = text_before_json.split('|')
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    
                    if key == 'SIGNAL_CODE':
                        # Handle case where value is {{plot_22}} or {{plot("Signal Type Code")}}
                        # Try to extract signal code from JSON if available
                        if '{{plot' in value:
                            logger.warning(f"⚠️ SIGNAL_CODE contains plot placeholder: {value}")
                            # Try to extract from JSON in the same message
                            json_match_in_text = re.search(r'"signal"\s*:\s*(\d+)', text)
                            if json_match_in_text:
                                value = json_match_in_text.group(1)
                                logger.info(f"✅ Extracted signal code from JSON: {value}")
                            else:
                                # If not found, try to find SIGNAL_CODE with actual number elsewhere
                                signal_code_direct = re.search(r'SIGNAL_CODE\s*:\s*(\d+)', text)
                                if signal_code_direct:
                                    value = signal_code_direct.group(1)
                                    logger.info(f"✅ Found SIGNAL_CODE with actual number: {value}")
                                else:
                                    logger.warning(f"⚠️ Cannot extract signal code - will try to detect from context or memory")
                                    value = None  # Will be detected from context or memory later
                        
                        if value and value not in ['{{plot_22}}', '{{plot("Signal Type Code")}}']:
                            # Convert signal code to signal name
                            signal_name = signal_code_map.get(value, 'UNKNOWN')
                            result['signal'] = signal_name
                            logger.info(f"📊 Converted Signal Code {value} → {signal_name}")
                    elif key == 'SIGNAL':
                        # Direct signal name (for backward compatibility)
                        result['signal'] = value.upper()
                    elif key == 'SYMBOL':
                        result['symbol'] = value
                    elif key == 'PRICE':
                        try:
                            price_val = float(value)
                            result['price'] = price_val
                            if 'entry_price' not in result:
                                result['entry_price'] = price_val
                        except:
                            pass
                    elif key == 'TIME':
                        result['time'] = value
                    elif key == 'TF':
                        result['timeframe'] = value
            
            # إذا كان signal = null أو 0، احذفه (سيتم تحديده من السياق أو الذاكرة)
            if result.get('signal') in [None, 'null', 0, '0']:
                logger.info("⚠️ Signal is null/0 - will be detected from context or memory")
                result.pop('signal', None)
            
            # إذا كانت هناك بيانات (symbol أو price)، نعيد النتيجة
            if result and (result.get('symbol') or result.get('price') or result.get('entry_price')):
                logger.info(f"✅ Parsed Smart Central Alert: symbol={result.get('symbol')}, price={result.get('price') or result.get('entry_price')}, signal={result.get('signal', 'will be detected')}")
                return result
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🔍 Parse traditional text format
        # ═══════════════════════════════════════════════════════════════════════
        
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
                extracted_value = float(price_str)
                
                # ⚠️ CRITICAL: Check if extracted value is Position Size (too large) instead of Price
                # Position Size typically > 100,000 for crypto, while prices are usually < 100,000
                # Most crypto prices are between 0.000001 and 100,000
                # If it's too large (> 100,000), it's likely Position Size, not Price
                if extracted_value > 100000:
                    logger.warning(f"⚠️ Extracted value {extracted_value:,.2f} is too large - likely Position Size, not Price!")
                    logger.warning(f"⚠️ Position Size = حجم المركز (Volume) ❌")
                    logger.warning(f"⚠️ Price = سعر العملة الحقيقي (Real Price) ✅")
                    logger.warning(f"⚠️ Cannot extract real price from text alert. Price will be set to 0.")
                    logger.warning(f"⚠️ SOLUTION: Use JSON format in TradingView Alert Message field to get real price.")
                    
                    # Set price to 0 to indicate we couldn't get real price
                    price = 0
                    
                    # Try to find a reasonable number in the text (might be timeframe or other value)
                    # But don't use it as price - it's not reliable
                    all_numbers = re.findall(r'([0-9]+(?:\.[0-9]+)?)', text)
                    reasonable_numbers = []
                    for num_str in all_numbers:
                        try:
                            num = float(num_str)
                            # Look for numbers that could be prices (0.000001 to 100,000)
                            # Exclude very small numbers that are likely percentages or other values
                            if 0.0001 <= num <= 100000:
                                reasonable_numbers.append(num)
                        except:
                            continue
                    
                    if reasonable_numbers:
                        logger.info(f"Found reasonable numbers in text: {reasonable_numbers[:5]} (but not using as price - unreliable from text)")
                else:
                    # Value seems reasonable for a price
                    price = extracted_value
                    logger.info(f"✅ Extracted price: {price}")
                    
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
        
        # ⚠️ IMPORTANT: If price is 0, it means we couldn't extract real price
        # (likely because text contained Position Size instead of Price)
        if price == 0:
            logger.error("❌ Cannot calculate TP/SL - real price not available from text alert")
            logger.error("❌ Text alert likely contains Position Size instead of Price")
            logger.error("❌ SOLUTION: Use JSON format in TradingView Alert Message field")
            tp1 = tp2 = tp3 = stop_loss = None
        # Calculate estimated TP/SL based on ATR-like logic (similar to Pine Script)
        # Using the same factors as the Pine Script: profitFactor = 2.5
        # Note: This is an ESTIMATE - real TP/SL comes from JSON alerts only
        # For accurate TP/SL, use JSON format in TradingView Alert Message field
        elif price > 0 and signal in ['BUY', 'SELL']:
            # Estimate ATR as percentage of price (adaptive based on price range)
            # For very high prices (>1M), use smaller percentage
            if price > 1000000:
                atr_percent = 0.005  # 0.5% for very high prices
            elif price > 10000:
                atr_percent = 0.01   # 1% for medium prices
            else:
                atr_percent = 0.02   # 2% for lower prices
            
            estimated_atr = price * atr_percent
            profit_factor = 2.5
            
            if signal == 'BUY':
                # For BUY: TP above entry, SL below entry
                tp1 = price + (1 * profit_factor * estimated_atr)
                tp2 = price + (2 * profit_factor * estimated_atr)
                tp3 = price + (3 * profit_factor * estimated_atr)
                stop_loss = price - (1 * profit_factor * estimated_atr)
            else:  # SELL
                # For SELL: TP below entry (price goes down), SL above entry
                tp1 = price - (1 * profit_factor * estimated_atr)
                tp2 = price - (2 * profit_factor * estimated_atr)
                tp3 = price - (3 * profit_factor * estimated_atr)
                stop_loss = price + (1 * profit_factor * estimated_atr)
        else:
            tp1 = tp2 = tp3 = stop_loss = None
        
        # Extract timeframe from text if possible (look for common patterns)
        timeframe = "N/A"
        timeframe_match = re.search(r'(\d+[mhdw])', text, re.IGNORECASE)
        if timeframe_match:
            timeframe = timeframe_match.group(1)
        
        result = {
            "signal": signal,
            "symbol": symbol,
            "entry_price": price,
            "price": price,  # For CLOSE and SL signals
            "time": current_time,
            "timeframe": timeframe,
        }
        
        # Add TP/SL if calculated
        if tp1 is not None:
            result["tp1"] = tp1
            result["tp2"] = tp2
            result["tp3"] = tp3
            result["stop_loss"] = stop_loss
            logger.info(f"Calculated estimated TP/SL: TP1={tp1:.2f}, TP2={tp2:.2f}, TP3={tp3:.2f}, SL={stop_loss:.2f}")
        
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
        logger.info("=" * 80)
        logger.info("=== WEBHOOK REQUEST RECEIVED ===")
        logger.info("=" * 80)
        logger.info(f"Method: {request.method}")
        logger.info(f"URL: {request.url}")
        logger.info(f"Chat ID from URL: {chat_id}")
        logger.info(f"Content-Type: {request.headers.get('Content-Type', 'Not specified')}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info("-" * 80)
        
        data = None
        
        # Try to get data - TradingView sends as text/plain, not application/json
        # Method 1: Try to get raw data first (for text/plain content type)
        # TradingView may send JSON mixed with default strategy message
        try:
            raw_data = request.get_data(as_text=True)
            logger.info("=" * 80)
            logger.info("=== RAW DATA RECEIVED ===")
            logger.info("=" * 80)
            if raw_data:
                logger.info(f"Raw Data Length: {len(raw_data)} characters")
                logger.info(f"Raw Data (Full):")
                logger.info("-" * 80)
                logger.info(raw_data)
                logger.info("-" * 80)
            else:
                logger.info("Raw Data: Empty")
            if raw_data:
                # Strip whitespace before/after JSON (TradingView might add extra spaces)
                raw_data_cleaned = raw_data.strip()
                
                # ═══════════════════════════════════════════════════════════════════════
                # 🔧 استخراج JSON كامل مباشرة (بدون regex أولاً)
                # ═══════════════════════════════════════════════════════════════════════
                # المشكلة: regex يجد فقط جزء صغير (مثل {"signal":{{plot_22}})
                # الحل: نستخدم منطق استخراج JSON الكامل مباشرة
                json_str = None
                json_start = raw_data_cleaned.find('{')
                if json_start != -1:
                    # ابحث عن آخر } المتطابق (بحساب الأقواس)
                    brace_count = 0
                    json_end = -1
                    for i in range(json_start, len(raw_data_cleaned)):
                        if raw_data_cleaned[i] == '{':
                            brace_count += 1
                        elif raw_data_cleaned[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > json_start:
                        json_str = raw_data_cleaned[json_start:json_end]
                        # التحقق من أن JSON يحتوي على "signal"
                        if '"signal"' in json_str:
                            logger.info(f"✅ Extracted complete JSON from text (length: {len(json_str)} chars)")
                        else:
                            logger.warning(f"⚠️ Extracted JSON does not contain 'signal' key")
                            json_str = None
                    else:
                        logger.warning(f"⚠️ Could not find complete JSON - brace_count={brace_count}, json_start={json_start}")
                else:
                    logger.warning(f"⚠️ No opening brace found in text")
                
                # إذا فشل الاستخراج المباشر، جرب regex
                if not json_str:
                    # Try to find JSON object with "signal" key using regex
                    json_match = json_re.search(r'\{[^{}]*"signal"[^{}]*\}', raw_data_cleaned, json_re.DOTALL)
                    if not json_match:
                        # Try to find complete JSON object by matching braces
                        brace_start = raw_data_cleaned.rfind('{')
                        if brace_start != -1:
                            brace_count = 0
                            for i in range(brace_start, len(raw_data_cleaned)):
                                if raw_data_cleaned[i] == '{':
                                    brace_count += 1
                                elif raw_data_cleaned[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        potential_json = raw_data_cleaned[brace_start:i+1]
                                        if '"signal"' in potential_json:
                                            json_str = potential_json
                                            logger.info(f"✅ Extracted JSON using brace matching (length: {len(json_str)} chars)")
                                            break
                    elif json_match:
                        json_str = json_match.group(0)
                
                if json_str:
                    logger.info(f"JSON string to parse (first 200 chars): {json_str[:200]}...")
                    
                    # Fix: Replace TradingView plot placeholders with actual values or extract them
                    # Handle cases where {{plot_22}} or {{plot("Signal Type Code")}} weren't replaced
                    import re
                    # ═══════════════════════════════════════════════════════════════════════
                    # 🔍 محاولة استخراج SIGNAL_CODE من alertcondition message
                    # ═══════════════════════════════════════════════════════════════════════
                    # عندما يكون alertcondition message يحتوي على SIGNAL_CODE والـ JSON في Message field
                    # يجب استخراج SIGNAL_CODE من النص قبل JSON
                    signal_code_from_alert = None
                    
                    # أولاً: حاول استخراج SIGNAL_CODE من alertcondition message (قبل JSON)
                    # Pattern: SIGNAL_CODE:{{plot_22}}|SYMBOL:... قبل JSON
                    # لكن المشكلة: TradingView يرسل {{plot_22}} وليس رقم
                    # الحل: نحتاج لاستخدام plot number (plot_22) لاستخراج القيمة
                    
                    # البحث عن SIGNAL_CODE مع رقم مباشر (1-8)
                    # Pattern 1: SIGNAL_CODE:1|SYMBOL:... (format صحيح)
                    signal_code_match = re.search(r'SIGNAL_CODE\s*:\s*(\d+)', raw_data_cleaned, re.IGNORECASE)
                    if signal_code_match:
                        signal_code_from_alert = signal_code_match.group(1)
                        logger.info(f"✅ Found SIGNAL_CODE with number in alertcondition message: {signal_code_from_alert}")
                    
                    # Pattern 2: إذا كان SIGNAL_CODE يحتوي على {{plot_22}}، نحتاج لاستخراج رقم من plot number
                    # plot_22 يعني plot رقم 22، لكن هذا لا يعطينا القيمة الفعلية
                    # الحل: نحاول استخراج رقم من JSON بعد الاستبدال
                    if not signal_code_from_alert:
                        # البحث عن SIGNAL_CODE مع plot placeholder
                        signal_code_with_plot = re.search(r'SIGNAL_CODE\s*:\s*\{\{plot[^}]+\}\}', raw_data_cleaned, re.IGNORECASE)
                        if signal_code_with_plot:
                            logger.warning("⚠️ SIGNAL_CODE contains plot placeholder - cannot extract actual value")
                            # سنستخدم fallback: تحديد من السياق
                    
                    # Pattern 3: SIGNAL_CODE=1 أو SIGNAL_CODE = 1
                    if not signal_code_from_alert:
                        signal_code_match2 = re.search(r'SIGNAL[_\s]*CODE\s*[:=]\s*(\d+)', raw_data_cleaned, re.IGNORECASE)
                        if signal_code_match2:
                            signal_code_from_alert = signal_code_match2.group(1)
                            logger.info(f"✅ Found SIGNAL_CODE in alternative format: {signal_code_from_alert}")
                    
                    # Check if signal field contains plot placeholder
                    if '{{plot' in json_str or '{{plot_' in json_str:
                        logger.warning("⚠️ Detected TradingView plot placeholder in JSON - attempting to fix...")
                        
                        if signal_code_from_alert:
                            # استبدال {{plot_...}} بـ SIGNAL_CODE الموجود في alertcondition message
                            json_str = re.sub(r'"signal"\s*:\s*\{\{[^}]+\}\}', f'"signal":{signal_code_from_alert}', json_str)
                            logger.info(f"✅ Fixed signal field using SIGNAL_CODE from alertcondition message: {signal_code_from_alert}")
                        else:
                            # إذا لم يوجد SIGNAL_CODE، استبدل بـ "0" (string) بدلاً من 0 (number)
                            # لأن JSON يحتاج quotes للقيم النصية، لكن signal قد يكون number أو string
                            # الحل: استبدل بـ null أولاً، ثم سيتم التعامل معه في الكود
                            json_str = re.sub(r'"signal"\s*:\s*\{\{[^}]+\}\}', '"signal":null', json_str)
                            # أيضاً استبدل أي {{plot...}} أخرى بـ null
                            json_str = re.sub(r'\{\{plot[^}]+\}\}', 'null', json_str)
                            logger.warning("⚠️ Replaced plot placeholder with null (SIGNAL_CODE not found - will detect from context or memory)")
                    
                    # أيضاً: إذا كان signal = null أو 0 في JSON الموجود، حاول استبداله بـ SIGNAL_CODE
                    if signal_code_from_alert:
                        json_str = re.sub(r'"signal"\s*:\s*(null|0)', f'"signal":{signal_code_from_alert}', json_str)
                        logger.info(f"✅ Fixed signal=null/0 using SIGNAL_CODE from alertcondition message: {signal_code_from_alert}")
                    
                    try:
                        data = json.loads(json_str)
                        # التحقق من أن data هو dict وليس int أو string
                        if not isinstance(data, dict):
                            logger.warning(f"⚠️ Parsed JSON is not a dict: {type(data)} = {data}")
                            data = None
                        else:
                            logger.info("✅ Successfully parsed JSON extracted from text")
                            logger.info(f"Parsed JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            logger.info(f"Signal: {data.get('signal', 'N/A')}, Symbol: {data.get('symbol', 'N/A')}")
                    except json.JSONDecodeError as e2:
                        logger.warning(f"Failed to parse extracted JSON: {e2}")
                        logger.info(f"Extracted JSON string: {json_str[:300]}")
                        # Try to parse whole string as JSON
                        try:
                            data = json.loads(raw_data_cleaned)
                            if not isinstance(data, dict):
                                data = None
                            else:
                                logger.info("✅ Successfully parsed JSON from raw data (after extraction attempt)")
                        except:
                            data = None
                else:
                    # No JSON found in text, try to parse whole string as JSON
                    logger.info("No JSON pattern found, trying to parse whole string as JSON...")
                    # Fix: Replace TradingView plot placeholders before parsing
                    raw_data_for_json = raw_data_cleaned
                    if '{{plot' in raw_data_for_json or '{{plot_' in raw_data_for_json:
                        logger.warning("⚠️ Detected TradingView plot placeholder in raw data - attempting to fix...")
                        # Try to extract signal code from text alert format (SIGNAL_CODE:...)
                        signal_code_match = re.search(r'SIGNAL_CODE:(\d+)', raw_data_for_json)
                        if signal_code_match:
                            signal_code = signal_code_match.group(1)
                            raw_data_for_json = re.sub(r'"signal"\s*:\s*\{\{[^}]+\}\}', f'"signal":{signal_code}', raw_data_for_json)
                            logger.info(f"✅ Fixed signal field using SIGNAL_CODE from text: {signal_code}")
                        else:
                            # Replace {{plot_22}} or {{plot("Signal Type Code")}} with 0 (unknown)
                            raw_data_for_json = re.sub(r'\{\{plot[^}]+\}\}', '0', raw_data_for_json)
                            logger.warning("⚠️ Replaced plot placeholder with 0 (will try to detect signal type from context)")
                    try:
                        data = json.loads(raw_data_for_json)
                        logger.info("✅ Successfully parsed JSON from raw data")
                        logger.info(f"Parsed JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    except json.JSONDecodeError:
                        logger.warning("Could not parse as JSON - will try text parsing")
                        pass
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse raw data as JSON: {e}")
            logger.info(f"Raw data preview: {raw_data[:200] if raw_data else 'Empty'}")
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
        # Also, if we have JSON but missing TP/SL, try to merge with text alert data
        if not data or not isinstance(data, dict):
            try:
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    # Try to parse TradingView text alert message
                    parsed_data = parse_tradingview_text_alert(raw_data)
                    if parsed_data:
                        data = parsed_data
                        logger.info("✅ Successfully parsed TradingView text alert")
                    else:
                        logger.warning(f"Could not parse text message: {raw_data[:100]}")
            except Exception as e:
                logger.warning(f"Error parsing text alert: {e}")
        else:
            # If we have JSON data but missing TP/SL, try to extract from text alert too
            # This helps with Central Alert where alertcondition message might have price info
            if isinstance(data, dict) and data.get('signal') and not data.get('tp1'):
                try:
                    raw_data = request.get_data(as_text=True)
                    if raw_data and ('SIGNAL:' in raw_data or 'PRICE:' in raw_data):
                        # Try to extract price from Central Alert format if JSON doesn't have it
                        if 'PRICE:' in raw_data and not data.get('entry_price') and not data.get('price'):
                            price_match = re.search(r'PRICE:([0-9]+(?:\.[0-9]+)?)', raw_data)
                            if price_match:
                                try:
                                    price = float(price_match.group(1))
                                    if not data.get('entry_price'):
                                        data['entry_price'] = price
                                    if not data.get('price'):
                                        data['price'] = price
                                    logger.info(f"✅ Extracted price from Central Alert format: {price}")
                                except:
                                    pass
                except:
                    pass
        
        if not data:
            logger.warning("Received empty request - no JSON, form, or raw data")
            raw_data_preview = request.get_data(as_text=True)[:200] if request.get_data() else "No data"
            return jsonify({
                "error": "No data received",
                "message": "Please send JSON data in the request body or use TradingView Alert with JSON format",
                "raw_data_preview": raw_data_preview,
                "tip": "In TradingView Alert, use JSON format in the message field. See TRADINGVIEW_ALERTS_SETUP.md"
            }), 400
        
        # Log parsed data in a formatted way
        logger.info("=" * 80)
        logger.info("=== PARSED DATA ===")
        logger.info("=" * 80)
        try:
            formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
            logger.info("Parsed Data (JSON formatted):")
            logger.info("-" * 80)
            logger.info(formatted_data)
            logger.info("-" * 80)
        except Exception as e:
            logger.info(f"Parsed Data (dict): {data}")
            logger.warning(f"Could not format as JSON: {e}")
        logger.info(f"Data Type: {type(data)}")
        logger.info(f"Data Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        
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
        
        # Signal Type Code mapping (from Pine Script indicator)
        # 1 = BUY, 2 = SELL, 3 = BUY_REVERSE, 4 = SELL_REVERSE, 5 = TP1, 6 = TP2, 7 = TP3, 8 = STOP_LOSS
        signal_code_map = {
            1: 'BUY',
            2: 'SELL',
            3: 'BUY_REVERSE',
            4: 'SELL_REVERSE',
            5: 'TP1_HIT',
            6: 'TP2_HIT',
            7: 'TP3_HIT',
            8: 'STOP_LOSS',
            '1': 'BUY',
            '2': 'SELL',
            '3': 'BUY_REVERSE',
            '4': 'SELL_REVERSE',
            '5': 'TP1_HIT',
            '6': 'TP2_HIT',
            '7': 'TP3_HIT',
            '8': 'STOP_LOSS'
        }
        
        # Convert signal code (number) to signal name if needed
        if signal in signal_code_map:
            original_signal = signal
            signal = signal_code_map[signal]
            logger.info(f"📊 Converted Signal Code {original_signal} → {signal}")
        elif isinstance(signal, str):
            signal = signal.upper()
        
        # Handle null signal or AUTO signal (from JSON when signal is "AUTO" or null)
        if signal is None or signal == 'null' or (isinstance(signal, str) and signal.upper() == 'AUTO'):
            signal = None
            logger.info("⚠️ Signal is null/AUTO - will detect from context or memory")
        
        # If signal is still 0 or empty/unknown, try to detect from context
        if signal is None or signal == 0 or signal == '' or signal == 'UNKNOWN' or (isinstance(signal, str) and signal.upper() == 'UNKNOWN'):
            logger.warning("⚠️ Signal type is unknown (0 or empty) - attempting to detect from context...")
            # Try to detect signal type from data context
            # This is a fallback when plot placeholder wasn't replaced
            entry_price = data.get('entry_price') or data.get('price')
            tp1 = data.get('tp1')
            tp2 = data.get('tp2')
            tp3 = data.get('tp3')
            stop_loss = data.get('stop_loss')
            
            logger.info(f"Context data: entry_price={entry_price}, tp1={tp1}, tp2={tp2}, tp3={tp3}, stop_loss={stop_loss}")
            
            # If we have TP/SL values, try to determine BUY vs SELL from price relationships
            if entry_price and entry_price > 0 and (tp1 or tp2 or tp3 or stop_loss):
                # For BUY: TP > Entry, SL < Entry
                # For SELL: TP < Entry, SL > Entry
                tp_value = tp1 or tp2 or tp3
                if tp_value and stop_loss and tp_value > 0 and stop_loss > 0:
                    if tp_value > entry_price and stop_loss < entry_price:
                        signal = 'BUY'
                        logger.info(f"✅ Detected BUY signal from context: TP ({tp_value}) > Entry ({entry_price}) > SL ({stop_loss})")
                    elif tp_value < entry_price and stop_loss > entry_price:
                        signal = 'SELL'
                        logger.info(f"✅ Detected SELL signal from context: TP ({tp_value}) < Entry ({entry_price}) < SL ({stop_loss})")
                    else:
                        # Default to BUY if relationship is unclear
                        signal = 'BUY'
                        logger.warning(f"⚠️ Cannot determine BUY/SELL from price relationships - defaulting to BUY")
                elif tp_value and tp_value > 0:
                    # Only TP available, check if it's above or below entry
                    if tp_value > entry_price:
                        signal = 'BUY'
                        logger.info(f"✅ Detected BUY signal from context: TP ({tp_value}) > Entry ({entry_price})")
                    else:
                        signal = 'SELL'
                        logger.info(f"✅ Detected SELL signal from context: TP ({tp_value}) < Entry ({entry_price})")
                elif stop_loss and stop_loss > 0:
                    # Only SL available, check if it's above or below entry
                    if stop_loss < entry_price:
                        signal = 'BUY'
                        logger.info(f"✅ Detected BUY signal from context: SL ({stop_loss}) < Entry ({entry_price})")
                    else:
                        signal = 'SELL'
                        logger.info(f"✅ Detected SELL signal from context: SL ({stop_loss}) > Entry ({entry_price})")
                else:
                    # Default to BUY if we can't determine
                    signal = 'BUY'
                    logger.warning("⚠️ Detected entry signal structure but cannot determine BUY/SELL - defaulting to BUY")
            else:
                logger.error(f"❌ Cannot determine signal type from context - entry_price={entry_price}, tp1={tp1}, tp2={tp2}, tp3={tp3}, stop_loss={stop_loss}")
                signal = 'UNKNOWN'
        
        logger.info(f"Signal type: {signal}")
        logger.info(f"Symbol: {data.get('symbol', 'N/A')}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 🧠 نظام الذاكرة: تحديد الإشارات العكسية و TP/SL تلقائياً
        # ═══════════════════════════════════════════════════════════════════════════
        symbol = data.get('symbol', '')
        current_price = data.get('price') or data.get('close') or data.get('entry_price')
        
        if symbol and signal:
            # ═══════════════════════════════════════════════════════════════════════════
            # 1. قبل تحديد REVERSE: تحقق من TP/SL المحفوظة من الإشارة السابقة
            # ═══════════════════════════════════════════════════════════════════════════
            # إذا كانت الإشارة BUY أو SELL، تحقق أولاً إذا كان السعر الحالي وصل لـ TP/SL
            original_signal = signal
            is_tp_sl_detected = False
            
            if signal in ['BUY', 'SELL'] and current_price and current_price > 0:
                position_data = get_open_position(symbol)
                if position_data and isinstance(position_data, dict):
                    # تحقق من TP/SL من الذاكرة
                    tp_sl_signal = detect_tp_sl_from_memory(symbol, current_price)
                    if tp_sl_signal:
                        # السعر الحالي وصل لـ TP/SL من الصفقة السابقة
                        signal = tp_sl_signal
                        data['signal'] = signal
                        is_tp_sl_detected = True
                        # تحديث data بالبيانات من الذاكرة
                        if not data.get('entry_price') and position_data.get('entry_price'):
                            data['entry_price'] = position_data.get('entry_price')
                        if not data.get('tp1') and position_data.get('tp1'):
                            data['tp1'] = position_data.get('tp1')
                        if not data.get('tp2') and position_data.get('tp2'):
                            data['tp2'] = position_data.get('tp2')
                        if not data.get('tp3') and position_data.get('tp3'):
                            data['tp3'] = position_data.get('tp3')
                        if not data.get('stop_loss') and position_data.get('stop_loss'):
                            data['stop_loss'] = position_data.get('stop_loss')
                        
                        # حذف من الذاكرة عند TP3 أو SL
                        position_closed = False
                        if signal in ['TP3_HIT', 'STOP_LOSS']:
                            clear_open_position(symbol)
                            logger.info(f"🗑️ Removed position from memory: {symbol} (closed: {signal})")
                            position_closed = True
                        else:
                            # TP1 أو TP2 - لا تحذف من الذاكرة
                            logger.info(f"✅ Detected {signal} from previous position in memory")
                        
                        # إذا أُغلقت الصفقة (TP3 أو SL)، لا نحفظ الإشارة الجديدة (BUY/SELL) لأنها قد تكون TP/SL فقط
                        # لكن إذا كانت الإشارة الأصلية (BUY/SELL) موجودة مع TP/SL في JSON، يمكن حفظها بعد إرسال TP/SL
                        # لكن في هذه الحالة، نرسل TP/SL فقط ولا نحفظ صفقة جديدة من نفس الإشارة
                        # (لأن الإشارة نفسها كانت TP/SL، وليست إشارة entry جديدة)
                        if not position_closed:
                            # TP1 أو TP2 - لا نحفظ إشارة جديدة (الصفقة لا تزال مفتوحة)
                            pass
                        else:
                            # TP3 أو SL - الصفقة أُغلقت، لكن لا نحفظ إشارة جديدة من نفس الإشارة
                            # (لأن الإشارة كانت TP/SL، وليست entry جديدة)
                            pass
            
            # ═══════════════════════════════════════════════════════════════════════════
            # 2. إذا كانت الإشارة BUY أو SELL (ولم تكن TP/SL)، تحقق من REVERSE
            # ═══════════════════════════════════════════════════════════════════════════
            # فقط إذا لم يتم اكتشاف TP/SL، نتعامل مع الإشارة الجديدة (Entry Signal)
            if not is_tp_sl_detected and signal in ['BUY', 'SELL'] and signal == original_signal:
                # استخدام نظام الذاكرة لتحديد إذا كانت الإشارة عكسية
                detected_signal = detect_reverse_signal(symbol, signal)
                if detected_signal != signal:
                    logger.info(f"🔄 Signal changed due to memory system: {signal} → {detected_signal}")
                    signal = detected_signal
                    # تحديث data['signal'] أيضاً
                    data['signal'] = signal
            
            # حفظ الصفقة في الذاكرة عند فتح صفقة جديدة (BUY أو SELL)
            # فقط إذا لم يتم اكتشاف TP/SL (لأن TP/SL يعني إغلاق الصفقة، وليس فتح صفقة جديدة)
            if not is_tp_sl_detected and signal in ['BUY', 'SELL', 'BUY_REVERSE', 'SELL_REVERSE']:
                # استخراج نوع الصفقة الأساسي (BUY أو SELL) من الإشارة
                base_signal = 'BUY' if signal in ['BUY', 'BUY_REVERSE'] else 'SELL'
                # حفظ TP/SL في الذاكرة أيضاً
                entry_price = data.get('entry_price') or data.get('price')
                tp1 = data.get('tp1')
                tp2 = data.get('tp2')
                tp3 = data.get('tp3')
                stop_loss = data.get('stop_loss')
                set_open_position(symbol, base_signal, entry_price, tp1, tp2, tp3, stop_loss)
                logger.info(f"💾 Saved position in memory: {symbol} = {base_signal} with TP/SL data")
            
            # حذف الصفقة من الذاكرة عند إغلاق الصفقة (TP3 أو STOP_LOSS)
            if signal in ['TP3_HIT', 'TP3', 'STOP_LOSS', 'SL']:
                clear_open_position(symbol)
                logger.info(f"🗑️ Removed position from memory: {symbol} (closed: {signal})")
        elif symbol and not signal:
            # إذا كان هناك symbol لكن لا يوجد signal، تحقق من البيانات لتحديد نوع الإشارة
            entry_price = data.get('entry_price') or data.get('price')
            exit_price = data.get('exit_price')  # للـ TP/SL
            current_price = data.get('price') or data.get('close') or entry_price  # السعر الحالي
            tp1 = data.get('tp1')
            tp2 = data.get('tp2')
            tp3 = data.get('tp3')
            stop_loss = data.get('stop_loss')
            
            # ═══════════════════════════════════════════════════════════════════════════
            # 🧠 تحديد نوع الإشارة تلقائياً من الذاكرة والبيانات
            # ═══════════════════════════════════════════════════════════════════════════
            
            # 1. أولاً: تحقق من الذاكرة إذا كانت هناك صفقة مفتوحة + سعر حالي (TP/SL)
            if current_price and current_price > 0:
                tp_sl_signal = detect_tp_sl_from_memory(symbol, current_price)
                if tp_sl_signal:
                    signal = tp_sl_signal
                    data['signal'] = signal
                    # تحديث data بالبيانات من الذاكرة
                    position_data = get_open_position(symbol)
                    if position_data and isinstance(position_data, dict):
                        if not data.get('entry_price') and position_data.get('entry_price'):
                            data['entry_price'] = position_data.get('entry_price')
                        if not data.get('tp1') and position_data.get('tp1'):
                            data['tp1'] = position_data.get('tp1')
                        if not data.get('tp2') and position_data.get('tp2'):
                            data['tp2'] = position_data.get('tp2')
                        if not data.get('tp3') and position_data.get('tp3'):
                            data['tp3'] = position_data.get('tp3')
                        if not data.get('stop_loss') and position_data.get('stop_loss'):
                            data['stop_loss'] = position_data.get('stop_loss')
                    
                    # حذف من الذاكرة عند TP3 أو SL
                    if signal in ['TP3_HIT', 'STOP_LOSS']:
                        clear_open_position(symbol)
                        logger.info(f"🗑️ Removed position from memory: {symbol} (closed: {signal})")
            
            # 2. إذا كان هناك exit_price أو current_price مع TP/SL في البيانات، قد تكون TP أو SL
            if not signal:
                price_to_check = exit_price or current_price
                
                if price_to_check and entry_price and (tp1 or tp2 or tp3 or stop_loss):
                    # تحقق من أي TP/SL تم الوصول إليه
                    # نستخدم tolerance صغير (0.5%) لتحديد أي TP/SL
                    tolerance = abs(price_to_check - entry_price) * 0.005 if entry_price > 0 else price_to_check * 0.005
                    
                    # تحقق من TP3 أولاً (الأبعد)
                    if tp3 and abs(price_to_check - tp3) <= tolerance:
                        signal = 'TP3_HIT'
                        # حذف من الذاكرة عند TP3
                        clear_open_position(symbol)
                        logger.info(f"🗑️ Removed position from memory: {symbol} (closed: TP3)")
                    # ثم TP2
                    elif tp2 and abs(price_to_check - tp2) <= tolerance:
                        signal = 'TP2_HIT'
                    # ثم TP1
                    elif tp1 and abs(price_to_check - tp1) <= tolerance:
                        signal = 'TP1_HIT'
                    # ثم Stop Loss
                    elif stop_loss and abs(price_to_check - stop_loss) <= tolerance:
                        signal = 'STOP_LOSS'
                        # حذف من الذاكرة عند SL
                        clear_open_position(symbol)
                        logger.info(f"🗑️ Removed position from memory: {symbol} (closed: SL)")
            
            # 3. إذا كان هناك TP/SL و entry_price (بدون exit_price)، فهذه إشارة entry (BUY/SELL)
            if not signal and entry_price and (tp1 or tp2 or tp3 or stop_loss):
                # تحديد BUY أو SELL من TP/SL relationships
                tp_value = tp1 or tp2 or tp3
                if tp_value and stop_loss and tp_value > 0 and stop_loss > 0:
                    if tp_value > entry_price and stop_loss < entry_price:
                        signal = 'BUY'
                    elif tp_value < entry_price and stop_loss > entry_price:
                        signal = 'SELL'
                elif tp_value and tp_value > 0:
                    # فقط TP متاح
                    if tp_value > entry_price:
                        signal = 'BUY'
                    else:
                        signal = 'SELL'
                elif stop_loss and stop_loss > 0:
                    # فقط SL متاح
                    if stop_loss < entry_price:
                        signal = 'BUY'
                    else:
                        signal = 'SELL'
            
            # 4. إذا تم تحديد BUY/SELL، استخدم نظام الذاكرة لتحديد REVERSE
            if signal in ['BUY', 'SELL']:
                detected_signal = detect_reverse_signal(symbol, signal)
                if detected_signal != signal:
                    logger.info(f"🔄 Signal changed due to memory system: {signal} → {detected_signal}")
                    signal = detected_signal
                data['signal'] = signal
                
                # حفظ في الذاكرة مع TP/SL
                base_signal = 'BUY' if signal in ['BUY', 'BUY_REVERSE'] else 'SELL'
                set_open_position(symbol, base_signal, entry_price, tp1, tp2, tp3, stop_loss)
                logger.info(f"💾 Saved position in memory: {symbol} = {base_signal} with TP/SL")
            elif signal:
                # TP/SL signals - تأكد من تحديث data
                data['signal'] = signal
                logger.info(f"✅ Auto-detected {signal} from memory and price data")
        
        # ═══════════════════════════════════════════════════════════════════════════
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
        elif signal == 'CLOSE' or signal == 'POSITION_CLOSED':
            message = format_position_closed(data)
        else:
            logger.warning(f"Unknown signal type: {signal}")
            return jsonify({"error": f"Unknown signal type: {signal}"}), 400
        
        # Send message to Telegram (use chat_id from URL if provided)
        if message:
            logger.info("=" * 80)
            logger.info("=== FORMATTED MESSAGE (TO BE SENT) ===")
            logger.info("=" * 80)
            logger.info(f"Message Length: {len(message)} characters")
            logger.info("-" * 80)
            logger.info("Message Content:")
            logger.info("-" * 80)
            logger.info(message)
            logger.info("-" * 80)
            logger.info(f"Target Chat ID: {target_chat_id}")
            logger.info("=" * 80)
            
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

