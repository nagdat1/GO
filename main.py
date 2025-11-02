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
import threading
import time

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️ إعدادات البوت - Bot Settings
# ═══════════════════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8361920962:AAFkWchaQStjaD09ayMI8VYm1vadr4p6zEY')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8169000394')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# الحصول على رابط المشروع من متغيرات البيئة
# Railway يوفر RAILWAY_PUBLIC_DOMAIN أو RAILWAY_STATIC_URL تلقائياً (نفس طريقة المشروع المرجعي)
RAILWAY_URL = os.getenv('RAILWAY_PUBLIC_DOMAIN') or os.getenv('RAILWAY_STATIC_URL')

# إضافة https إذا لم يكن موجوداً
if RAILWAY_URL and not RAILWAY_URL.startswith('http'):
    RAILWAY_URL = f"https://{RAILWAY_URL}"

# استخدام RAILWAY_URL مباشرة
PROJECT_URL = RAILWAY_URL

# طباعة معلومات Railway للتأكد
if PROJECT_URL:
    print(f"🚂 Railway URL detected at module load: {PROJECT_URL}")
else:
    print("⏳ Railway URL not available at module load, will detect on first HTTP request")

app = Flask(__name__)

# متغير لتتبع ما إذا تم إرسال رسالة الترحيب
_welcome_sent = False


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


def get_project_url():
    """
    الحصول على رابط المشروع من Railway (نفس طريقة المشروع المرجعي)
    Get project URL from Railway (same method as reference project)
    """
    # طريقة بسيطة ومباشرة مثل المشروع المرجعي
    railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN') or os.getenv('RAILWAY_STATIC_URL')
    
    if railway_url:
        if not railway_url.startswith('http'):
            railway_url = f"https://{railway_url}"
        return railway_url
    
    # إذا لم يتم العثور، استخدم PROJECT_URL (المحفوظ عند البدء)
    return PROJECT_URL


def send_welcome_message_with_url(project_url=None):
    """
    إرسال رسالة ترحيب مع رابط محدد
    Send welcome message with specified URL
    """
    if not project_url:
        project_url = get_project_url()
    
    webhook_url = f"{project_url}/personal/{TELEGRAM_CHAT_ID}/webhook"
    url_note = ""
    return _build_and_send_welcome_message(webhook_url, url_note, project_url)


def send_welcome_message():
    """
    إرسال رسالة ترحيب عند بدء التطبيق (نفس نهج المشروع المرجعي)
    Send welcome message when app starts (same approach as reference project)
    """
    # الحصول على الرابط من Railway (مثل المشروع المرجعي)
    project_url = get_project_url()
    
    if project_url:
        webhook_url = f"{project_url}/personal/{TELEGRAM_CHAT_ID}/webhook"
        url_note = ""
        print(f"✅ Railway URL detected: {project_url}")
    else:
        # إذا لم يتوفر الرابط، لن نرسل الرسالة الآن
        # سيتم الإرسال عند أول طلب HTTP
        print("⏳ Railway URL not available yet, will send welcome message on first HTTP request")
        return False
    
    return _build_and_send_welcome_message(webhook_url, url_note, project_url)


def _build_and_send_welcome_message(webhook_url, url_note, project_url=None):
    """
    بناء وإرسال رسالة الترحيب
    Build and send welcome message
    """
    try:
        
        # بناء الرسالة باستخدام HTML لتجنب مشاكل Markdown
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        welcome_msg = f"""🎉 <b>مرحباً! البوت يعمل الآن</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 <b>حالة البوت:</b> ✅ نشط
📊 <b>الخدمة:</b> TradingView ➜ Telegram
⏰ <b>وقت البدء:</b> <code>{time_str}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 <b>رابط Webhook (جاهز للنسخ والاستخدام):</b>

<code>{webhook_url}</code>

<a href="{webhook_url}">🔗 اضغط هنا للفتح</a>

📋 <b>انسخ الرابط أعلاه وضعه مباشرة في TradingView</b>{url_note}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 <b>تعليمات الاستخدام:</b>
1. انسخ الرابط أعلاه
2. افتح TradingView
3. اضغط على Alert 🔔
4. ضع الرابط في حقل Webhook URL
5. ابدأ بإرسال التنبيهات!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ البوت جاهز لاستقبال التنبيهات من TradingView
"""
        
        result = send_telegram_message(welcome_msg, parse_mode="HTML")
        if result and result.get('ok'):
            print("✅ Welcome message sent successfully!")
            print(f"📡 Webhook URL sent: {webhook_url}")
            return True
        else:
            print(f"⚠️ Failed to send welcome message: {result}")
            return False
    except Exception as e:
        print(f"❌ Error sending welcome message: {e}")
        import traceback
        traceback.print_exc()
        return False


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
    return jsonify({
        "service": "TradingView to Telegram Bot",
        "status": "running",
        "endpoints": {
            "/personal/<chat_id>/webhook": "POST - Receive TradingView alerts (personal link)",
            "/webhook": "POST - Receive TradingView alerts (legacy)",
            "/test": "GET - Send test message to Telegram",
            "/": "GET - This page"
        },
        "telegram_chat_id": TELEGRAM_CHAT_ID,
        "instructions": "Add /webhook URL to TradingView Alert webhook field"
    }), 200


def process_webhook_request():
    """
    معالجة طلب webhook من TradingView
    Process webhook request from TradingView
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
                "telegram_chat_id": TELEGRAM_CHAT_ID
            }), 200
            
    except Exception as e:
        print(f"❌ Error in webhook: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/personal/<chat_id>/webhook', methods=['POST', 'GET'])
def personal_webhook(chat_id):
    """
    استقبال التنبيهات من TradingView عبر رابط شخصي
    Receive alerts from TradingView via personal link
    """
    # التحقق من أن chat_id يتطابق مع TELEGRAM_CHAT_ID
    if chat_id != TELEGRAM_CHAT_ID:
        return jsonify({
            "status": "error",
            "message": "Invalid chat ID"
        }), 403
    
    return process_webhook_request()


@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """
    استقبال التنبيهات من TradingView (endpoint قديم للتوافق)
    Receive alerts from TradingView (legacy endpoint for compatibility)
    """
    return process_webhook_request()


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


# دالة لإرسال رسالة الترحيب عند بدء التطبيق
def initialize_bot():
    """
    تهيئة البوت وإرسال رسالة الترحيب
    Initialize bot and send welcome message
    """
    global _welcome_sent
    
    # تجنب إرسال الرسالة أكثر من مرة
    if _welcome_sent:
        return
    
    # الحصول على الرابط من Railway
    project_url = get_project_url()
    if project_url:
        webhook_url = f"{project_url}/personal/{TELEGRAM_CHAT_ID}/webhook"
    else:
        webhook_url = f"https://YOUR-RAILWAY-URL.railway.app/personal/{TELEGRAM_CHAT_ID}/webhook"
    
    print("=" * 60)
    print("🤖 TradingView to Telegram Bot")
    print("=" * 60)
    print(f"\n📱 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"\n🌐 Railway URL: {project_url if project_url else 'Not detected yet'}")
    print(f"📡 Webhook URL: {webhook_url}")
    if project_url:
        print(f"\n✅ Test endpoint: {project_url}/test")
        print(f"✅ Personal webhook: {webhook_url}")
    else:
        print(f"\n⏳ Railway URL will be detected on first HTTP request")
    print("=" * 60)
    
    # إرسال رسالة الترحيب
    print("\n📨 Sending welcome message...")
    if send_welcome_message():
        _welcome_sent = True
    print("=" * 60)


def send_welcome_on_startup():
    """
    إرسال رسالة الترحيب بعد فترة قصيرة من بدء التطبيق
    Send welcome message after a short delay from app startup
    """
    global _welcome_sent
    try:
        # انتظر 8 ثوانٍ لضمان أن التطبيق بدأ بشكل كامل وأن gunicorn جاهز
        print("⏳ Waiting 8 seconds before sending welcome message...")
        time.sleep(8)
        if not _welcome_sent:
            print("📨 Starting welcome message initialization...")
            initialize_bot()
        else:
            print("✅ Welcome message already sent")
    except Exception as e:
        print(f"❌ Error in welcome thread: {e}")


# بدء thread لإرسال رسالة الترحيب عند تحميل التطبيق
# يعمل مع gunicorn و Flask development server
welcome_thread = threading.Thread(target=send_welcome_on_startup, daemon=True)
welcome_thread.start()


# أيضاً، إرسال رسالة الترحيب عند أول طلب HTTP (كنسخة احتياطية)
@app.before_request
def before_first_request():
    """
    إرسال رسالة الترحيب عند أول طلب HTTP إذا لم يتم إرسالها بعد
    Send welcome message on first HTTP request if not sent yet
    """
    global _welcome_sent
    
    # إرسال رسالة الترحيب عند أول طلب إذا لم يتم إرسالها
    if not _welcome_sent:
        print("📨 First HTTP request detected, sending welcome message...")
        # الحصول على الرابط من Railway
        project_url = get_project_url()
        if project_url:
            send_welcome_message_with_url(project_url)
        else:
            initialize_bot()
        _welcome_sent = True


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # تهيئة البوت وإرسال رسالة الترحيب
    initialize_bot()
    
    # Railway uses gunicorn, but keep this for local testing
    app.run(host='0.0.0.0', port=port, debug=False)

