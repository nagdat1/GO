"""
TradingView to Telegram Bot
بوت تلجرام لاستقبال التنبيهات من TradingView

جاهز للرفع على Railway.app
"""

from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️ إعدادات البوت - Bot Settings
# ═══════════════════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = "8361920962:AAFkWchaQStjaD09ayMI8VYm1vadr4p6zEY"
TELEGRAM_CHAT_ID = "8169000394"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

app = Flask(__name__)


def get_app_url():
    """
    الحصول على رابط التطبيق الفعلي
    Get the actual application URL
    """
    # محاولة الحصول من متغيرات البيئة (Railway)
    # Railway يوفر RAILWAY_PUBLIC_DOMAIN أو RAILWAY_STATIC_URL
    railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    if railway_domain:
        return f"https://{railway_domain}"
    
    railway_url = os.environ.get('RAILWAY_STATIC_URL')
    if railway_url:
        return railway_url
    
    # محاولة من متغيرات أخرى محتملة
    service_domain = os.environ.get('RAILWAY_SERVICE_DOMAIN')
    if service_domain:
        return f"https://{service_domain}"
    
    # محاولة الحصول من request عند وجوده (للتشغيل على السيرفر)
    try:
        from flask import has_request_context, request
        if has_request_context():
            # الحصول من الطلب الحالي
            return f"{request.scheme}://{request.host}"
    except:
        pass
    
    # إذا لم يكن متاحاً، استخدم localhost للتطوير المحلي
    port = os.environ.get('PORT', '5000')
    return f"http://localhost:{port}"


def send_telegram_message(message, parse_mode="Markdown"):
    """
    إرسال رسالة إلى تلجرام
    Send message to Telegram
    """
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode
        }
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return {"ok": False, "error": str(e)}


def format_trading_alert(data):
    """
    تحويل بيانات TradingView إلى رسالة منسقة وجميلة
    Convert TradingView data to formatted message
    """
    # استخراج الرسالة المباشرة أولاً
    message = (data.get('message') or 
               data.get('text') or 
               data.get('msg') or 
               data.get('alert_message') or "")
    
    # إذا كانت الرسالة موجودة وليست JSON، استخدمها مباشرة
    if message and not message.startswith("{") and message != "{}":
        return message
    
    # استخراج المعلومات من البيانات
    ticker = (data.get('ticker') or 
              data.get('symbol') or 
              data.get('{{ticker}}') or "")
    
    price = (data.get('close') or 
             data.get('price') or 
             data.get('{{close}}') or "")
    
    comment = (data.get('comment') or 
               data.get('strategy.order.comment') or 
               data.get('{{strategy.order.comment}}') or 
               data.get('alert_message') or "")
    
    time_str = (data.get('time') or 
                data.get('{{time}}') or 
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    timeframe = data.get('{{timeframe}}') or data.get('timeframe') or ""
    
    # تحديد نوع الإشارة من التعليق
    signal_type = "📊"
    if "BUY" in str(comment).upper() or "LONG" in str(comment).upper() or "LE" in str(comment):
        signal_type = "🟢"
    elif "SELL" in str(comment).upper() or "SHORT" in str(comment).upper() or "SE" in str(comment):
        signal_type = "🔴"
    elif "TP" in str(comment).upper() or "TAKE PROFIT" in str(comment).upper():
        signal_type = "🎯"
    elif "SL" in str(comment).upper() or "STOP LOSS" in str(comment).upper():
        signal_type = "🛑"
    elif "CLOSE" in str(comment).upper() or "CLOSED" in str(comment).upper():
        signal_type = "🔚"
    
    # بناء الرسالة بشكل منسق
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
    
    if time_str:
        formatted_msg += f"\n⏰ *Time:* `{time_str}`\n"
    
    formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return formatted_msg


@app.route('/', methods=['GET'])
def home():
    """الصفحة الرئيسية - Home page"""
    app_url = get_app_url()
    return jsonify({
        "service": "TradingView to Telegram Bot",
        "status": "running",
        "app_url": app_url,
        "endpoints": {
            "/webhook": f"{app_url}/webhook - POST - Receive TradingView alerts",
            "/test": f"{app_url}/test - GET - Send test message to Telegram",
            "/welcome": f"{app_url}/welcome - GET - Send welcome message",
            "/health": f"{app_url}/health - GET - Health check",
            "/": f"{app_url}/ - GET - This page"
        },
        "telegram_chat_id": TELEGRAM_CHAT_ID,
        "webhook_url": f"{app_url}/webhook",
        "instructions": f"Add {app_url}/webhook to TradingView Alert webhook field"
    }), 200


@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """
    استقبال التنبيهات من TradingView
    Receive alerts from TradingView
    """
    try:
        if request.method == 'POST':
            # استقبال البيانات من TradingView
            data = {}
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                data = request.get_json() or {}
            elif 'application/x-www-form-urlencoded' in content_type:
                data = dict(request.form)
            else:
                # محاولة قراءة كـ JSON أولاً
                try:
                    data = request.get_json() or {}
                except:
                    data = dict(request.form) or dict(request.args)
            
            # إذا كانت البيانات فارغة، حاول من query parameters
            if not data:
                data = dict(request.args)
            
            # تحويل البيانات إلى رسالة منسقة
            message = format_trading_alert(data)
            
            # إرسال الرسالة إلى Telegram
            result = send_telegram_message(message)
            
            if result and result.get('ok'):
                return jsonify({
                    "status": "success",
                    "message": "Alert sent to Telegram successfully"
                }), 200
            else:
                print(f"❌ Telegram API Error: {result}")
                return jsonify({
                    "status": "error",
                    "message": "Failed to send to Telegram",
                    "error": result
                }), 500
                
        elif request.method == 'GET':
            # للتحقق من أن الخادم يعمل
            return jsonify({
                "status": "online",
                "message": "Webhook is ready",
                "endpoint": "/webhook",
                "telegram_chat_id": TELEGRAM_CHAT_ID
            }), 200
            
    except Exception as e:
        print(f"❌ Error in webhook: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/test', methods=['GET'])
def test():
    """
    اختبار إرسال رسالة - Test message sending
    """
    test_message = """
✅ *Webhook Test* ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 *Bot Status:* Active
📊 *Service:* TradingView → Telegram
⏰ *Time:* {time}

✅ If you received this, your bot is working correctly!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """.format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    result = send_telegram_message(test_message)
    
    if result and result.get('ok'):
        return jsonify({
            "status": "success",
            "message": "Test message sent successfully!",
            "telegram_response": result
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to send test message",
            "error": result
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "TradingView to Telegram Bot"
    }), 200


def send_welcome_message():
    """
    إرسال رسالة ترحيب عند بدء البوت
    Send welcome message when bot starts
    """
    # الحصول على الرابط الفعلي
    app_url = get_app_url()
    webhook_url = f"{app_url}/webhook"
    test_url = f"{app_url}/test"
    welcome_url = f"{app_url}/welcome"
    
    welcome_message = """
🎉 *مرحباً! البوت يعمل الآن* 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 *حالة البوت:* ✅ نشط
📊 *الخدمة:* TradingView → Telegram
⏰ *وقت البدء:* {time}

✅ *البوت جاهز لاستقبال التنبيهات من TradingView!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 *روابط البوت:*

📡 *Webhook (للإشارات):*
`{webhook_url}`

🧪 *اختبار البوت:*
`{test_url}`

👋 *رسالة ترحيب:*
`{welcome_url}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 *تعليمات:*
1. افتح TradingView
2. اذهب إلى Alerts → Create Alert
3. فعّل Webhook URL
4. ضع هذا الرابط:
   `{webhook_url}`
5. احفظ الإعدادات! 🚀

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *ملاحظة:* هذا هو رابطك الفعلي - استخدمه مباشرة في TradingView!
    """.format(
        time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        webhook_url=webhook_url,
        test_url=test_url,
        welcome_url=welcome_url
    )
    
    try:
        result = send_telegram_message(welcome_message)
        if result and result.get('ok'):
            print("✅ Welcome message sent successfully!")
            return True
        else:
            print(f"⚠️ Warning: Could not send welcome message: {result}")
            return False
    except Exception as e:
        print(f"⚠️ Warning: Error sending welcome message: {e}")
        return False


@app.route('/welcome', methods=['GET'])
def welcome():
    """
    إرسال رسالة ترحيب - Send welcome message
    """
    send_welcome_message()
    return jsonify({
        "status": "success",
        "message": "Welcome message sent!"
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# 🚀 بدء البوت - Bot Startup
# ═══════════════════════════════════════════════════════════════════════════

# دالة لإرسال رسالة ترحيب عند بدء البوت
# Function to send welcome message when bot starts
def on_startup():
    """تشغيل عند بدء البوت"""
    # الحصول على الرابط الفعلي
    app_url = get_app_url()
    webhook_url = f"{app_url}/webhook"
    test_url = f"{app_url}/test"
    
    print("=" * 60)
    print("🤖 TradingView to Telegram Bot")
    print("=" * 60)
    print(f"\n📱 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"\n🌐 Server starting...")
    print(f"🔗 App URL: {app_url}")
    print(f"📡 Webhook URL: {webhook_url}")
    print(f"✅ To test: {test_url}")
    print("=" * 60)
    
    # إرسال رسالة ترحيب
    print("\n📨 Sending welcome message...")
    send_welcome_message()


# متغير لتتبع ما إذا تم إرسال رسالة الترحيب
_welcome_sent = False

@app.before_request
def check_welcome():
    """إرسال رسالة ترحيب عند أول طلب"""
    global _welcome_sent
    if not _welcome_sent:
        _welcome_sent = True
        # تشغيل في thread منفصل لتجنب تأخير الطلب
        import threading
        threading.Thread(target=on_startup, daemon=True).start()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # إرسال رسالة ترحيب عند التشغيل المحلي
    on_startup()
    
    print(f"\n🌐 Server starting on port: {port}")
    print("=" * 60)
    
    # Railway uses gunicorn, but keep this for local testing
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # عند التشغيل على Railway/Gunicorn
    # When running on Railway/Gunicorn
    import threading
    import time
    
    def delayed_startup():
        """بدء متأخر لضمان أن الخادم جاهز"""
        time.sleep(3)  # انتظار 3 ثواني لضمان أن الخادم جاهز تماماً
        on_startup()
    
    # تشغيل في thread منفصل
    startup_thread = threading.Thread(target=delayed_startup, daemon=True)
    startup_thread.start()

