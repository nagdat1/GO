"""
Telegram Bot Module for sending trading signals
"""
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def format_price(price: float) -> str:
    """
    Format price with appropriate decimal places based on price range
    
    Args:
        price: Price value to format
        
    Returns:
        str: Formatted price string
    """
    if price == 0:
        return "0.00"
    
    # For very high prices (> 1000): show 0-2 decimal places
    if price >= 1000:
        # Round to nearest integer or 1-2 decimals
        if price >= 10000:
            return f"{price:,.0f}"  # No decimals, with commas
        else:
            return f"{price:,.2f}"  # 2 decimals with commas
    
    # For medium prices (1-1000): show 2-4 decimal places
    elif price >= 1:
        return f"{price:,.2f}"  # 2 decimals with commas
    
    # For low prices (0.01-1): show 4-6 decimal places
    elif price >= 0.01:
        return f"{price:.4f}"  # 4 decimals
    
    # For very low prices (< 0.01): show 6-8 decimal places
    else:
        return f"{price:.8f}".rstrip('0').rstrip('.')  # Up to 8 decimals, remove trailing zeros


def send_message(message: str, chat_id: str = None) -> bool:
    """
    Send message to Telegram chat
    
    Args:
        message: Message text to send
        chat_id: Optional chat ID (if not provided, uses TELEGRAM_CHAT_ID from config)
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        # Use provided chat_id or fall back to config
        target_chat_id = chat_id or TELEGRAM_CHAT_ID
        
        if not target_chat_id:
            logger.error("No chat ID provided and TELEGRAM_CHAT_ID not set")
            return False
        
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Message sent successfully to Telegram (chat_id: {target_chat_id})")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message to Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def format_buy_signal(data: dict) -> str:
    """
    Format BUY signal message
    
    Args:
        data: Dictionary containing signal data
        
    Returns:
        str: Formatted message
    """
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🟢🟢🟢 *BUY SIGNAL* 🟢🟢🟢\n\n"
    message += f"📊 Symbol: {symbol}\n"
    
    # Check if price is valid (not 0, which means Position Size was extracted instead of Price)
    if entry_price == 0:
        message += f"⚠️ *Entry Price: NOT AVAILABLE*\n"
        message += f"❌ Text alert contains Position Size instead of Price!\n\n"
    else:
        message += f"💰 Entry Price: {format_price(entry_price)}\n"
    
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}\n\n"
    
    # Only show TP/SL if they exist (from JSON data, not estimated)
    if tp1 is not None and tp2 is not None and tp3 is not None and stop_loss is not None:
        tp1 = float(tp1)
        tp2 = float(tp2)
        tp3 = float(tp3)
        stop_loss = float(stop_loss)
        
        # Calculate percentages
        # For BUY: profit when price increases, so TP > Entry, SL < Entry
        tp1_pct = ((tp1 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        tp2_pct = ((tp2 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        tp3_pct = ((tp3 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        sl_pct = ((stop_loss - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        
        # Validate and format signs correctly
        tp1_sign = "+" if tp1_pct >= 0 else "-"
        tp2_sign = "+" if tp2_pct >= 0 else "-"
        tp3_sign = "+" if tp3_pct >= 0 else "-"
        sl_sign = "-" if sl_pct < 0 else "+"
        
        message += f"🎯 *Take Profit Targets:*\n"
        message += f"🎯 TP1: {format_price(tp1)} ({tp1_sign}{abs(tp1_pct):.2f}%)\n"
        message += f"🎯 TP2: {format_price(tp2)} ({tp2_sign}{abs(tp2_pct):.2f}%)\n"
        message += f"🎯 TP3: {format_price(tp3)} ({tp3_sign}{abs(tp3_pct):.2f}%)\n\n"
        message += f"🛑 Stop Loss: {format_price(stop_loss)} ({sl_sign}{abs(sl_pct):.2f}%)"
    else:
        # Text alert - no TP/SL data available
        if entry_price == 0:
            message += f"⚠️ *ERROR:* Real price not available!\n"
            message += f"📌 Text alert contains Position Size instead of Price.\n"
            message += f"📌 Position Size: حجم المركز (Volume) ❌\n"
            message += f"📌 Price: سعر العملة الحقيقي ✅\n\n"
            message += f"✅ *SOLUTION:* Use JSON format in TradingView Alert Message field.\n"
            message += f"📖 See README.md for instructions."
        else:
            message += f"⚠️ *Note:* TP/SL data not available from text alert.\n"
            message += f"Please use JSON format in TradingView Alert for complete data."
    
    return message


def format_sell_signal(data: dict) -> str:
    """
    Format SELL signal message
    
    Args:
        data: Dictionary containing signal data
        
    Returns:
        str: Formatted message
    """
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🔴🔴🔴 *SELL SIGNAL* 🔴🔴🔴\n\n"
    message += f"📊 Symbol: {symbol}\n"
    
    # Check if price is valid (not 0, which means Position Size was extracted instead of Price)
    if entry_price == 0:
        message += f"⚠️ *Entry Price: NOT AVAILABLE*\n"
        message += f"❌ Text alert contains Position Size instead of Price!\n\n"
    else:
        message += f"💰 Entry Price: {format_price(entry_price)}\n"
    
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}\n\n"
    
    # Only show TP/SL if they exist (from JSON data, not estimated)
    if tp1 is not None and tp2 is not None and tp3 is not None and stop_loss is not None:
        tp1 = float(tp1)
        tp2 = float(tp2)
        tp3 = float(tp3)
        stop_loss = float(stop_loss)
        
        # Calculate percentages (for SELL, profit when price goes down)
        # TP should be lower than entry for SELL
        # For SELL: profit when price decreases, so TP < Entry, SL > Entry
        tp1_pct = ((entry_price - tp1) / entry_price) * 100 if entry_price > 0 else 0
        tp2_pct = ((entry_price - tp2) / entry_price) * 100 if entry_price > 0 else 0
        tp3_pct = ((entry_price - tp3) / entry_price) * 100 if entry_price > 0 else 0
        # SL is higher than entry for SELL (loss if price goes up)
        sl_pct = ((stop_loss - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        
        # Validate and format signs correctly
        tp1_sign = "+" if tp1_pct >= 0 else "-"
        tp2_sign = "+" if tp2_pct >= 0 else "-"
        tp3_sign = "+" if tp3_pct >= 0 else "-"
        sl_sign = "-" if sl_pct > 0 else "+"
        
        message += f"🎯 *Take Profit Targets:*\n"
        message += f"🎯 TP1: {format_price(tp1)} ({tp1_sign}{abs(tp1_pct):.2f}%)\n"
        message += f"🎯 TP2: {format_price(tp2)} ({tp2_sign}{abs(tp2_pct):.2f}%)\n"
        message += f"🎯 TP3: {format_price(tp3)} ({tp3_sign}{abs(tp3_pct):.2f}%)\n\n"
        message += f"🛑 Stop Loss: {format_price(stop_loss)} ({sl_sign}{abs(sl_pct):.2f}%)"
    else:
        # Text alert - no TP/SL data available
        if entry_price == 0:
            message += f"⚠️ *ERROR:* Real price not available!\n"
            message += f"📌 Text alert contains Position Size instead of Price.\n"
            message += f"📌 Position Size: حجم المركز (Volume) ❌\n"
            message += f"📌 Price: سعر العملة الحقيقي ✅\n\n"
            message += f"✅ *SOLUTION:* Use JSON format in TradingView Alert Message field.\n"
            message += f"📖 See README.md for instructions."
        else:
            message += f"⚠️ *Note:* TP/SL data not available from text alert.\n"
            message += f"Please use JSON format in TradingView Alert for complete data."
    
    return message


def format_buy_reverse_signal(data: dict) -> str:
    """
    Format BUY REVERSE signal message (position reversed from Short to Long)
    
    Args:
        data: Dictionary containing signal data
        
    Returns:
        str: Formatted message
    """
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🟠🔄🟠 *BUY REVERSE SIGNAL* 🟠🔄🟠\n"
    message += f"⚠️ *Position Reversed (Short → Long)*\n\n"
    message += f"📊 Symbol: {symbol}\n"
    
    # Check if price is valid (not 0, which means Position Size was extracted instead of Price)
    if entry_price == 0:
        message += f"⚠️ *Entry Price: NOT AVAILABLE*\n"
        message += f"❌ Text alert contains Position Size instead of Price!\n\n"
    else:
        message += f"💰 Entry Price: {format_price(entry_price)}\n"
    
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}\n\n"
    
    # Only show TP/SL if they exist (from JSON data, not estimated)
    if tp1 is not None and tp2 is not None and tp3 is not None and stop_loss is not None:
        tp1 = float(tp1)
        tp2 = float(tp2)
        tp3 = float(tp3)
        stop_loss = float(stop_loss)
        
        # Calculate percentages
        # For BUY: profit when price increases, so TP > Entry, SL < Entry
        tp1_pct = ((tp1 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        tp2_pct = ((tp2 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        tp3_pct = ((tp3 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        sl_pct = ((stop_loss - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        
        # Validate and format signs correctly
        tp1_sign = "+" if tp1_pct >= 0 else "-"
        tp2_sign = "+" if tp2_pct >= 0 else "-"
        tp3_sign = "+" if tp3_pct >= 0 else "-"
        sl_sign = "-" if sl_pct < 0 else "+"
        
        message += f"🎯 *Take Profit Targets:*\n"
        message += f"🎯 TP1: {format_price(tp1)} ({tp1_sign}{abs(tp1_pct):.2f}%)\n"
        message += f"🎯 TP2: {format_price(tp2)} ({tp2_sign}{abs(tp2_pct):.2f}%)\n"
        message += f"🎯 TP3: {format_price(tp3)} ({tp3_sign}{abs(tp3_pct):.2f}%)\n\n"
        message += f"🛑 Stop Loss: {format_price(stop_loss)} ({sl_sign}{abs(sl_pct):.2f}%)"
    else:
        # Text alert - no TP/SL data available
        if entry_price == 0:
            message += f"⚠️ *ERROR:* Real price not available!\n"
            message += f"📌 Text alert contains Position Size instead of Price.\n"
            message += f"📌 Position Size: حجم المركز (Volume) ❌\n"
            message += f"📌 Price: سعر العملة الحقيقي ✅\n\n"
            message += f"✅ *SOLUTION:* Use JSON format in TradingView Alert Message field.\n"
            message += f"📖 See README.md for instructions."
        else:
            message += f"⚠️ *Note:* TP/SL data not available from text alert.\n"
            message += f"Please use JSON format in TradingView Alert for complete data."
    
    return message


def format_sell_reverse_signal(data: dict) -> str:
    """
    Format SELL REVERSE signal message (position reversed from Long to Short)
    
    Args:
        data: Dictionary containing signal data
        
    Returns:
        str: Formatted message
    """
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🟠🔄🟠 *SELL REVERSE SIGNAL* 🟠🔄🟠\n"
    message += f"⚠️ *Position Reversed (Long → Short)*\n\n"
    message += f"📊 Symbol: {symbol}\n"
    
    # Check if price is valid (not 0, which means Position Size was extracted instead of Price)
    if entry_price == 0:
        message += f"⚠️ *Entry Price: NOT AVAILABLE*\n"
        message += f"❌ Text alert contains Position Size instead of Price!\n\n"
    else:
        message += f"💰 Entry Price: {format_price(entry_price)}\n"
    
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}\n\n"
    
    # Only show TP/SL if they exist (from JSON data, not estimated)
    if tp1 is not None and tp2 is not None and tp3 is not None and stop_loss is not None:
        tp1 = float(tp1)
        tp2 = float(tp2)
        tp3 = float(tp3)
        stop_loss = float(stop_loss)
        
        # Calculate percentages (for SELL, profit when price goes down)
        # TP should be lower than entry for SELL
        # For SELL: profit when price decreases, so TP < Entry, SL > Entry
        tp1_pct = ((entry_price - tp1) / entry_price) * 100 if entry_price > 0 else 0
        tp2_pct = ((entry_price - tp2) / entry_price) * 100 if entry_price > 0 else 0
        tp3_pct = ((entry_price - tp3) / entry_price) * 100 if entry_price > 0 else 0
        # SL is higher than entry for SELL (loss if price goes up)
        sl_pct = ((stop_loss - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        
        # Validate and format signs correctly
        tp1_sign = "+" if tp1_pct >= 0 else "-"
        tp2_sign = "+" if tp2_pct >= 0 else "-"
        tp3_sign = "+" if tp3_pct >= 0 else "-"
        sl_sign = "-" if sl_pct > 0 else "+"
        
        message += f"🎯 *Take Profit Targets:*\n"
        message += f"🎯 TP1: {format_price(tp1)} ({tp1_sign}{abs(tp1_pct):.2f}%)\n"
        message += f"🎯 TP2: {format_price(tp2)} ({tp2_sign}{abs(tp2_pct):.2f}%)\n"
        message += f"🎯 TP3: {format_price(tp3)} ({tp3_sign}{abs(tp3_pct):.2f}%)\n\n"
        message += f"🛑 Stop Loss: {format_price(stop_loss)} ({sl_sign}{abs(sl_pct):.2f}%)"
    else:
        # Text alert - no TP/SL data available
        if entry_price == 0:
            message += f"⚠️ *ERROR:* Real price not available!\n"
            message += f"📌 Text alert contains Position Size instead of Price.\n"
            message += f"📌 Position Size: حجم المركز (Volume) ❌\n"
            message += f"📌 Price: سعر العملة الحقيقي ✅\n\n"
            message += f"✅ *SOLUTION:* Use JSON format in TradingView Alert Message field.\n"
            message += f"📖 See README.md for instructions."
        else:
            message += f"⚠️ *Note:* TP/SL data not available from text alert.\n"
            message += f"Please use JSON format in TradingView Alert for complete data."
    
    return message


def format_tp1_hit(data: dict) -> str:
    """Format TP1 target hit message"""
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    exit_price = float(data.get('exit_price', data.get('tp1', 0)))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    # Calculate profit percentage
    # For BUY: exit_price > entry_price (profit when price goes up)
    # For SELL: exit_price < entry_price (profit when price goes down)
    # Use absolute value since we know TP was hit (profit scenario)
    if entry_price > 0:
        if exit_price > entry_price:
            # BUY position - profit when exit is higher
            profit_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            # SELL position - profit when exit is lower
            profit_pct = ((entry_price - exit_price) / entry_price) * 100
    else:
        profit_pct = 0
    
    message = f"🎯✅🎯 *TP1 - FIRST TARGET HIT* 🎯✅🎯\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {format_price(entry_price)}\n"
    message += f"💰 Exit Price: {format_price(exit_price)}\n"
    message += f"💵 Profit: +{profit_pct:.2f}%\n"
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}"
    
    return message


def format_tp2_hit(data: dict) -> str:
    """Format TP2 target hit message"""
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    exit_price = float(data.get('exit_price', data.get('tp2', 0)))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    # Calculate profit percentage
    # For BUY: exit_price > entry_price (profit when price goes up)
    # For SELL: exit_price < entry_price (profit when price goes down)
    if entry_price > 0:
        if exit_price > entry_price:
            # BUY position - profit when exit is higher
            profit_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            # SELL position - profit when exit is lower
            profit_pct = ((entry_price - exit_price) / entry_price) * 100
    else:
        profit_pct = 0
    
    message = f"🎯✅🎯 *TP2 - SECOND TARGET HIT* 🎯✅🎯\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {format_price(entry_price)}\n"
    message += f"💰 Exit Price: {format_price(exit_price)}\n"
    message += f"💵 Profit: +{profit_pct:.2f}%\n"
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}"
    
    return message


def format_tp3_hit(data: dict) -> str:
    """Format TP3 target hit message"""
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    exit_price = float(data.get('exit_price', data.get('tp3', 0)))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    # Calculate profit percentage
    # For BUY: exit_price > entry_price (profit when price goes up)
    # For SELL: exit_price < entry_price (profit when price goes down)
    if entry_price > 0:
        if exit_price > entry_price:
            # BUY position - profit when exit is higher
            profit_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            # SELL position - profit when exit is lower
            profit_pct = ((entry_price - exit_price) / entry_price) * 100
    else:
        profit_pct = 0
    
    message = f"🎯✅🎯 *TP3 - THIRD TARGET HIT* 🎯✅🎯\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {format_price(entry_price)}\n"
    message += f"💰 Exit Price: {format_price(exit_price)}\n"
    message += f"💵 Profit: +{profit_pct:.2f}%\n"
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}"
    
    return message


def format_stop_loss_hit(data: dict) -> str:
    """Format Stop Loss hit message"""
    symbol = data.get('symbol', 'N/A')
    price = float(data.get('price', 0))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🛑😔🛑 *STOP LOSS HIT* 🛑😔🛑\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Price: {format_price(price)}\n"
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}"
    
    return message


def format_position_closed(data: dict) -> str:
    """Format Position Closed message"""
    symbol = data.get('symbol', 'N/A')
    price = float(data.get('price', 0))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🔚📊🔚 *POSITION CLOSED* 🔚📊🔚\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Price: {format_price(price)}\n"
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}"
    
    return message


def send_startup_message() -> bool:
    """
    Send welcome/startup message when the application starts
    
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🤖 *Bot Started Successfully!*\n\n"
        message += f"✅ TradingView Webhook to Telegram Bot\n"
        message += f"🕐 Started at: {current_time}\n\n"
        message += f"📊 Ready to receive trading signals!\n"
        message += f"🔗 Webhook endpoint: `/webhook`\n\n"
        message += f"✨ Waiting for signals..."
        
        return send_message(message)
        
    except Exception as e:
        logger.error(f"Error sending startup message: {e}")
        return False

