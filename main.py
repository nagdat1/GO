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
    # إذا كانت البيانات نصاً بسيطاً
    if isinstance(data, str):
        return f"🔔 *تنبيه*\n\n{data}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # إذا كانت البيانات فارغة
    if not data:
        return f"🔔 *تنبيه ورد*\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # استخراج الرسالة المباشرة
    message = (data.get('message') or 
               data.get('text') or 
               data.get('msg') or 
               data.get('alert_message') or "")
    
    if message and message.strip():
        return f"🔔 *تنبيه*\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # استخراج المعلومات من البيانات
    ticker = (data.get('ticker') or 
              data.get('symbol') or 
              data.get('{{ticker}}') or "")
    
    price = (data.get('close') or 
             data.get('price') or 
             data.get('{{close}}') or "")
    
    comment = (data.get('comment') or 
               data.get('strategy.order.comment') or 
               data.get('{{strategy.order.comment}}') or "")
    
    timeframe = (data.get('{{timeframe}}') or 
                 data.get('timeframe') or "")
    
    # تحديد نوع الإشارة
    signal_type = "📊"
    comment_upper = str(comment).upper()
    if any(word in comment_upper for word in ["BUY", "LONG", "شراء"]):
        signal_type = "🟢"
    elif any(word in comment_upper for word in ["SELL", "SHORT", "بيع"]):
        signal_type = "🔴"
    elif any(word in comment_upper for word in ["TP", "TAKE PROFIT", "جني ربح"]):
        signal_type = "🎯"
    elif any(word in comment_upper for word in ["SL", "STOP LOSS", "وقف خسارة"]):
        signal_type = "🛑"
    
    # بناء الرسالة
    formatted_msg = f"{signal_type} *Trading Alert*\n"
    formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if ticker:
        formatted_msg += f"💰 *Symbol:* `{ticker}`\n"
    if price:
        formatted_msg += f"💵 *Price:* `{price}`\n"
    if timeframe:
        formatted_msg += f"📈 *Timeframe:* `{timeframe}`\n"
    if comment:
        formatted_msg += f"📝 *Comment:*\n`{comment}`\n"
    
    formatted_msg += f"\n⏰ *Time:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
    formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return formatted_msg


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

