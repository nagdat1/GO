"""
Telegram Bot Module for sending trading signals
"""
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


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
    tp1 = float(data.get('tp1', 0))
    tp2 = float(data.get('tp2', 0))
    tp3 = float(data.get('tp3', 0))
    stop_loss = float(data.get('stop_loss', 0))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    # Calculate percentages
    tp1_pct = ((tp1 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    tp2_pct = ((tp2 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    tp3_pct = ((tp3 - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    sl_pct = ((stop_loss - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    
    message = f"🟢🟢🟢 *BUY SIGNAL* 🟢🟢🟢\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {entry_price:.2f}\n"
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}\n\n"
    message += f"🎯 *Take Profit Targets:*\n"
    message += f"🎯 TP1: {tp1:.2f} (+{tp1_pct:.2f}%)\n"
    message += f"🎯 TP2: {tp2:.2f} (+{tp2_pct:.2f}%)\n"
    message += f"🎯 TP3: {tp3:.2f} (+{tp3_pct:.2f}%)\n\n"
    message += f"🛑 Stop Loss: {stop_loss:.2f} ({sl_pct:.2f}%)"
    
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
    tp1 = float(data.get('tp1', 0))
    tp2 = float(data.get('tp2', 0))
    tp3 = float(data.get('tp3', 0))
    stop_loss = float(data.get('stop_loss', 0))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    # Calculate percentages (for SELL, profit when price goes down)
    # TP should be lower than entry for SELL
    tp1_pct = ((entry_price - tp1) / entry_price) * 100 if entry_price > 0 else 0
    tp2_pct = ((entry_price - tp2) / entry_price) * 100 if entry_price > 0 else 0
    tp3_pct = ((entry_price - tp3) / entry_price) * 100 if entry_price > 0 else 0
    # SL is higher than entry for SELL (loss if price goes up)
    sl_pct = ((stop_loss - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    
    message = f"🔴🔴🔴 *SELL SIGNAL* 🔴🔴🔴\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {entry_price:.2f}\n"
    message += f"⏰ Time: {time}\n"
    message += f"📈 Timeframe: {timeframe}\n\n"
    message += f"🎯 *Take Profit Targets:*\n"
    message += f"🎯 TP1: {tp1:.2f} (+{tp1_pct:.2f}%)\n"
    message += f"🎯 TP2: {tp2:.2f} (+{tp2_pct:.2f}%)\n"
    message += f"🎯 TP3: {tp3:.2f} (+{tp3_pct:.2f}%)\n\n"
    message += f"🛑 Stop Loss: {stop_loss:.2f} ({sl_pct:.2f}%)"
    
    return message


def format_tp1_hit(data: dict) -> str:
    """Format TP1 target hit message"""
    symbol = data.get('symbol', 'N/A')
    entry_price = float(data.get('entry_price', 0))
    exit_price = float(data.get('exit_price', data.get('tp1', 0)))
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    # Calculate profit percentage
    profit_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    
    message = f"🎯✅🎯 *TP1 - FIRST TARGET HIT* 🎯✅🎯\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {entry_price:.2f}\n"
    message += f"💰 Exit Price: {exit_price:.2f}\n"
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
    profit_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    
    message = f"🎯✅🎯 *TP2 - SECOND TARGET HIT* 🎯✅🎯\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {entry_price:.2f}\n"
    message += f"💰 Exit Price: {exit_price:.2f}\n"
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
    profit_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    
    message = f"🎯✅🎯 *TP3 - THIRD TARGET HIT* 🎯✅🎯\n\n"
    message += f"📊 Symbol: {symbol}\n"
    message += f"💰 Entry Price: {entry_price:.2f}\n"
    message += f"💰 Exit Price: {exit_price:.2f}\n"
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
    message += f"💰 Price: {price:.2f}\n"
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
    message += f"💰 Price: {price:.2f}\n"
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

