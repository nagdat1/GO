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
TELEGRAM_GET_CHAT_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
TELEGRAM_GET_ME_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"

# Rate limiting: آخر وقت إرسال رسالة (لتجنب spam)
_last_message_time = 0
_min_delay_between_messages = 1.0  # 1 ثانية بين كل رسالة (آمن جداً)
_bot_kicked_chats = set()  # حفظ قائمة المجموعات التي طُرد منها البوت
_max_retries = 3  # عدد المحاولات

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

def format_timeframe(timeframe: str) -> str:
    """تحويل الإطار الزمني إلى تنسيق قابل للقراءة"""
    if not timeframe or timeframe == 'N/A':
        return 'N/A'
    
    # إذا كان رقم (دقائق)
    try:
        minutes = int(timeframe)
        
        # تحويل إلى تنسيق أفضل
        if minutes < 60:
            return f"{minutes} د"  # دقائق
        elif minutes < 1440:  # أقل من 24 ساعة
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours} س"  # ساعات فقط
            else:
                return f"{hours} س {remaining_minutes} د"  # ساعات ودقائق
        else:  # أيام
            days = minutes // 1440
            remaining_hours = (minutes % 1440) // 60
            if remaining_hours == 0:
                return f"{days} ي"
            else:
                return f"{days} ي {remaining_hours} س"
    except (ValueError, TypeError):
        # إذا كان نص (مثل "15D", "1H", "5M")
        timeframe_upper = str(timeframe).upper()
        
        # تحويل الاختصارات الشائعة
        if timeframe_upper.endswith('D'):
            days = int(timeframe_upper.replace('D', ''))
            return f"{days} ي"
        elif timeframe_upper.endswith('H'):
            hours = int(timeframe_upper.replace('H', ''))
            return f"{hours} س"
        elif timeframe_upper.endswith('M'):
            minutes = int(timeframe_upper.replace('M', ''))
            return f"{minutes} د"
        elif timeframe_upper.endswith('W'):
            weeks = int(timeframe_upper.replace('W', ''))
            return f"{weeks} أ"
        elif timeframe_upper.endswith('S'):
            seconds = int(timeframe_upper.replace('S', ''))
            if seconds < 60:
                return f"{seconds} ث"
            else:
                minutes = seconds // 60
                return f"{minutes} د"
        
        # إذا لم يكن تنسيق معروف، ارجعه كما هو
        return str(timeframe)

def check_bot_status(chat_id: str) -> bool:
    """التحقق من حالة البوت في المجموعة قبل الإرسال"""
    global _bot_kicked_chats
    
    chat_id_str = str(chat_id)
    
    # إذا كان البوت طُرد سابقاً، تحقق مرة أخرى بعد 5 دقائق
    if chat_id_str in _bot_kicked_chats:
        logger.warning(f"⚠️ البوت كان محظوراً سابقاً في {chat_id_str}، سيتم التحقق مرة أخرى...")
        # يمكن إضافة منطق للتحقق مرة أخرى بعد فترة
    
    try:
        # التحقق من حالة البوت في المجموعة
        response = requests.get(
            TELEGRAM_GET_CHAT_URL,
            params={"chat_id": chat_id_str},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                # البوت موجود في المجموعة
                if chat_id_str in _bot_kicked_chats:
                    _bot_kicked_chats.remove(chat_id_str)
                    logger.info(f"✅ البوت تم إضافته مرة أخرى إلى {chat_id_str}")
                return True
            else:
                error = result.get('description', '')
                if 'kicked' in error.lower() or 'not found' in error.lower():
                    _bot_kicked_chats.add(chat_id_str)
                    logger.error(f"❌ البوت غير موجود في المجموعة: {error}")
                    return False
        
        return True  # إذا فشل التحقق، حاول الإرسال على أي حال
    except Exception as e:
        logger.warning(f"⚠️ فشل التحقق من حالة البوت: {e}")
        return True  # إذا فشل التحقق، حاول الإرسال على أي حال

def send_message(message: str, chat_id: str = None, retry_count: int = 0) -> bool:
    """إرسال رسالة إلى Telegram مع rate limiting وتجنب spam"""
    global _last_message_time, _min_delay_between_messages, _max_retries
    
    try:
        target_chat_id = chat_id or TELEGRAM_CHAT_ID
        if not target_chat_id:
            logger.error("❌ No chat ID provided - يجب تحديد Chat ID")
            return False
        
        chat_id_str = str(target_chat_id)
        
        # التحقق من حالة البوت قبل الإرسال (فقط في المحاولة الأولى)
        if retry_count == 0:
            if not check_bot_status(chat_id_str):
                logger.error(f"❌ البوت غير موجود في المجموعة {chat_id_str} - لن يتم الإرسال")
                return False
        
        # Rate limiting: تأخير بسيط بين الرسائل لتجنب spam detection
        current_time = time.time()
        time_since_last_message = current_time - _last_message_time
        if time_since_last_message < _min_delay_between_messages:
            sleep_time = _min_delay_between_messages - time_since_last_message
            time.sleep(sleep_time)
        _last_message_time = time.time()
        
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
                    _bot_kicked_chats.add(chat_id_str)
                    logger.error("❌ المشكلة: البوت تم طرده من المجموعة!")
                    logger.error("💡 الحل: أضف البوت إلى المجموعة مرة أخرى من إعدادات المجموعة")
                    logger.error("💡 لمنع الطرد: تأكد من أن البوت لديه صلاحية 'Send Messages' في إعدادات المجموعة")
                    return False
                elif 'too many requests' in error_description.lower() or 'flood' in error_description.lower():
                    logger.error("❌ المشكلة: إرسال رسائل كثيرة جداً (Rate Limit)!")
                    logger.error("💡 الحل: البوت سيقلل من سرعة الإرسال تلقائياً")
                    # زيادة التأخير مؤقتاً بشكل تدريجي
                    _min_delay_between_messages = min(_min_delay_between_messages * 1.5, 3.0)  # حد أقصى 3 ثواني
                    # إعادة المحاولة بعد التأخير
                    if retry_count < _max_retries:
                        wait_time = _min_delay_between_messages * (retry_count + 1)
                        logger.info(f"⏳ انتظار {wait_time:.1f} ثانية قبل إعادة المحاولة...")
                        time.sleep(wait_time)
                        return send_message(message, chat_id, retry_count + 1)
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

def calculate_tp_sl(entry_price: float, is_long: bool = True) -> dict:
    """حساب TP/SL بناءً على entry_price (ATR-based calculation)"""
    # إعدادات ATR من المؤشر
    atr_length = 20
    profit_factor = 2.5
    
    # حساب ATR تقريبي (نستخدم نسبة تقريبية من entry_price)
    # ATR عادة يكون حوالي 0.5% - 2% من السعر حسب الإطار الزمني
    # سنستخدم 1% كقيمة تقريبية (يمكن تعديلها)
    estimated_atr_percent = 0.01  # 1% من السعر
    estimated_atr = entry_price * estimated_atr_percent
    
    if is_long:
        tp1 = entry_price + (1 * profit_factor * estimated_atr)
        tp2 = entry_price + (2 * profit_factor * estimated_atr)
        tp3 = entry_price + (3 * profit_factor * estimated_atr)
        stop_loss = entry_price - (1 * profit_factor * estimated_atr)
    else:
        tp1 = entry_price - (1 * profit_factor * estimated_atr)
        tp2 = entry_price - (2 * profit_factor * estimated_atr)
        tp3 = entry_price - (3 * profit_factor * estimated_atr)
        stop_loss = entry_price + (1 * profit_factor * estimated_atr)
    
    return {"tp1": tp1, "tp2": tp2, "tp3": tp3, "stop_loss": stop_loss}

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
    
    # إذا لم تكن TP/SL موجودة، حسابها بناءً على entry_price
    if not (tp1 or tp2 or tp3 or stop_loss) and entry_price:
        try:
            calculated = calculate_tp_sl(float(entry_price), is_long=True)
            tp1 = calculated['tp1']
            tp2 = calculated['tp2']
            tp3 = calculated['tp3']
            stop_loss = calculated['stop_loss']
        except:
            pass
    
    message = f"🟢 <b>صفقة لونج (LONG)</b> 🟢\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(format_timeframe(timeframe))}\n\n"
    
    # عرض TP/SL المتاحة
    has_tp_sl = tp1 or tp2 or tp3 or stop_loss
    if has_tp_sl:
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
    else:
        # إذا لم تكن TP/SL موجودة، أضف رسالة توضيحية
        message += f"⚠️ <i>ملاحظة: TP/SL غير متاحة</i>\n"
        message += f"💡 <i>الحل: تأكد من أسماء الـ plots في التنبيه</i>\n"
        message += f"📝 <i>الأسماء الشائعة: \"TP Line 1\", \"TP1\", \"SL Line\", \"Stop Loss\"</i>"
    
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
    
    # إذا لم تكن TP/SL موجودة، حسابها بناءً على entry_price
    if not (tp1 or tp2 or tp3 or stop_loss) and entry_price:
        try:
            calculated = calculate_tp_sl(float(entry_price), is_long=False)
            tp1 = calculated['tp1']
            tp2 = calculated['tp2']
            tp3 = calculated['tp3']
            stop_loss = calculated['stop_loss']
        except:
            pass
    
    message = f"🔴 <b>صفقة شورت (SHORT)</b> 🔴\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(format_timeframe(timeframe))}\n\n"
    
    # عرض TP/SL المتاحة
    has_tp_sl = tp1 or tp2 or tp3 or stop_loss
    if has_tp_sl:
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
    else:
        message += f"⚠️ <i>ملاحظة: TP/SL غير متاحة</i>\n"
        message += f"💡 <i>الحل: تأكد من أسماء الـ plots في التنبيه</i>\n"
        message += f"📝 <i>الأسماء الشائعة: \"TP Line 1\", \"TP1\", \"SL Line\", \"Stop Loss\"</i>"
    
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
    
    # إذا لم تكن TP/SL موجودة، حسابها بناءً على entry_price
    if not (tp1 or tp2 or tp3 or stop_loss) and entry_price:
        try:
            calculated = calculate_tp_sl(float(entry_price), is_long=True)
            tp1 = calculated['tp1']
            tp2 = calculated['tp2']
            tp3 = calculated['tp3']
            stop_loss = calculated['stop_loss']
        except:
            pass
    
    message = f"🟠 <b>صفقة لونج عكسي (LONG REVERSE)</b> 🟠\n"
    message += f"⚠️ <b>تم عكس الصفقة</b>\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(format_timeframe(timeframe))}\n\n"
    
    # عرض TP/SL المتاحة
    has_tp_sl = tp1 or tp2 or tp3 or stop_loss
    if has_tp_sl:
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
    else:
        message += f"⚠️ <i>ملاحظة: TP/SL غير متاحة</i>\n"
        message += f"💡 <i>الحل: تأكد من أسماء الـ plots في التنبيه</i>\n"
        message += f"📝 <i>الأسماء الشائعة: \"TP Line 1\", \"TP1\", \"SL Line\", \"Stop Loss\"</i>"
    
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
    
    # إذا لم تكن TP/SL موجودة، حسابها بناءً على entry_price
    if not (tp1 or tp2 or tp3 or stop_loss) and entry_price:
        try:
            calculated = calculate_tp_sl(float(entry_price), is_long=False)
            tp1 = calculated['tp1']
            tp2 = calculated['tp2']
            tp3 = calculated['tp3']
            stop_loss = calculated['stop_loss']
        except:
            pass
    
    message = f"🟠 <b>صفقة شورت عكسي (SHORT REVERSE)</b> 🟠\n"
    message += f"⚠️ <b>تم عكس الصفقة</b>\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    message += f"⏰ الوقت: {escape_html(time)}\n"
    message += f"📈 الإطار الزمني: {escape_html(format_timeframe(timeframe))}\n\n"
    
    # عرض TP/SL المتاحة
    has_tp_sl = tp1 or tp2 or tp3 or stop_loss
    if has_tp_sl:
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
    else:
        message += f"⚠️ <i>ملاحظة: TP/SL غير متاحة</i>\n"
        message += f"💡 <i>الحل: تأكد من أسماء الـ plots في التنبيه</i>\n"
        message += f"📝 <i>الأسماء الشائعة: \"TP Line 1\", \"TP1\", \"SL Line\", \"Stop Loss\"</i>"
    
    return message

def format_tp1_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الأول"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    tp1 = data.get('tp1')
    exit_price = data.get('exit_price') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    # تحسين: إذا كان exit_price = entry_price، استخدم tp1 أو close
    if exit_price and entry_price:
        try:
            if abs(float(exit_price) - float(entry_price)) < 0.01:  # تقريباً نفس القيمة
                if tp1:
                    exit_price = tp1
                    logger.info(f"✅ TP1 Hit: تم استخدام TP1 كسعر خروج لأن exit_price = entry_price")
        except (ValueError, TypeError):
            pass
    
    message = f"🎯✅ <b>تم ضرب الهدف الأول (TP1)</b> ✅🎯\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    
    # عرض سعر الدخول فقط إذا كان مختلفاً عن سعر الخروج
    if entry_price and exit_price:
        try:
            if abs(float(entry_price) - float(exit_price)) > 0.01:
                message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
        except (ValueError, TypeError):
            message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    
    if tp1:
        message += f"🎯 TP1: <code>{format_price(float(tp1))}</code>\n"
    
    message += f"⏰ الوقت: {escape_html(time)}"
    
    return message

def format_tp2_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الثاني"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    tp2 = data.get('tp2')
    exit_price = data.get('exit_price') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    # تحسين: إذا كان exit_price = entry_price، استخدم tp2
    if exit_price and entry_price:
        try:
            if abs(float(exit_price) - float(entry_price)) < 0.01:
                if tp2:
                    exit_price = tp2
                    logger.info(f"✅ TP2 Hit: تم استخدام TP2 كسعر خروج لأن exit_price = entry_price")
        except (ValueError, TypeError):
            pass
    
    message = f"🎯✅ <b>تم ضرب الهدف الثاني (TP2)</b> ✅🎯\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    
    # عرض سعر الدخول فقط إذا كان مختلفاً عن سعر الخروج
    if entry_price and exit_price:
        try:
            if abs(float(entry_price) - float(exit_price)) > 0.01:
                message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
        except (ValueError, TypeError):
            message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    
    if tp2:
        message += f"🎯 TP2: <code>{format_price(float(tp2))}</code>\n"
    
    message += f"⏰ الوقت: {escape_html(time)}"
    
    return message

def format_tp3_hit(data: dict) -> str:
    """تنسيق رسالة ضرب الهدف الثالث"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    tp3 = data.get('tp3')
    exit_price = data.get('exit_price') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    # تحسين: إذا كان exit_price = entry_price، استخدم tp3
    if exit_price and entry_price:
        try:
            if abs(float(exit_price) - float(entry_price)) < 0.01:
                if tp3:
                    exit_price = tp3
                    logger.info(f"✅ TP3 Hit: تم استخدام TP3 كسعر خروج لأن exit_price = entry_price")
        except (ValueError, TypeError):
            pass
    
    message = f"🎯✅ <b>تم ضرب الهدف الثالث (TP3)</b> ✅🎯\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    
    # عرض سعر الدخول فقط إذا كان مختلفاً عن سعر الخروج
    if entry_price and exit_price:
        try:
            if abs(float(entry_price) - float(exit_price)) > 0.01:
                message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
        except (ValueError, TypeError):
            message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    
    if tp3:
        message += f"🎯 TP3: <code>{format_price(float(tp3))}</code>\n"
    
    message += f"⏰ الوقت: {escape_html(time)}"
    
    return message

def format_stop_loss_hit(data: dict) -> str:
    """تنسيق رسالة ضرب وقف الخسارة"""
    symbol = data.get('symbol', 'N/A')
    entry_price = data.get('entry_price', 0)
    stop_loss = data.get('stop_loss')
    exit_price = data.get('exit_price') or data.get('price', 0)
    time = data.get('time', 'N/A')
    
    # تحسين: إذا كان exit_price = entry_price، استخدم stop_loss
    if exit_price and entry_price:
        try:
            if abs(float(exit_price) - float(entry_price)) < 0.01:
                if stop_loss:
                    exit_price = stop_loss
                    logger.info(f"✅ SL Hit: تم استخدام SL كسعر خروج لأن exit_price = entry_price")
        except (ValueError, TypeError):
            pass
    
    message = f"🛑😔 <b>تم ضرب وقف الخسارة (Stop Loss)</b> 😔🛑\n\n"
    message += f"📊 الرمز: {escape_html(symbol)}\n"
    
    # عرض سعر الدخول فقط إذا كان مختلفاً عن سعر الخروج
    if entry_price and exit_price:
        try:
            if abs(float(entry_price) - float(exit_price)) > 0.01:
                message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
        except (ValueError, TypeError):
            message += f"💰 سعر الدخول: <code>{format_price(entry_price)}</code>\n"
    
    message += f"💰 سعر الخروج: <code>{format_price(exit_price)}</code>\n"
    
    if stop_loss:
        message += f"🛑 Stop Loss: <code>{format_price(float(stop_loss))}</code>\n"
    
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
