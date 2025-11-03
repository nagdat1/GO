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
        return result.get('ok', False)
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False


def format_trading_alert(data):
    """تحويل بيانات TradingView إلى رسالة منسقة"""
    import re
    
    # إذا كانت البيانات نصاً بسيطاً
    if isinstance(data, str):
        message_text = data
    elif not data:
        return f"🔔 *تنبيه ورد*\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        # استخراج الرسالة المباشرة
        message_text = (data.get('message') or 
                       data.get('text') or 
                       data.get('msg') or 
                       data.get('alert_message') or "")
        
        if not message_text:
            message_text = str(data)
    
    # تحليل الرسالة واستخراج المعلومات
    if message_text:
        # استخراج نوع الأمر (sell, buy, etc)
        signal_type = "📊"
        message_upper = message_text.upper()
        
        if "SELL" in message_upper or "بيع" in message_text:
            signal_type = "🔴"
        elif "BUY" in message_upper or "LONG" in message_upper or "شراء" in message_text:
            signal_type = "🟢"
        elif "TP" in message_upper or "TAKE PROFIT" in message_upper:
            signal_type = "🎯"
        elif "SL" in message_upper or "STOP LOSS" in message_upper:
            signal_type = "🛑"
        
        # استخراج السعر
        price_match = re.search(r'@\s*([\d.]+)', message_text)
        price = price_match.group(1) if price_match else None
        
        # استخراج العملة/الرمز
        ticker_match = re.search(r'على\s+([A-Z]+)', message_text) or re.search(r'@\s*[\d.]+\s+على\s+([A-Z]+)', message_text)
        if not ticker_match:
            ticker_match = re.search(r'([A-Z]+USDT|[A-Z]+BTC|[A-Z]+ETH)', message_text.upper())
        ticker = ticker_match.group(1) if ticker_match else None
        
        # استخراج المركز
        position_match = re.search(r'المركز\s+.*?(\d+)', message_text) or re.search(r'position.*?(\d+)', message_text.upper())
        position = position_match.group(1) if position_match else None
        
        # تنظيف الرسالة من التفاصيل التقنية للاستراتيجية
        cleaned_message = message_text
        # إزالة تفاصيل الاستراتيجية بين الأقواس
        cleaned_message = re.sub(r'\([^)]+\):\s*', '', cleaned_message)
        cleaned_message = re.sub(r'nagdat\s*\([^)]+\):\s*', '', cleaned_message, flags=re.IGNORECASE)
        
        # بناء الرسالة المنسقة
        formatted_msg = f"{signal_type} *Trading Alert*\n"
        formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if ticker:
            formatted_msg += f"💰 *Symbol:* `{ticker}`\n"
        if price:
            formatted_msg += f"💵 *Price:* `{price}`\n"
        if position is not None:
            formatted_msg += f"📊 *Position:* `{position}`\n"
        
        formatted_msg += f"\n📝 *Details:*\n`{cleaned_message.strip()}`\n"
        formatted_msg += f"\n⏰ *Time:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
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
        # استقبال البيانات
        data = {}
        content_type = request.headers.get('Content-Type', '').lower()
        
        if 'application/json' in content_type:
            data = request.get_json() or {}
        else:
            form_data = dict(request.form)
            if form_data:
                data = form_data
            else:
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    try:
                        data = json.loads(raw_data)
                    except:
                        data = {"message": raw_data}
        
        if not data:
            data = {"message": "تنبيه ورد بدون بيانات"}
        
        # تحويل البيانات إلى رسالة
        message = format_trading_alert(data)
        
        # إرسال الرسالة إلى Telegram
        if send_telegram_message(message):
            return jsonify({
                "status": "success",
                "message": "Alert sent to Telegram successfully"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to send to Telegram"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """استقبال التنبيهات (endpoint قديم للتوافق)"""
    return personal_webhook(TELEGRAM_CHAT_ID)


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

