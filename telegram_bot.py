"""
Telegram Bot Module - نسخة مبسطة مع رسائل بالعربية
"""
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Rate limiting: آخر وقت إرسال رسالة (لتجنب spam)
_last_message_time = 0
_min_delay_between_messages = 0.5  # 500ms بين كل رسالة (لتجنب spam detection)

def escape_html(text: str) -> str:
    """تهريب الأحرف الخاصة في HTML"""
    if not isinstance(text, str):
        text = str(text)
    # تهريب الأحرف الخاصة في HTML
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
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
    """إرسال رسالة إلى Telegram مع rate limiting لتجنب spam"""
    global _last_message_time
    
    try:
        target_chat_id = chat_id or TELEGRAM_CHAT_ID
        if not target_chat_id:
            logger.error("❌ No chat ID provided - يجب تحديد Chat ID")
            return False
        
        # Rate limiting: تأخير بسيط بين الرسائل لتجنب spam detection
        current_time = time.time()
        time_since_last_message = current_time - _last_message_time
        if time_since_last_message < _min_delay_between_messages:
            sleep_time = _min_delay_between_messages - time_since_last_message
            time.sleep(sleep_time)
        _last_message_time = time.time()
        
        # تحويل chat_id إلى string (للمجموعات قد يكون سالباً)
        chat_id_str = str(target_chat_id)
        
        payload = {
            "chat_id": chat_id_str,
            "text": message,
            "parse_mode": "HTML"  # استخدام HTML بدلاً من Markdown لتجنب مشاكل التهريب
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
                    logger.error("💡 الحل: أضف البوت إلى المجموعة مرة أخرى")
                elif 'bot was blocked' in error_description.lower() or 'kicked' in error_description.lower():
                    logger.error("❌ المشكلة: البوت تم طرده من المجموعة!")
                    logger.error("💡 الحل: أضف البوت إلى المجموعة مرة أخرى من إعدادات المجموعة")
                    logger.error("💡 لمنع الطرد: تأكد من أن البوت لديه صلاحية 'Send Messages' في إعدادات المجموعة")
                elif 'too many requests' in error_description.lower() or 'flood' in error_description.lower():
                    logger.error("❌ المشكلة: إرسال رسائل كثيرة جداً (Rate Limit)!")
                    logger.error("💡 الحل: البوت سيقلل من سرعة الإرسال تلقائياً")
                    # زيادة التأخير مؤقتاً
                    global _min_delay_between_messages
                    _min_delay_between_messages = min(_min_delay_between_messages * 2, 2.0)  # حد أقصى 2 ثانية
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
    
    message = f"🟢 <b>صفقة لونج (LONG)</b> 🟢\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 <b>أهداف الربح:</b>\n"
        if tp1:
            message += f"🎯 TP1: <code>{format_price(float(tp1))}</code>\n"
        if tp2:
            message += f"🎯 TP2: <code>{format_price(float(tp2))}</code>\n"
        if tp3:
            message += f"🎯 TP3: <code>{format_price(float(tp3))}</code>\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: <code>{format_price(float(stop_loss))}</code>"
    
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
    
    message = f"🔴 <b>صفقة شورت (SHORT)</b> 🔴\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 <b>أهداف الربح:</b>\n"
        if tp1:
            message += f"🎯 TP1: <code>{format_price(float(tp1))}</code>\n"
        if tp2:
            message += f"🎯 TP2: <code>{format_price(float(tp2))}</code>\n"
        if tp3:
            message += f"🎯 TP3: <code>{format_price(float(tp3))}</code>\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: <code>{format_price(float(stop_loss))}</code>"
    
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
    
    message = f"🟠 <b>صفقة لونج عكسي (LONG REVERSE)</b> 🟠\n"
    message += f"⚠️ <b>تم عكس الصفقة</b>\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 <b>أهداف الربح:</b>\n"
        if tp1:
            message += f"🎯 TP1: <code>{format_price(float(tp1))}</code>\n"
        if tp2:
            message += f"🎯 TP2: <code>{format_price(float(tp2))}</code>\n"
        if tp3:
            message += f"🎯 TP3: <code>{format_price(float(tp3))}</code>\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: <code>{format_price(float(stop_loss))}</code>"
    
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
    
    message = f"🟠 <b>صفقة شورت عكسي (SHORT REVERSE)</b> 🟠\n"
    message += f"⚠️ <b>تم عكس الصفقة</b>\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(timeframe)}\n\n"
    
    # عرض TP/SL المتاحة
    if tp1 or tp2 or tp3 or stop_loss:
        message += f"🎯 <b>أهداف الربح:</b>\n"
        if tp1:
            message += f"🎯 TP1: <code>{format_price(float(tp1))}</code>\n"
        if tp2:
            message += f"🎯 TP2: <code>{format_price(float(tp2))}</code>\n"
        if tp3:
            message += f"🎯 TP3: <code>{format_price(float(tp3))}</code>\n"
        message += "\n"
        if stop_loss:
            message += f"🛑 وقف الخسارة: <code>{format_price(float(stop_loss))}</code>"
    
    return message

def format_tp1_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الأول"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('tp1') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🎯✅ <b>تم ضرب الهدف الأول (TP1)</b> ✅🎯\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}"
    
    return message

def format_tp2_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الثاني"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('tp2') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🎯✅ <b>تم ضرب الهدف الثاني (TP2)</b> ✅🎯\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}"
    
    return message

def format_tp3_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الثالث"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('tp3') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🎯✅ <b>تم ضرب الهدف الثالث (TP3)</b> ✅🎯\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}"
    
    return message

def format_stop_loss_hit(data: dict) -> str:
    """تنسيق رسالة ضرب وقف الخسارة"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    exit_price = data.get('exit_price') or data.get('stop_loss') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    message = f"🛑😔 <b>تم ضرب وقف الخسارة (Stop Loss)</b> 😔🛑\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry_price:
        message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}"
    
    return message

def send_startup_message() -> bool:
    """إرسال رسالة بدء التشغيل"""
    try:
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🤖 <b>تم تشغيل البوت بنجاح!</b>\n\n"
        message += f"✅ البوت جاهز لاستقبال الإشارات\n"
        message += f"🕐 وقت البدء: {escape_html(current_time)}\n\n"
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
