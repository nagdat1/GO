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
# Railway يوفر RAILWAY_PUBLIC_DOMAIN أو RAILWAY_STATIC_URL (في بعض الحالات يجب إضافته يدوياً)
# يمكن أيضاً استخدام PUBLIC_URL كبديل

# طباعة جميع المتغيرات للتحقق (في حالة debug)
def check_env_vars():
    """فحص متغيرات البيئة للتحقق من وجود RAILWAY_PUBLIC_DOMAIN"""
    railway_public = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    railway_static = os.getenv('RAILWAY_STATIC_URL')
    public_url = os.getenv('PUBLIC_URL')
    
    print("\n" + "=" * 70)
    print("🔍 Checking Environment Variables:")
    print("=" * 70)
    print(f"   RAILWAY_PUBLIC_DOMAIN = {railway_public or 'NOT SET'}")
    print(f"   RAILWAY_STATIC_URL = {railway_static or 'NOT SET'}")
    print(f"   PUBLIC_URL = {public_url or 'NOT SET'}")
    print("=" * 70 + "\n")
    
    return railway_public, railway_static, public_url

# فحص المتغيرات عند التحميل
check_env_vars()

RAILWAY_URL = (
    os.getenv('RAILWAY_PUBLIC_DOMAIN') or 
    os.getenv('RAILWAY_STATIC_URL') or 
    os.getenv('PUBLIC_URL') or
    os.getenv('RENDER_EXTERNAL_URL')  # دعم Render أيضاً
)

# إضافة https إذا لم يكن موجوداً
if RAILWAY_URL and not RAILWAY_URL.startswith('http'):
    RAILWAY_URL = f"https://{RAILWAY_URL}"

# استخدام RAILWAY_URL مباشرة
PROJECT_URL = RAILWAY_URL

# طباعة معلومات Railway للتأكد
if PROJECT_URL:
    print(f"🚂 Railway URL detected at module load: {PROJECT_URL}")
else:
    print("=" * 70)
    print("⚠️  RAILWAY URL NOT DETECTED!")
    print("=" * 70)
    print("\n📋 QUICK FIX - Add this in Railway Dashboard:")
    print("   1. Go to: Settings → Variables")
    print("   2. Click: + New Variable")
    print("   3. Name:  RAILWAY_PUBLIC_DOMAIN")
    print("   4. Value: your-app-name.up.railway.app")
    print("      (Get from: Settings → Domains)")
    print("\n   Alternative: Add PUBLIC_URL with full URL")
    print("=" * 70)
    print("\n⏳ Will try to detect from first HTTP request...")

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
        print(f"   📤 Telegram API URL: {url}")
        print(f"   📤 Chat ID: {TELEGRAM_CHAT_ID}")
        print(f"   📤 Message length: {len(message)} characters")
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        # طباعة الاستجابة الكاملة للتحقق
        print(f"   📬 Telegram API Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('ok'):
            print(f"   ✅ Telegram API: Message sent successfully")
            # التحقق من وجود result في الاستجابة
            if 'result' in result:
                print(f"   ✅ Message ID: {result['result'].get('message_id', 'N/A')}")
                print(f"   ✅ Chat: {result['result'].get('chat', {}).get('title', result['result'].get('chat', {}).get('username', 'N/A'))}")
        else:
            error_code = result.get('error_code', 'N/A')
            error_desc = result.get('description', 'Unknown error')
            print(f"   ❌ Telegram API Error Code: {error_code}")
            print(f"   ❌ Telegram API Error: {error_desc}")
            print(f"   ❌ Full response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # رسائل توضيحية للأخطاء الشائعة
            if error_code == 403:
                print(f"   ⚠️  Error 403: البوت محظور أو المستخدم لم يبدأ محادثة مع البوت")
                print(f"   💡 Solution: أرسل /start للبوت أولاً: @{(TELEGRAM_BOT_TOKEN.split(':')[0] if ':' in TELEGRAM_BOT_TOKEN else 'your_bot')}")
            elif error_code == 400:
                print(f"   ⚠️  Error 400: Chat ID غير صحيح أو غير موجود")
            elif error_code == 401:
                print(f"   ⚠️  Error 401: Bot Token غير صحيح أو منتهي الصلاحية")
        
        return result
    except Exception as e:
        print(f"   ❌ Exception sending message: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


def get_project_url():
    """
    الحصول على رابط المشروع من Railway أو من request
    Get project URL from Railway or from request
    """
    # أولاً: محاولة من متغيرات البيئة (قراءة مباشرة في كل مرة)
    railway_url = (
        os.getenv('RAILWAY_PUBLIC_DOMAIN') or 
        os.getenv('RAILWAY_STATIC_URL') or 
        os.getenv('PUBLIC_URL') or
        os.getenv('RENDER_EXTERNAL_URL')
    )
    
    if railway_url:
        if not railway_url.startswith('http'):
            railway_url = f"https://{railway_url}"
        print(f"✅ Found Railway URL from environment: {railway_url}")
        return railway_url
    
    # ثانياً: محاولة استخراج من request.host (إذا كان هناك request نشط)
    try:
        from flask import has_request_context, request
        if has_request_context() and request and request.host:
            host = request.host
            # إزالة رقم المنفذ إذا وُجد
            if ':' in host:
                host = host.split(':')[0]
            # التحقق من أنه رابط عام (وليس localhost)
            if 'localhost' not in host and '127.0.0.1' not in host and '0.0.0.0' not in host:
                # إذا كان يحتوي على railway.app، استخدمه مباشرة
                if 'railway.app' in host:
                    detected_url = f"https://{host}"
                    print(f"✅ Detected Railway URL from request.host: {detected_url}")
                    return detected_url
                # إذا كان يحتوي على go-production، استخدمه مباشرة
                elif 'go-production' in host:
                    detected_url = f"https://{host}"
                    print(f"✅ Detected URL from request.host: {detected_url}")
                    return detected_url
    except Exception as e:
        pass
    
    # ثالثاً: استخدم PROJECT_URL إذا كان محفوظاً
    if PROJECT_URL:
        return PROJECT_URL
    
    # رابعاً: حل بديل - استخدام القيمة الثابتة إذا كانت معروفة
    # (يمكن حذفها لاحقاً بعد إصلاح المتغير)
    known_url = "https://go-production.up.railway.app"
    print(f"⚠️ Using known URL as fallback: {known_url}")
    return known_url


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
        # إذا لم يتوفر الرابط، نرسل الرسالة مع رابط placeholder وتعليمات
        webhook_url = f"https://YOUR-RAILWAY-URL.railway.app/personal/{TELEGRAM_CHAT_ID}/webhook"
        url_note = "\n\n⚠️ <b>ملاحظة مهمة:</b>\nيرجى استبدال YOUR-RAILWAY-URL برابط مشروعك من Railway.\nاذهب إلى Settings → Variables وأضف:\n<code>RAILWAY_PUBLIC_DOMAIN = your-app-name.up.railway.app</code>"
        print("⚠️ Railway URL not available, sending welcome message with placeholder URL")
    
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
    يدعم جميع أنواع التنبيهات - Supports all alert types
    """
    # إذا كانت البيانات نصاً بسيطاً (string)، أرسلها مباشرة
    if isinstance(data, str):
        return f"🔔 *تنبيه*\n\n{data}"
    
    # إذا كانت البيانات فارغة أو None، أرسل رسالة افتراضية
    if not data:
        return f"🔔 *تنبيه ورد*\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # استخراج الرسالة المباشرة أولاً
    message = (data.get('message') or 
               data.get('text') or 
               data.get('msg') or 
               data.get('alert_message') or 
               data.get('alert') or "")
    
    # إذا كانت الرسالة موجودة وليست JSON فارغ، استخدمها مباشرة
    if message and not message.startswith("{") and message != "{}" and message.strip():
        # إذا كانت الرسالة نصية بسيطة، أرسلها مع تنسيق بسيط
        return f"🔔 *تنبيه*\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # استخراج المعلومات من البيانات
    ticker = (data.get('ticker') or 
              data.get('symbol') or 
              data.get('{{ticker}}') or 
              data.get('Ticker') or "")
    
    price = (data.get('close') or 
             data.get('price') or 
             data.get('{{close}}') or 
             data.get('Close') or "")
    
    comment = (data.get('comment') or 
               data.get('strategy.order.comment') or 
               data.get('{{strategy.order.comment}}') or 
               data.get('alert_message') or
               data.get('message') or "")
    
    time_str = (data.get('time') or 
                data.get('{{time}}') or 
                data.get('Time') or
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    timeframe = (data.get('{{timeframe}}') or 
                 data.get('timeframe') or 
                 data.get('Timeframe') or "")
    
    # إذا لم توجد معلومات أساسية، أرسل البيانات الخام بشكل منسق
    if not ticker and not price and not comment:
        # محاولة تحويل البيانات إلى نص
        try:
            data_str = json.dumps(data, indent=2, ensure_ascii=False)
            return f"🔔 *تنبيه ورد*\n\n```\n{data_str}\n```\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        except:
            return f"🔔 *تنبيه ورد*\n\n{str(data)}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # تحديد نوع الإشارة من التعليق
    signal_type = "📊"
    comment_upper = str(comment).upper()
    if any(word in comment_upper for word in ["BUY", "LONG", "LE", "شراء", "شرى"]):
        signal_type = "🟢"
    elif any(word in comment_upper for word in ["SELL", "SHORT", "SE", "بيع", "بيعي"]):
        signal_type = "🔴"
    elif any(word in comment_upper for word in ["TP", "TAKE PROFIT", "جني ربح"]):
        signal_type = "🎯"
    elif any(word in comment_upper for word in ["SL", "STOP LOSS", "وقف خسارة"]):
        signal_type = "🛑"
    elif any(word in comment_upper for word in ["CLOSE", "CLOSED", "إغلاق"]):
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
    
    formatted_msg += f"\n⏰ *Time:* `{time_str}`\n"
    formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return formatted_msg


@app.route('/', methods=['GET'])
def home():
    """الصفحة الرئيسية - Home page"""
    project_url = get_project_url()
    webhook_url = f"{project_url}/personal/{TELEGRAM_CHAT_ID}/webhook" if project_url else "Not detected"
    
    return jsonify({
        "service": "TradingView to Telegram Bot",
        "status": "running",
        "telegram_chat_id": TELEGRAM_CHAT_ID,
        "project_url": project_url or "Not detected",
        "webhook_url": webhook_url,
        "endpoints": {
            "/personal/<chat_id>/webhook": "POST - Receive TradingView alerts (personal link)",
            "/webhook": "POST - Receive TradingView alerts (legacy)",
            "/test": "GET - Send test message to Telegram",
            "/send-alert": "GET/POST - Send test alert to Telegram",
            "/send-welcome": "GET - Manually send welcome message",
            "/health": "GET - Health check",
            "/": "GET - This page"
        },
        "instructions": "Add webhook URL to TradingView Alert webhook field"
    }), 200


def process_webhook_request():
    """
    معالجة طلب webhook من TradingView
    Process webhook request from TradingView
    يدعم جميع أنواع التنبيهات - Supports all alert types
    """
    try:
        if request.method == 'POST':
            print(f"📥 Processing POST request...")
            
            # استقبال البيانات من TradingView
            data = {}
            content_type = request.headers.get('Content-Type', '').lower()
            raw_data = None
            
            print(f"   Content-Type: {content_type}")
            
            # محاولة قراءة البيانات الخام أولاً
            try:
                raw_data = request.get_data(as_text=True)
                print(f"   Raw data length: {len(raw_data) if raw_data else 0}")
                if raw_data:
                    print(f"   Raw data preview: {raw_data[:200]}")
            except Exception as e:
                print(f"   ⚠️ Could not read raw data: {e}")
            
            # محاولة قراءة JSON
            if 'application/json' in content_type or not content_type:
                try:
                    data = request.get_json()
                    if data:
                        print(f"   ✅ Got JSON data: {data}")
                    elif raw_data:
                        # محاولة تحليل JSON من البيانات الخام
                        try:
                            data = json.loads(raw_data)
                            print(f"   ✅ Parsed JSON from raw data: {data}")
                        except Exception as e:
                            print(f"   ⚠️ Could not parse JSON: {e}")
                except Exception as e:
                    print(f"   ⚠️ Could not get JSON: {e}")
            
            # محاولة قراءة Form Data
            if not data or (isinstance(data, dict) and len(data) == 0):
                try:
                    form_data = dict(request.form)
                    if form_data:
                        data = form_data
                        print(f"   ✅ Got form data: {data}")
                except Exception as e:
                    print(f"   ⚠️ Could not read form data: {e}")
            
            # محاولة قراءة Query Parameters
            if not data or (isinstance(data, dict) and len(data) == 0):
                try:
                    args_data = dict(request.args)
                    if args_data:
                        data = args_data
                        print(f"   ✅ Got query params: {data}")
                except Exception as e:
                    print(f"   ⚠️ Could not read query params: {e}")
            
            # إذا كانت البيانات نصاً خاماً، استخدمها مباشرة
            if (not data or (isinstance(data, dict) and len(data) == 0)) and raw_data:
                data = raw_data.strip()
                print(f"   ✅ Using raw data as string: {data[:100]}")
            
            # إذا كانت البيانات فارغة تماماً، استخدم رسالة افتراضية
            if not data or (isinstance(data, dict) and len(data) == 0):
                data = {"message": "تنبيه ورد بدون بيانات"}
                print(f"   ⚠️ No data found, using default message")
            
            print(f"📥 Final alert data: {data}")
            
            # تحويل البيانات إلى رسالة منسقة
            message = format_trading_alert(data)
            print(f"📝 Formatted message: {message[:200]}...")
            
            # إرسال الرسالة إلى Telegram
            print(f"📤 Sending to Telegram (Chat ID: {TELEGRAM_CHAT_ID})...")
            result = send_telegram_message(message)
            print(f"📬 Telegram API response: {result}")
            
            if result and result.get('ok'):
                print(f"✅ Alert sent successfully to Telegram!")
                return jsonify({
                    "status": "success",
                    "message": "Alert sent to Telegram successfully"
                }), 200
            else:
                error_msg = result.get('description', 'Unknown error') if result else 'No response'
                print(f"❌ Telegram API Error: {error_msg}")
                print(f"   Full response: {result}")
                return jsonify({
                    "status": "error",
                    "message": "Failed to send to Telegram",
                    "error": error_msg,
                    "full_error": result
                }), 500
                
        elif request.method == 'GET':
            # للتحقق من أن الخادم يعمل
            print(f"✅ GET request - Webhook is ready")
            return jsonify({
                "status": "online",
                "message": "Webhook is ready",
                "telegram_chat_id": TELEGRAM_CHAT_ID
            }), 200
            
    except Exception as e:
        print(f"❌ Error in webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/personal/<chat_id>/webhook', methods=['POST', 'GET'])
def personal_webhook(chat_id):
    """
    استقبال التنبيهات من TradingView عبر رابط شخصي
    Receive alerts from TradingView via personal link
    """
    print(f"📨 Webhook request received!")
    print(f"   Method: {request.method}")
    print(f"   Chat ID from URL: {chat_id}")
    print(f"   Expected Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"   Request URL: {request.url}")
    print(f"   Headers: {dict(request.headers)}")
    
    # التحقق من أن chat_id يتطابق مع TELEGRAM_CHAT_ID
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        print(f"❌ Invalid chat ID: {chat_id} != {TELEGRAM_CHAT_ID}")
        return jsonify({
            "status": "error",
            "message": f"Invalid chat ID. Expected: {TELEGRAM_CHAT_ID}, Got: {chat_id}"
        }), 403
    
    print(f"✅ Chat ID verified, processing webhook request...")
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


@app.route('/send-welcome', methods=['GET'])
def send_welcome_now():
    """
    إرسال رسالة الترحيب يدوياً للتحقق
    Manually send welcome message for testing
    """
    try:
        project_url = get_project_url()
        
        response_data = {
            "project_url_detected": project_url,
            "env_vars": {
                "RAILWAY_PUBLIC_DOMAIN": os.getenv('RAILWAY_PUBLIC_DOMAIN'),
                "RAILWAY_STATIC_URL": os.getenv('RAILWAY_STATIC_URL'),
                "PUBLIC_URL": os.getenv('PUBLIC_URL'),
            },
            "request_host": request.host if request else None
        }
        
        if project_url:
            result = send_welcome_message_with_url(project_url)
            response_data["status"] = "success" if result else "failed"
            response_data["message"] = "Welcome message sent!" if result else "Failed to send"
            return jsonify(response_data), 200
        else:
            response_data["status"] = "error"
            response_data["message"] = "Could not detect Railway URL. Please add RAILWAY_PUBLIC_DOMAIN to environment variables."
            return jsonify(response_data), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": str(e.__traceback__)
        }), 500


@app.route('/send-alert', methods=['POST', 'GET'])
def send_test_alert():
    """
    إرسال تنبيه تجريبي مباشرة إلى Telegram
    Send test alert directly to Telegram
    """
    try:
        # إذا كان POST، استخدم البيانات المرسلة
        if request.method == 'POST':
            try:
                alert_data = request.get_json() or dict(request.form) or dict(request.args)
            except:
                alert_data = {"message": "تنبيه تجريبي من endpoint /send-alert"}
        else:
            # إذا كان GET، أنشئ تنبيه تجريبي
            alert_data = {
                "ticker": "BTC/USDT",
                "price": "50000",
                "comment": "TEST ALERT - البوت يعمل بشكل صحيح ✅",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # تحويل البيانات إلى رسالة
        message = format_trading_alert(alert_data)
        
        # إرسال الرسالة
        result = send_telegram_message(message)
        
        if result and result.get('ok'):
            return jsonify({
                "status": "success",
                "message": "Test alert sent successfully!",
                "data_sent": alert_data,
                "formatted_message": message[:200] + "..." if len(message) > 200 else message
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to send alert",
                "error": result
            }), 500
            
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/test-webhook-direct', methods=['POST', 'GET'])
def test_webhook_direct():
    """
    اختبار webhook مباشرة - محاكاة طلب من TradingView
    Test webhook directly - simulate TradingView request
    """
    print("🧪 Testing webhook endpoint directly...")
    print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
    
    try:
        # استدعاء process_webhook_request مباشرة
        # محاكاة طلب POST مع بيانات تجريبية
        if request.method == 'GET':
            # للاختبار السريع، أنشئ طلب POST وهمي
            test_data = {
                "ticker": "BTC/USDT",
                "price": "50000",
                "comment": "TEST ALERT من endpoint /test-webhook-direct",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            # إرسال البيانات كـ JSON
            from flask import jsonify as flask_jsonify
            return flask_jsonify({
                "status": "info",
                "message": "Use POST method or call /personal/{chat_id}/webhook",
                "test_url": f"/personal/{TELEGRAM_CHAT_ID}/webhook",
                "instructions": "Send POST request to the webhook URL with your alert data"
            }), 200
        
        # إذا كان POST، استخدم process_webhook_request
        return process_webhook_request()
    except Exception as e:
        print(f"❌ Error in test_webhook_direct: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "TradingView to Telegram Bot"
    }), 200


@app.route('/verify-webhook', methods=['GET'])
def verify_webhook():
    """
    التحقق من صحة رابط Webhook
    Verify webhook URL is correct
    """
    project_url = get_project_url()
    correct_webhook = f"{project_url}/personal/{TELEGRAM_CHAT_ID}/webhook" if project_url else "Not detected"
    
    # بناء رابط متوقع
    expected_webhook = f"https://go-production.up.railway.app/personal/{TELEGRAM_CHAT_ID}/webhook"
    
    return jsonify({
        "status": "ok",
        "your_info": {
            "telegram_chat_id": TELEGRAM_CHAT_ID,
            "bot_username": "@nagdat232_bot",
        },
        "project_info": {
            "detected_url": project_url or "Not detected",
            "expected_url": "https://go-production.up.railway.app"
        },
        "webhook_urls": {
            "correct_webhook": correct_webhook,
            "expected_webhook": expected_webhook,
            "is_correct": correct_webhook == expected_webhook if project_url else False
        },
        "copy_this_url_for_tradingview": expected_webhook,
        "instructions": {
            "step_1": f"Copy this URL: {expected_webhook}",
            "step_2": "Open TradingView and go to Alert settings",
            "step_3": "Paste the URL in the 'Webhook URL' field",
            "step_4": "Save and test by sending an alert"
        },
        "important_note": "Make sure you have sent /start to @nagdat232_bot in Telegram first!"
    }), 200


@app.route('/check-env', methods=['GET'])
def check_env():
    """
    التحقق من متغيرات البيئة في الوقت الفعلي
    Check environment variables in real-time
    """
    railway_public = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    railway_static = os.getenv('RAILWAY_STATIC_URL')
    public_url = os.getenv('PUBLIC_URL')
    
    # قراءة جميع متغيرات Railway المتاحة
    all_railway_vars = {k: v for k, v in os.environ.items() if 'RAILWAY' in k}
    
    return jsonify({
        "status": "ok",
        "environment_variables": {
            "RAILWAY_PUBLIC_DOMAIN": railway_public or "NOT SET",
            "RAILWAY_STATIC_URL": railway_static or "NOT SET",
            "PUBLIC_URL": public_url or "NOT SET",
            "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
            "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN[:20] + "..." if TELEGRAM_BOT_TOKEN else "NOT SET"
        },
        "all_railway_variables": all_railway_vars,
        "detected_project_url": get_project_url() or "NOT DETECTED",
        "project_url_from_module": PROJECT_URL or "NOT SET",
        "recommendation": "If RAILWAY_PUBLIC_DOMAIN is NOT SET, add it in Railway Dashboard → Settings → Variables and redeploy the service."
    }), 200


@app.route('/get-bot-info', methods=['GET'])
def get_bot_info():
    """
    الحصول على معلومات البوت من Telegram
    Get bot information from Telegram
    """
    try:
        url = f"{TELEGRAM_API_URL}/getMe"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        return jsonify({
            "status": "ok" if result.get('ok') else "error",
            "bot_info": result.get('result', {}),
            "bot_username": result.get('result', {}).get('username', 'N/A'),
            "bot_name": result.get('result', {}).get('first_name', 'N/A'),
            "instructions": {
                "1": "Open Telegram and search for the bot username above",
                "2": "Click Start or send /start to the bot",
                "3": "Then try sending messages again"
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/test-telegram', methods=['GET'])
def test_telegram():
    """
    اختبار إرسال رسالة مباشرة إلى Telegram مع تفاصيل كاملة
    Test sending message directly to Telegram with full details
    """
    try:
        test_message = "🧪 Test message from bot\n\n✅ If you receive this, the bot is working correctly!"
        
        print("🧪 Testing Telegram connection...")
        print(f"   Bot Token: {TELEGRAM_BOT_TOKEN[:20]}...")
        print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
        
        result = send_telegram_message(test_message)
        
        response_data = {
            "status": "ok" if result.get('ok') else "error",
            "telegram_response": result,
            "bot_token_prefix": TELEGRAM_BOT_TOKEN[:20] + "..." if TELEGRAM_BOT_TOKEN else "NOT SET",
            "chat_id": TELEGRAM_CHAT_ID,
            "message_sent": test_message,
        }
        
        if result.get('ok'):
            chat_info = result.get('result', {}).get('chat', {})
            response_data["message"] = "✅ Test message sent successfully! Check your Telegram."
            response_data["bot_info"] = {
                "message_id": result.get('result', {}).get('message_id'),
                "chat": chat_info,
                "chat_id_received": chat_info.get('id'),
                "chat_username": chat_info.get('username'),
                "chat_name": f"{chat_info.get('first_name', '')} {chat_info.get('last_name', '')}".strip(),
            }
            
            # تحذير إذا كان Chat ID مختلف
            if str(chat_info.get('id')) != str(TELEGRAM_CHAT_ID):
                response_data["warning"] = f"⚠️ Chat ID mismatch! Expected: {TELEGRAM_CHAT_ID}, Got: {chat_info.get('id')}"
        else:
            error_code = result.get('error_code')
            error_desc = result.get('description', 'Unknown error')
            response_data["message"] = f"❌ Failed to send message: {error_desc}"
            response_data["error_code"] = error_code
            
            if error_code == 403:
                # الحصول على اسم البوت
                try:
                    bot_info_url = f"{TELEGRAM_API_URL}/getMe"
                    bot_response = requests.get(bot_info_url, timeout=5)
                    bot_result = bot_response.json()
                    bot_username = bot_result.get('result', {}).get('username', 'your_bot')
                except:
                    bot_username = 'your_bot'
                
                response_data["solution"] = f"❌ Error 403: You haven't started a conversation with the bot yet!\n\n💡 SOLUTION:\n1. Open Telegram\n2. Search for: @{bot_username}\n3. Click START or send /start\n4. Then try again"
            elif error_code == 400:
                response_data["solution"] = "❌ Error 400: Invalid Chat ID. Make sure TELEGRAM_CHAT_ID is correct.\n\n💡 How to get your Chat ID:\n1. Start a chat with @userinfobot on Telegram\n2. It will send you your Chat ID\n3. Update TELEGRAM_CHAT_ID in Railway Variables"
            elif error_code == 401:
                response_data["solution"] = "❌ Error 401: Invalid Bot Token. Check TELEGRAM_BOT_TOKEN in Railway Variables."
        
        return jsonify(response_data), 200 if result.get('ok') else 400
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


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
    إرسال رسالة الترحيب عند بدء التطبيق
    Send welcome message on application startup
    """
    global _welcome_sent
    try:
        # انتظر 3 ثوانٍ لضمان أن gunicorn جاهز
        print("⏳ Waiting 3 seconds for gunicorn to be ready...")
        time.sleep(3)
        
        if not _welcome_sent:
            print("📨 Attempting to send welcome message...")
            
            # محاولة إرسال رسالة الترحيب مباشرة (حتى لو لم يتوفر الرابط)
            result = send_welcome_message()
            
            if result:
                _welcome_sent = True
                print("✅ Welcome message sent successfully!")
            else:
                print("❌ Failed to send welcome message")
        else:
            print("✅ Welcome message already sent")
    except Exception as e:
        print(f"❌ Error in welcome thread: {e}")
        import traceback
        traceback.print_exc()


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
        try:
            print("📨 First HTTP request detected!")
            print(f"   Request host: {request.host}")
            print(f"   Request URL: {request.url}")
            
            # الحصول على الرابط من request.host
            project_url = get_project_url()
            
            if project_url:
                print(f"✅ Sending welcome message with URL: {project_url}")
                send_welcome_message_with_url(project_url)
            else:
                print("⚠️ Could not detect public URL from request")
                print("   Sending welcome message with placeholder URL")
                # إرسال الرسالة حتى لو لم يتوفر الرابط
                send_welcome_message()
            
            _welcome_sent = True
        except Exception as e:
            print(f"❌ Error in before_first_request: {e}")
            import traceback
            traceback.print_exc()
            _welcome_sent = True  # منع المحاولة مرة أخرى


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # تهيئة البوت وإرسال رسالة الترحيب
    initialize_bot()
    
    # Railway uses gunicorn, but keep this for local testing
    app.run(host='0.0.0.0', port=port, debug=False)

