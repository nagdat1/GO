"""
TradingView to Telegram Bot
بوت تلجرام لاستقبال التنبيهات من TradingView
"""

from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime
import threading
import time

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️ إعدادات البوت
# ═══════════════════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8361920962:AAFkWchaQStjaD09ayMI8VYm1vadr4p6zEY')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8169000394')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# الحصول على رابط المشروع
RAILWAY_PUBLIC_DOMAIN = os.getenv('RAILWAY_PUBLIC_DOMAIN', 'go-production-e51a.up.railway.app')
PROJECT_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}" if not RAILWAY_PUBLIC_DOMAIN.startswith('http') else RAILWAY_PUBLIC_DOMAIN

app = Flask(__name__)

# متغير لتتبع ما إذا تم إرسال رسالة الترحيب
_welcome_sent = False


def send_telegram_message(message, parse_mode="Markdown"):
    """إرسال رسالة إلى تلجرام"""
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode
        }
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            print(f"   ✅ Telegram API: Message sent successfully")
            return True
        else:
            error_code = result.get('error_code', 'N/A')
            error_desc = result.get('description', 'Unknown error')
            print(f"   ❌ Telegram API Error {error_code}: {error_desc}")
            return False
    except Exception as e:
        print(f"   ❌ Exception sending message: {e}")
        import traceback
        traceback.print_exc()
        return False


def format_trading_alert(data):
    """
    تحويل بيانات TradingView إلى رسالة منسقة - نسخة احترافية
    يدعم: فتح صفقة، إغلاق، أهداف (TP1, TP2, TP3)، وقف خسارة
    متوافق مع رسائل مؤشر "غروب الاشارات"
    """
    import re
    
    # استخراج النص من البيانات
    if isinstance(data, str):
        message_text = data
    elif not data:
        return f"🔔 *تنبيه ورد*\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        message_text = (data.get('message') or 
               data.get('text') or 
               data.get('msg') or 
               data.get('alert_message') or 
               data.get('signal') or
               data.get('alert') or "")
    
        if not message_text:
            message_text = str(data)
    
    # إذا كانت الرسالة من المؤشر جاهزة ومنسقة بالفعل
    # المؤشر "غروب الاشارات" يرسل رسائل جاهزة ومكتملة
    if message_text and ('🟢🟢🟢' in message_text or '🔴🔴🔴' in message_text or 
                        '🎯✅🎯' in message_text or '🛑😔🛑' in message_text or 
                        '🔚📊🔚' in message_text or '*BUY SIGNAL*' in message_text or
                        '*SELL SIGNAL*' in message_text or '*TP1 - FIRST TARGET HIT*' in message_text or
                        '*TP2 - SECOND TARGET HIT*' in message_text or '*TP3 - THIRD TARGET HIT*' in message_text or
                        '*STOP LOSS HIT*' in message_text or '*POSITION CLOSED*' in message_text):
        # الرسالة من المؤشر جاهزة ومنسقة - نعيدها كما هي
        # المؤشر يرسل الرسالة مباشرة عبر alert() في Pine Script
        return message_text
    
    # تحليل الرسالة واستخراج المعلومات (للرسائل الأخرى غير المؤشر)
    if message_text:
        import re
        
        # تنظيف الرسالة من التفاصيل التقنية
        cleaned_message = message_text
        cleaned_message = re.sub(r'^[^:]*\([^)]+\):\s*', '', cleaned_message)
        cleaned_message = re.sub(r'nagdat\s*\([^)]+\):\s*', '', cleaned_message, flags=re.IGNORECASE)
        
        message_upper = cleaned_message.upper()
        
        # ═══════════════════════════════════════════════════════════════
        # تحديد نوع الإشارة
        # ═══════════════════════════════════════════════════════════════
        
        signal_category = None
        signal_emoji = "📊"
        signal_title = "Trading Alert"
        
        # 1. فتح صفقة BUY
        if any(word in message_upper for word in ["BUY", "LONG", "شراء"]) and not any(word in message_upper for word in ["CLOSE", "إغلاق", "TP", "SL"]):
            signal_category = "ENTRY_BUY"
            signal_emoji = "🟢"
            signal_title = "إشارة شراء"
        
        # 2. فتح صفقة SELL
        elif any(word in message_upper for word in ["SELL", "SHORT", "بيع"]) and not any(word in message_upper for word in ["CLOSE", "إغلاق", "TP", "SL"]):
            signal_category = "ENTRY_SELL"
            signal_emoji = "🔴"
            signal_title = "إشارة بيع"
        
        # 3. إغلاق صفقة
        elif any(word in message_upper for word in ["CLOSE", "إغلاق", "EXIT"]):
            signal_category = "CLOSE"
            signal_emoji = "🔒"
            signal_title = "إغلاق صفقة"
        
        # 4. هدف 1
        elif any(word in message_upper for word in ["TP1", "TARGET 1", "TAKE PROFIT 1", "الهدف 1", "هدف 1"]):
            signal_category = "TP1"
            signal_emoji = "🎯"
            signal_title = "تحقيق الهدف الأول"
        
        # 5. هدف 2
        elif any(word in message_upper for word in ["TP2", "TARGET 2", "TAKE PROFIT 2", "الهدف 2", "هدف 2"]):
            signal_category = "TP2"
            signal_emoji = "🎯🎯"
            signal_title = "تحقيق الهدف الثاني"
        
        # 6. هدف 3
        elif any(word in message_upper for word in ["TP3", "TARGET 3", "TAKE PROFIT 3", "الهدف 3", "هدف 3"]):
            signal_category = "TP3"
            signal_emoji = "🎯🎯🎯"
            signal_title = "تحقيق الهدف الثالث"
        
        # 7. وقف خسارة
        elif any(word in message_upper for word in ["STOP LOSS", "SL", "STOPLOSS", "وقف الخسارة", "ستوب لوز"]):
            signal_category = "STOP_LOSS"
            signal_emoji = "🛑"
            signal_title = "وقف الخسارة"
        
        # 8. هدف عام (TP بدون رقم)
        elif any(word in message_upper for word in ["TP", "TAKE PROFIT", "TARGET", "هدف"]):
            signal_category = "TP"
            signal_emoji = "🎯"
            signal_title = "تحقيق هدف"
        
        # ═══════════════════════════════════════════════════════════════
        # استخراج المعلومات
        # ═══════════════════════════════════════════════════════════════
        
        # استخراج السعر
        price_match = re.search(r'@\s*([\d.,]+)', cleaned_message)
        price = price_match.group(1).replace(',', '') if price_match else None
        
        # استخراج العملة
        ticker_match = re.search(r'على\s+([A-Z0-9]+)', cleaned_message) or re.search(r'([A-Z]+USDT|[A-Z]+BTC|[A-Z]+ETH|[A-Z]+BUSD)', cleaned_message.upper())
        ticker = ticker_match.group(1) if ticker_match else None
        
        # استخراج المركز
        position_match = re.search(r'المركز[^ه]*هو\s*(-?\d+\.?\d*)', cleaned_message) or re.search(r'position[^i]*is\s*(-?\d+\.?\d*)', cleaned_message, re.IGNORECASE)
        position = position_match.group(1) if position_match else None
        
        # استخراج الأهداف (TP1, TP2, TP3)
        tp1_match = re.search(r'TP1[:\s]*@?\s*([\d.,]+)', cleaned_message, re.IGNORECASE)
        tp2_match = re.search(r'TP2[:\s]*@?\s*([\d.,]+)', cleaned_message, re.IGNORECASE)
        tp3_match = re.search(r'TP3[:\s]*@?\s*([\d.,]+)', cleaned_message, re.IGNORECASE)
        
        tp1 = tp1_match.group(1).replace(',', '') if tp1_match else None
        tp2 = tp2_match.group(1).replace(',', '') if tp2_match else None
        tp3 = tp3_match.group(1).replace(',', '') if tp3_match else None
        
        # استخراج وقف الخسارة
        sl_match = re.search(r'SL[:\s]*@?\s*([\d.,]+)', cleaned_message, re.IGNORECASE) or re.search(r'STOP\s*LOSS[:\s]*@?\s*([\d.,]+)', cleaned_message, re.IGNORECASE)
        stop_loss = sl_match.group(1).replace(',', '') if sl_match else None
        
        # ═══════════════════════════════════════════════════════════════
        # بناء الرسالة حسب نوع الإشارة
        # ═══════════════════════════════════════════════════════════════
        
        formatted_msg = f"{signal_emoji} *{signal_title}*\n"
        formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # معلومات أساسية
        if ticker:
            formatted_msg += f"💰 *العملة:* `{ticker}`\n"
        
        if price:
            try:
                price_float = float(price)
                formatted_price = f"{price_float:,.4f}".rstrip('0').rstrip('.')
                formatted_msg += f"💵 *السعر:* `{formatted_price}`\n"
            except:
                formatted_msg += f"💵 *السعر:* `{price}`\n"
        
        # رسائل مخصصة حسب نوع الإشارة
        if signal_category == "ENTRY_BUY":
            formatted_msg += f"\n🟢 *نوع الصفقة:* شراء (LONG)\n"
            if tp1 or tp2 or tp3:
                formatted_msg += f"\n📍 *الأهداف:*\n"
                if tp1:
                    formatted_msg += f"   🎯 TP1: `{tp1}`\n"
                if tp2:
                    formatted_msg += f"   🎯 TP2: `{tp2}`\n"
                if tp3:
                    formatted_msg += f"   🎯 TP3: `{tp3}`\n"
            if stop_loss:
                formatted_msg += f"\n🛑 *وقف الخسارة:* `{stop_loss}`\n"
        
        elif signal_category == "ENTRY_SELL":
            formatted_msg += f"\n🔴 *نوع الصفقة:* بيع (SHORT)\n"
            if tp1 or tp2 or tp3:
                formatted_msg += f"\n📍 *الأهداف:*\n"
                if tp1:
                    formatted_msg += f"   🎯 TP1: `{tp1}`\n"
                if tp2:
                    formatted_msg += f"   🎯 TP2: `{tp2}`\n"
                if tp3:
                    formatted_msg += f"   🎯 TP3: `{tp3}`\n"
            if stop_loss:
                formatted_msg += f"\n🛑 *وقف الخسارة:* `{stop_loss}`\n"
        
        elif signal_category == "CLOSE":
            formatted_msg += f"\n🔒 *تم إغلاق الصفقة*\n"
            if position and float(position) == 0:
                formatted_msg += f"✅ *المركز الحالي:* صفر (تم الإغلاق بالكامل)\n"
        
        elif signal_category in ["TP1", "TP2", "TP3"]:
            tp_number = signal_category[-1]
            formatted_msg += f"\n🎉 *تهانينا! تم تحقيق الهدف {tp_number}*\n"
        
        elif signal_category == "STOP_LOSS":
            formatted_msg += f"\n🛑 *للأسف، تم ضرب وقف الخسارة*\n"
            formatted_msg += f"⚠️ *يُنصح بمراجعة الاستراتيجية*\n"
        
        # معلومات إضافية
        if position is not None and signal_category not in ["TP1", "TP2", "TP3", "STOP_LOSS"]:
            try:
                position_float = float(position)
                if position_float == 0:
                    formatted_msg += f"\n📊 *المركز:* لا يوجد\n"
                else:
                    formatted_msg += f"\n📊 *حجم المركز:* `{position_float}`\n"
            except:
                pass
        
        # الوقت
        formatted_msg += f"\n⏰ *الوقت:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
    formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return formatted_msg
    
    # إذا لم يتم تحليل الرسالة، أرسلها كما هي
    if message_text:
        return f"🔔 *تنبيه*\n\n{message_text}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        return f"🔔 *تنبيه ورد*\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@app.route('/', methods=['GET'])
def home():
    """الصفحة الرئيسية"""
    webhook_url = f"{PROJECT_URL}/personal/{TELEGRAM_CHAT_ID}/webhook"
    return jsonify({
        "service": "TradingView to Telegram Bot",
        "status": "running",
        "webhook_url": webhook_url
    }), 200


@app.route('/personal/<chat_id>/webhook', methods=['POST', 'GET'])
def personal_webhook(chat_id):
    """استقبال التنبيهات من TradingView"""
    # التحقق من chat_id
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        return jsonify({
            "status": "error",
            "message": "Invalid chat ID"
        }), 403
    
    if request.method == 'GET':
        return jsonify({
            "status": "online",
            "message": "Webhook is ready"
        }), 200
    
    try:
        print(f"📥 Webhook request received!")
        print(f"   Method: {request.method}")
        print(f"   Content-Type: {request.headers.get('Content-Type', 'N/A')}")
        print(f"   URL: {request.url}")
        
        # استقبال البيانات
        data = {}
        content_type = request.headers.get('Content-Type', '').lower()
        
        if 'application/json' in content_type:
            data = request.get_json() or {}
            print(f"   ✅ Got JSON data: {data}")
        else:
            form_data = dict(request.form)
            if form_data:
                data = form_data
                print(f"   ✅ Got form data: {data}")
            else:
                raw_data = request.get_data(as_text=True)
                print(f"   📝 Raw data: {raw_data[:200] if raw_data else 'Empty'}")
                if raw_data:
                    try:
                        data = json.loads(raw_data)
                        print(f"   ✅ Parsed JSON from raw: {data}")
                    except:
                        data = {"message": raw_data}
                        print(f"   ✅ Using raw data as message")
        
        if not data:
            data = {"message": "تنبيه ورد بدون بيانات"}
            print(f"   ⚠️ No data found, using default")
        
        print(f"   📊 Final data: {data}")
        
        # تحويل البيانات إلى رسالة
        message = format_trading_alert(data)
        print(f"   📝 Formatted message length: {len(message)} chars")
        
        # إرسال الرسالة إلى Telegram
        print(f"   📤 Sending to Telegram (Chat ID: {TELEGRAM_CHAT_ID})...")
        if send_telegram_message(message):
            print(f"   ✅ Alert sent successfully!")
            return jsonify({
                "status": "success",
                "message": "Alert sent to Telegram successfully"
            }), 200
        else:
            print(f"   ❌ Failed to send to Telegram")
            return jsonify({
                "status": "error",
                "message": "Failed to send to Telegram"
            }), 500
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """استقبال التنبيهات (endpoint قديم للتوافق)"""
    return personal_webhook(TELEGRAM_CHAT_ID)


@app.route('/test-alert', methods=['GET', 'POST'])
def test_alert():
    """اختبار إرسال إشارة"""
    test_data = {
        "message": "nagdat (Trailing, Open/Close, No Filtering, 7, 45, 10, 2, 10, 50, 30, 20, 10): تم تنفيذ الأمر sell @ 55556.723 على SCRUSDT. المركز الجديدة للإستراتيجية هو -55556.723"
    }
    
    # استخدام نفس منطق personal_webhook
    message = format_trading_alert(test_data)
    
    if send_telegram_message(message):
        return jsonify({
            "status": "success",
            "message": "Test alert sent successfully!",
            "test_data": test_data,
            "formatted_message": message
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to send test alert"
        }), 500


def send_welcome_message():
    """إرسال رسالة الترحيب عند البدء"""
    global _welcome_sent
    
    if _welcome_sent:
        return
    
    try:
        # انتظر قليلاً لضمان أن gunicorn جاهز
        time.sleep(3)
        
        if not _welcome_sent:
            webhook_url = f"{PROJECT_URL}/personal/{TELEGRAM_CHAT_ID}/webhook"
            welcome_msg = f"✅ *البوت يعمل الآن*\n\n🔗 *رابط Webhook:*\n`{webhook_url}`\n\n📋 *انسخ الرابط وضعه في TradingView*"
            
            if send_telegram_message(welcome_msg):
                print(f"✅ Welcome message sent with URL: {webhook_url}")
                _welcome_sent = True
            else:
                print(f"⚠️ Failed to send welcome message")
    except Exception as e:
        print(f"❌ Error sending welcome message: {e}")


# إرسال رسالة الترحيب عند بدء التطبيق
welcome_thread = threading.Thread(target=send_welcome_message, daemon=True)
welcome_thread.start()

# أيضاً عند أول طلب HTTP (كنسخة احتياطية)
@app.before_request
def before_first_request():
    """إرسال رسالة الترحيب عند أول طلب HTTP (نسخة احتياطية)"""
    global _welcome_sent
    
    if not _welcome_sent:
        try:
            webhook_url = f"{PROJECT_URL}/personal/{TELEGRAM_CHAT_ID}/webhook"
            welcome_msg = f"✅ *البوت يعمل الآن*\n\n🔗 *رابط Webhook:*\n`{webhook_url}`\n\n📋 *انسخ الرابط وضعه في TradingView*"
            
            if send_telegram_message(welcome_msg):
                print(f"✅ Welcome message sent with URL: {webhook_url}")
            
            _welcome_sent = True
        except Exception as e:
            print(f"❌ Error sending welcome message: {e}")
            _welcome_sent = True


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

