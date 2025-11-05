"""
Telegram Bot Module - نسخة مبسطة مع رسائل بالعربية
"""
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def escape_markdown(text: str) -> str:
    """تهريب الأحرف الخاصة في Markdown (لا نهرب . و , لأنها جزء من الأرقام)"""
    if not isinstance(text, str):
        text = str(text)
    # تهريب الأحرف الخاصة في Markdown (لا نهرب . و , لأنها جزء من الأرقام)
    # الأرقام نضعها داخل backticks (`) بدلاً من تهريبها
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text

def format_price(price: float) -> str:
    """تنسيق السعر"""
    if price == 0:
        return "0.00"
    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:,.2f}"
    elif price >= 0.01:
        return f"{price:.4f}"
    else:
        return f"{price:.8f}".rstrip('0').rstrip('.')

def send_message(message: str, chat_id: str = None) -> bool:
    """إرسال رسالة إلى Telegram"""
    try:
        target_chat_id = chat_id or TELEGRAM_CHAT_ID
        if not target_chat_id:
            logger.error("❌ No chat ID provided - يجب تحديد Chat ID")
            return False
        
        # تحويل chat_id إلى string (للمجموعات قد يكون سالباً)
        chat_id_str = str(target_chat_id)
        
        payload = {
            "chat_id": chat_id_str,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        logger.info(f"📤 Attempting to send message to chat_id: {chat_id_str}")
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        
        # التحقق من الاستجابة
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Message sent successfully to Telegram (chat_id: {chat_id_str})")
                return True
            else:
                error_description = result.get('description', 'Unknown error')
                logger.error(f"❌ Telegram API error: {error_description}")
                if 'chat not found' in error_description.lower():
                    logger.error("❌ المشكلة: Chat ID غير صحيح أو البوت غير عضو في المجموعة!")
                elif 'bot was blocked' in error_description.lower():
                    logger.error("❌ المشكلة: البوت محظور من المجموعة!")
                return False
        else:
            logger.error(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error sending message: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending message: {e}", exc_info=True)
        return False

def format_buy_signal(data: dict) -> str:
    """تنسيق إشارة الشراء (صفقة لونج)"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price') or data.get('price', 0)
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🟢 *صفقة لونج \\(LONG\\)* 🟢\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}\n"
    message += f"📈 الإطار الزمني: {escape_markdown(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 *أهداف الربح:*\n"
        if tp1:
            message += f"🎯 TP1: `{format_price(float(tp1))}`\n"
        if tp2:
            message += f"🎯 TP2: `{format_price(float(tp2))}`\n"
        if tp3:
            message += f"🎯 TP3: `{format_price(float(tp3))}`\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: `{format_price(float(stop_loss))}`"
    
    return message

def format_sell_signal(data: dict) -> str:
    """تنسيق إشارة البيع (صفقة شورت)"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price') or data.get('price', 0)
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🔴 *صفقة شورت \\(SHORT\\)* 🔴\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}\n"
    message += f"📈 الإطار الزمني: {escape_markdown(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 *أهداف الربح:*\n"
        if tp1:
            message += f"🎯 TP1: `{format_price(float(tp1))}`\n"
        if tp2:
            message += f"🎯 TP2: `{format_price(float(tp2))}`\n"
        if tp3:
            message += f"🎯 TP3: `{format_price(float(tp3))}`\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: `{format_price(float(stop_loss))}`"
    
    return message

def format_buy_reverse_signal(data: dict) -> str:
    """تنسيق إشارة الشراء العكسية (لونج عكسي)"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price') or data.get('price', 0)
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🟠 *صفقة لونج عكسي \\(LONG REVERSE\\)* 🟠\n"
    message += f"⚠️ *تم عكس الصفقة*\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}\n"
    message += f"📈 الإطار الزمني: {escape_markdown(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 *أهداف الربح:*\n"
        if tp1:
            message += f"🎯 TP1: `{format_price(float(tp1))}`\n"
        if tp2:
            message += f"🎯 TP2: `{format_price(float(tp2))}`\n"
        if tp3:
            message += f"🎯 TP3: `{format_price(float(tp3))}`\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: `{format_price(float(stop_loss))}`"
    
    return message

def format_sell_reverse_signal(data: dict) -> str:
    """تنسيق إشارة البيع العكسية (شورت عكسي)"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price') or data.get('price', 0)
    tp1 = data.get('tp1')
    tp2 = data.get('tp2')
    tp3 = data.get('tp3')
    stop_loss = data.get('stop_loss')
    time = data.get('time', 'N/A')
    timeframe = data.get('timeframe', 'N/A')
    
    message = f"🟠 *صفقة شورت عكسي \\(SHORT REVERSE\\)* 🟠\n"
    message += f"⚠️ *تم عكس الصفقة*\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}\n"
    message += f"📈 الإطار الزمني: {escape_markdown(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 *أهداف الربح:*\n"
        if tp1:
            message += f"🎯 TP1: `{format_price(float(tp1))}`\n"
        if tp2:
            message += f"🎯 TP2: `{format_price(float(tp2))}`\n"
        if tp3:
            message += f"🎯 TP3: `{format_price(float(tp3))}`\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: `{format_price(float(stop_loss))}`"
    
    return message

def format_tp1_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الأول"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('tp1') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🎯✅ *تم ضرب الهدف الأول \\(TP1\\)* ✅🎯\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"💰 سعر الخروج: `{format_price(exit_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}"
    
    return message

def format_tp2_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الثاني"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('tp2') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🎯✅ *تم ضرب الهدف الثاني \\(TP2\\)* ✅🎯\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"💰 سعر الخروج: `{format_price(exit_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}"
    
    return message

def format_tp3_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الثالث"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('tp3') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🎯✅ *تم ضرب الهدف الثالث \\(TP3\\)* ✅🎯\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"💰 سعر الخروج: `{format_price(exit_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}"
    
    return message

def format_stop_loss_hit(data: dict) -> str:
    """تنسيق رسالة ضرب وقف الخسارة"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('stop_loss') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🛑😔 *تم ضرب وقف الخسارة \\(Stop Loss\\)* 😔🛑\n\n"
    message += f"📊 الرمز: {escape_markdown(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: `{format_price(entry_price)}`\n"
    message += f"💰 سعر الخروج: `{format_price(exit_price)}`\n"
    message += f"⏰ الوقت: {escape_markdown(time)}"
    
    return message

def send_startup_message() -> bool:
    """إرسال رسالة بدء التشغيل"""
    try:
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🤖 *تم تشغيل البوت بنجاح!*\n\n"
        message += f"✅ البوت جاهز لاستقبال الإشارات\n"
        message += f"🕐 وقت البدء: {current_time}\n\n"
        message += f"📊 البوت يستقبل 8 أنواع من الإشارات:\n"
        message += f"• صفقة لونج (BUY)\n"
        message += f"• صفقة شورت (SELL)\n"
        message += f"• صفقة لونج عكسي (BUY_REVERSE)\n"
        message += f"• صفقة شورت عكسي (SELL_REVERSE)\n"
        message += f"• ضرب الهدف الأول (TP1)\n"
        message += f"• ضرب الهدف الثاني (TP2)\n"
        message += f"• ضرب الهدف الثالث (TP3)\n"
        message += f"• ضرب وقف الخسارة (STOP_LOSS)"
        
        return send_message(message)
    except Exception as e:
        logger.error(f"Error sending startup message: {e}")
        return False
