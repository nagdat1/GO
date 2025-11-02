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
    الحصول على رابط التطبيق الفعلي من Railway
    Get the actual application URL from Railway
    """
    global _app_url_detected
    
    # استخدام الرابط المكتشف من الطلب الأول
    if _app_url_detected:
        return _app_url_detected
    
    # محاولة الحصول من متغيرات البيئة (Railway) - الأولوية الأولى
    railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RAILWAY_STATIC_URL')
    if railway_url:
        # التأكد من وجود https
        if not railway_url.startswith('http'):
            railway_url = f"https://{railway_url}"
        _app_url_detected = railway_url
        print(f"✅ Found Railway URL from environment: {railway_url}")
        return railway_url
    
    # محاولة الحصول من request عند وجوده (للتشغيل على السيرفر)
    try:
        from flask import has_request_context, request
        if has_request_context() and request:
            scheme = request.scheme if hasattr(request, 'scheme') and request.scheme else 'https'
            host = request.host if hasattr(request, 'host') else None
            if host and host != 'localhost' and 'localhost' not in host and '127.0.0.1' not in host:
                detected = f"{scheme}://{host}"
                _app_url_detected = detected
                print(f"✅ Detected URL from request: {detected}")
                return detected
    except:
        pass
    
    # إذا لم يكن متاحاً، استخدم localhost للتطوير المحلي
    port = os.environ.get('PORT', '5000')
    return f"http://localhost:{port}"


def send_welcome_with_url():
    """إرسال رسالة ترحيب مع الرابط المكتشف (deprecated - use check_welcome instead)"""
    send_welcome_message()


def send_telegram_message(message, parse_mode="Markdown"):
    """
    إرسال رسالة إلى تلجرام
    Send message to Telegram
    """
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        
        # إضافة parse_mode فقط إذا لم يكن None
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        print(f"📤 Sending message to Telegram...")
        print(f"   URL: {url}")
        print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
        print(f"   Parse mode: {parse_mode}")
        print(f"   Message length: {len(message)} chars")
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        print(f"📥 Telegram response: {result}")
        
        if result.get('ok'):
            print(f"✅ Message sent successfully!")
        else:
            print(f"❌ Failed to send message: {result.get('description')}")
        
        return result
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        import traceback
        traceback.print_exc()
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
    """الصفحة الرئيسية - ترسل الرسالة تلقائياً"""
    # عند فتح الصفحة الرئيسية، ترسل الرسالة مباشرة
    return get_webhook_url()


@app.route('/personal/<chat_id>/webhook', methods=['POST', 'GET'])
def personal_webhook(chat_id):
    """
    Webhook مخصص لكل مستخدم باستخدام Chat ID
    Personal webhook for each user using Chat ID
    """
    try:
        # التحقق من Chat ID (اختياري - للأمان)
        # يمكنك إزالة هذا الشرط إذا أردت أن يكون مفتوحاً
        if chat_id != TELEGRAM_CHAT_ID:
            print(f"⚠️ Warning: Webhook called with different chat_id: {chat_id}")
        
        if request.method == 'POST':
            # استقبال البيانات من TradingView
            data = {}
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                data = request.get_json() or {}
            elif 'application/x-www-form-urlencoded' in content_type:
                data = dict(request.form)
            else:
                try:
                    data = request.get_json() or {}
                except:
                    data = dict(request.form) or dict(request.args)
            
            if not data:
                data = dict(request.args)
            
            # تحويل البيانات إلى رسالة منسقة
            message = format_trading_alert(data)
            
            # إرسال الرسالة إلى Telegram باستخدام Chat ID المحدد
            original_chat_id = TELEGRAM_CHAT_ID
            try:
                # استخدام Chat ID من الرابط
                url = f"{TELEGRAM_API_URL}/sendMessage"
                telegram_data = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                response = requests.post(url, json=telegram_data, timeout=10)
                result = response.json()
            except Exception as e:
                print(f"❌ Error sending to chat_id {chat_id}: {e}")
                result = {"ok": False, "error": str(e)}
            
            if result and result.get('ok'):
                return jsonify({
                    "status": "success",
                    "message": f"Alert sent to Telegram (chat_id: {chat_id})",
                    "chat_id": chat_id
                }), 200
            else:
                print(f"❌ Telegram API Error: {result}")
                return jsonify({
                    "status": "error",
                    "message": f"Failed to send to Telegram (chat_id: {chat_id})",
                    "error": result
                }), 500
                
        elif request.method == 'GET':
            # الحصول على الرابط من الطلب الحالي
            try:
                scheme = request.scheme if request.scheme else 'https'
                host = request.host
                current_url = f"{scheme}://{host}"
            except:
                current_url = get_app_url()
            
            webhook_url = f"{current_url}/personal/{chat_id}/webhook"
            
            return jsonify({
                "status": "online",
                "message": "Personal webhook is ready",
                "endpoint": f"/personal/{chat_id}/webhook",
                "chat_id": chat_id,
                "webhook_url": webhook_url,
                "current_host": request.host if hasattr(request, 'host') else "unknown"
            }), 200
            
    except Exception as e:
        print(f"❌ Error in personal webhook: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


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


@app.route('/send-welcome', methods=['GET'])
def send_welcome_endpoint():
    """
    إرسال رسالة ترحيب مباشرة
    Send welcome message directly
    """
    # الحصول على الرابط من الطلب الحالي
    try:
        scheme = request.scheme if hasattr(request, 'scheme') and request.scheme else 'https'
        host = request.host if hasattr(request, 'host') else None
        
        if host and host != 'localhost' and 'localhost' not in host and '127.0.0.1' not in host:
            global _app_url_detected
            _app_url_detected = f"{scheme}://{host}"
            print(f"✅ Detected URL in /send-welcome: {_app_url_detected}")
    except Exception as e:
        print(f"⚠️ Error detecting URL: {e}")
    
    result = send_welcome_message()
    return jsonify({
        "status": "success" if result else "warning",
        "message": "Welcome message sent!" if result else "Welcome message not sent (check logs)",
        "detected_url": _app_url_detected,
        "chat_id": TELEGRAM_CHAT_ID
    }), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "TradingView to Telegram Bot"
    }), 200


@app.route('/test-bot', methods=['GET'])
def test_bot():
    """
    اختبار صحة Bot Token و Chat ID
    Test Bot Token and Chat ID validity
    """
    results = {}
    
    # 1. اختبار صحة Bot Token
    try:
        url = f"{TELEGRAM_API_URL}/getMe"
        response = requests.get(url, timeout=10)
        bot_info = response.json()
        results['bot_token_test'] = {
            'valid': bot_info.get('ok', False),
            'bot_info': bot_info.get('result', {}) if bot_info.get('ok') else None,
            'error': bot_info.get('description') if not bot_info.get('ok') else None
        }
    except Exception as e:
        results['bot_token_test'] = {
            'valid': False,
            'error': str(e)
        }
    
    # 2. اختبار إرسال رسالة بسيطة (بدون Markdown)
    try:
        test_message = f"🧪 رسالة اختبار\nTest Message\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_result = send_telegram_message(test_message, parse_mode=None)
        
        results['send_test'] = {
            'success': send_result.get('ok', False) if send_result else False,
            'response': send_result,
            'chat_id': TELEGRAM_CHAT_ID
        }
    except Exception as e:
        results['send_test'] = {
            'success': False,
            'error': str(e)
        }
    
    return jsonify({
        "test_results": results,
        "bot_token": f"{TELEGRAM_BOT_TOKEN[:15]}...",
        "chat_id": TELEGRAM_CHAT_ID,
        "telegram_api_url": TELEGRAM_API_URL
    }), 200


@app.route('/simple-test', methods=['GET'])
def simple_test():
    """
    اختبار بسيط جداً - إرسال رسالة بدون أي تنسيق
    Very simple test - send plain text message
    """
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        simple_message = f"Simple test {datetime.now().strftime('%H:%M:%S')}"
        
        # إرسال بدون parse_mode
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": simple_message
        }
        
        print(f"🔍 Testing simple message...")
        print(f"URL: {url}")
        print(f"Data: {data}")
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        print(f"Response: {result}")
        
        return jsonify({
            "status": "success" if result.get('ok') else "error",
            "result": result,
            "message": "Check logs for details"
        }), 200 if result.get('ok') else 500
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error: {error_details}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": error_details
        }), 500


@app.route('/diagnose', methods=['GET'])
def diagnose():
    """
    تشخيص شامل للبوت - يفحص كل شيء
    Full bot diagnostics - checks everything
    """
    diagnosis = {
        "bot_token_check": {},
        "chat_id_check": {},
        "message_test": {},
        "recent_chats": {}
    }
    
    # 1. فحص Bot Token
    try:
        url = f"{TELEGRAM_API_URL}/getMe"
        response = requests.get(url, timeout=10)
        bot_result = response.json()
        
        diagnosis["bot_token_check"] = {
            "valid": bot_result.get('ok', False),
            "bot_info": bot_result.get('result') if bot_result.get('ok') else None,
            "error": bot_result.get('description') if not bot_result.get('ok') else None
        }
    except Exception as e:
        diagnosis["bot_token_check"] = {
            "valid": False,
            "error": str(e)
        }
    
    # 2. فحص الرسائل الحديثة للحصول على Chat IDs الصحيحة
    try:
        url = f"{TELEGRAM_API_URL}/getUpdates"
        response = requests.get(url, timeout=10)
        updates_result = response.json()
        
        if updates_result.get('ok'):
            updates = updates_result.get('result', [])
            chat_ids = set()
            chat_details = []
            
            for update in updates:
                if 'message' in update:
                    chat = update['message']['chat']
                    chat_id = str(chat['id'])
                    if chat_id not in chat_ids:
                        chat_ids.add(chat_id)
                        chat_details.append({
                            "chat_id": chat_id,
                            "type": chat.get('type'),
                            "username": chat.get('username'),
                            "first_name": chat.get('first_name'),
                            "last_name": chat.get('last_name')
                        })
            
            diagnosis["recent_chats"] = {
                "found": len(chat_details),
                "chats": chat_details,
                "configured_chat_id": TELEGRAM_CHAT_ID,
                "configured_chat_found": TELEGRAM_CHAT_ID in chat_ids
            }
        else:
            diagnosis["recent_chats"] = {
                "error": updates_result.get('description')
            }
    except Exception as e:
        diagnosis["recent_chats"] = {
            "error": str(e)
        }
    
    # 3. محاولة إرسال رسالة اختبار
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        test_msg = f"Test from diagnose endpoint at {datetime.now().strftime('%H:%M:%S')}"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": test_msg
        }
        
        response = requests.post(url, json=data, timeout=10)
        msg_result = response.json()
        
        diagnosis["message_test"] = {
            "success": msg_result.get('ok', False),
            "response": msg_result,
            "error_code": msg_result.get('error_code'),
            "error_description": msg_result.get('description')
        }
    except Exception as e:
        diagnosis["message_test"] = {
            "success": False,
            "error": str(e)
        }
    
    # تقرير نهائي
    all_good = (
        diagnosis["bot_token_check"].get("valid") and
        diagnosis["message_test"].get("success")
    )
    
    diagnosis["summary"] = {
        "status": "healthy" if all_good else "issues_detected",
        "bot_token_valid": diagnosis["bot_token_check"].get("valid", False),
        "message_sent": diagnosis["message_test"].get("success", False),
        "configured_chat_id": TELEGRAM_CHAT_ID,
        "bot_token_preview": f"{TELEGRAM_BOT_TOKEN[:15]}..."
    }
    
    # توصيات
    recommendations = []
    if not diagnosis["bot_token_check"].get("valid"):
        recommendations.append("Bot Token is invalid. Get a new token from @BotFather")
    
    if not diagnosis["message_test"].get("success"):
        error_code = diagnosis["message_test"].get("error_code")
        if error_code == 403:
            bot_username = diagnosis["bot_token_check"].get("bot_info", {}).get("username", "your_bot")
            recommendations.append(f"Bot is blocked or user hasn't started chat. Open Telegram and send /start to @{bot_username}")
        elif error_code == 400:
            recommendations.append("Chat ID might be incorrect. Check 'recent_chats' section for valid Chat IDs")
        else:
            recommendations.append(f"Error {error_code}: {diagnosis['message_test'].get('error_description')}")
    
    if not diagnosis["recent_chats"].get("configured_chat_found", False):
        recommendations.append(f"Your configured Chat ID ({TELEGRAM_CHAT_ID}) was not found in recent messages. Make sure to send a message to the bot first.")
    
    diagnosis["recommendations"] = recommendations
    
    return jsonify(diagnosis), 200 if all_good else 500


@app.route('/url', methods=['GET'])
@app.route('/link', methods=['GET'])
@app.route('/webhook-url', methods=['GET'])
def get_webhook_url():
    """
    الحصول على رابط Webhook وإرسال رسالة ترحيب
    Get webhook URL and send welcome message
    """
    # الحصول على الرابط من الطلب الحالي (من Railway)
    try:
        scheme = request.scheme if hasattr(request, 'scheme') and request.scheme else 'https'
        host = request.host if hasattr(request, 'host') else None
        
        if host and host != 'localhost' and 'localhost' not in host and '127.0.0.1' not in host:
            app_url = f"{scheme}://{host}"
            # حفظ الرابط المكتشف
            global _app_url_detected
            _app_url_detected = app_url
            print(f"✅ Detected Railway URL from request: {app_url}")
        else:
            # محاولة الحصول من متغيرات البيئة
            railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RAILWAY_STATIC_URL')
            if railway_url:
                if not railway_url.startswith('http'):
                    railway_url = f"https://{railway_url}"
                app_url = railway_url
                _app_url_detected = railway_url
                print(f"✅ Using Railway URL from environment: {app_url}")
            else:
                app_url = get_app_url()
                print(f"⚠️ Using fallback URL: {app_url}")
    except Exception as e:
        print(f"⚠️ Error getting URL: {e}")
        app_url = get_app_url()
    
    # رابط Webhook المخصص
    personal_webhook_url = f"{app_url}/personal/{TELEGRAM_CHAT_ID}/webhook"
    
    print(f"📡 Generated webhook URL: {personal_webhook_url}")
    print(f"📤 Sending welcome message to Telegram (chat_id: {TELEGRAM_CHAT_ID})...")
    
    # إرسال رسالة الترحيب الكاملة مع الرابط
    welcome_message = f"""
🎉 *مرحباً! البوت يعمل الآن* 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 *حالة البوت:* ✅ نشط
📊 *الخدمة:* TradingView → Telegram
⏰ *وقت البدء:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

✅ *البوت جاهز لاستقبال التنبيهات من TradingView!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 *رابط Webhook الخاص بك:*

📡 *انسخ هذا الرابط وأضفه في TradingView:*

`{personal_webhook_url}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 *تعليمات:*
1. افتح TradingView
2. اذهب إلى Alerts → Create Alert
3. فعّل Webhook URL
4. انسخ الرابط أعلاه والصقه
5. احفظ الإعدادات! 🚀

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *ملاحظة:* هذا هو رابطك الفعلي على Railway - استخدمه مباشرة في TradingView!
    """
    
    # إرسال الرسالة إلى Telegram
    result = send_telegram_message(welcome_message)
    
    if result and result.get('ok'):
        print("✅ Welcome message with webhook URL sent successfully!")
        return jsonify({
            "status": "success",
            "message": "Welcome message sent to Telegram",
            "webhook_url": personal_webhook_url,
            "chat_id": TELEGRAM_CHAT_ID,
            "railway_url": app_url
        }), 200
    else:
        print(f"❌ Failed to send message. Error: {result}")
        return jsonify({
            "status": "error",
            "message": "Failed to send message to Telegram",
            "webhook_url": personal_webhook_url,
            "chat_id": TELEGRAM_CHAT_ID,
            "error": result
        }), 500


def send_welcome_message():
    """
    إرسال رسالة ترحيب عند بدء البوت
    Send welcome message when bot starts
    """
    # محاولة استخدام الرابط المكتشف
    global _app_url_detected
    
    # محاولة الحصول من متغيرات البيئة أولاً
    railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RAILWAY_STATIC_URL')
    if railway_url:
        if not railway_url.startswith('http'):
            railway_url = f"https://{railway_url}"
        _app_url_detected = railway_url
        app_url = railway_url
        print(f"✅ Using Railway URL from environment: {app_url}")
    else:
        app_url = _app_url_detected if _app_url_detected else get_app_url()
    
    # إذا كان الرابط لا يزال localhost، لا ترسل رسالة
    if not app_url or app_url.startswith('http://localhost') or '127.0.0.1' in app_url:
        print(f"⚠️ Cannot send welcome message: URL is localhost ({app_url})")
        print("💡 Please visit /url endpoint from your Railway domain to get your webhook URL")
        return False
    
    print(f"📨 Preparing welcome message with URL: {app_url}")
    
    webhook_url = f"{app_url}/webhook"
    personal_webhook_url = f"{app_url}/personal/{TELEGRAM_CHAT_ID}/webhook"
    test_url = f"{app_url}/test"
    welcome_url = f"{app_url}/welcome"
    
    print(f"📨 Sending welcome message with URL: {app_url}")
    
    welcome_message = """
🎉 *مرحباً! البوت يعمل الآن* 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 *حالة البوت:* ✅ نشط
📊 *الخدمة:* TradingView → Telegram
⏰ *وقت البدء:* {time}

✅ *البوت جاهز لاستقبال التنبيهات من TradingView!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 *روابط البوت:*

📡 *Webhook المخصص (للإشارات) - موصى به:*
`{personal_webhook_url}`

📡 *Webhook العام:*
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
4. ضع هذا الرابط (المخصص):
   `{personal_webhook_url}`
   أو الرابط العام:
   `{webhook_url}`
5. احفظ الإعدادات! 🚀

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *ملاحظة:* هذا هو رابطك الفعلي - استخدمه مباشرة في TradingView!
    """.format(
        time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        webhook_url=webhook_url,
        personal_webhook_url=personal_webhook_url,
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
    # الحصول على الرابط من الطلب الحالي
    try:
        scheme = request.scheme if hasattr(request, 'scheme') and request.scheme else 'https'
        host = request.host if hasattr(request, 'host') else None
        
        if host and host != 'localhost' and 'localhost' not in host and '127.0.0.1' not in host:
            global _app_url_detected
            _app_url_detected = f"{scheme}://{host}"
            print(f"✅ Detected URL in /welcome: {_app_url_detected}")
    except Exception as e:
        print(f"⚠️ Error detecting URL: {e}")
    
    result = send_welcome_message()
    return jsonify({
        "status": "success" if result else "warning",
        "message": "Welcome message sent!" if result else "Welcome message not sent (URL might be localhost)",
        "detected_url": _app_url_detected
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# 🚀 بدء البوت - Bot Startup
# ═══════════════════════════════════════════════════════════════════════════

# دالة لإرسال رسالة ترحيب عند بدء البوت
# Function to send welcome message when bot starts
def on_startup():
    """تشغيل عند بدء البوت"""
    print("=" * 60)
    print("🤖 TradingView to Telegram Bot")
    print("=" * 60)
    print(f"\n📱 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"\n🌐 Server starting...")
    
    # محاولة الحصول على الرابط من Railway مباشرة
    railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RAILWAY_STATIC_URL')
    if railway_url:
        if not railway_url.startswith('http'):
            railway_url = f"https://{railway_url}"
        global _app_url_detected
        _app_url_detected = railway_url
        print(f"✅ Railway URL detected: {railway_url}")
        
        # إرسال رسالة الترحيب مباشرة
        import threading
        import time
        
        def send_startup_message():
            time.sleep(2)  # انتظار قليل لضمان أن السيرفر جاهز
            send_welcome_message()
        
        threading.Thread(target=send_startup_message, daemon=True).start()
        print(f"📨 Welcome message will be sent shortly...")
    else:
        print(f"📡 Waiting for first request to detect URL...")
        print(f"✅ To test: /test endpoint or /url")
    
    print("=" * 60)


# متغير لتتبع ما إذا تم إرسال رسالة الترحيب
_welcome_sent = False
_app_url_detected = None

def detect_app_url_from_request():
    """الحصول على الرابط الفعلي من الطلب"""
    try:
        from flask import has_request_context
        if has_request_context() and request:
            scheme = request.scheme if request.scheme else 'https'
            host = request.host
            if host and host != 'localhost' and 'localhost' not in host:
                return f"{scheme}://{host}"
    except:
        pass
    return None

@app.before_request
def check_welcome():
    """إرسال رسالة ترحيب عند أول طلب"""
    global _welcome_sent, _app_url_detected
    
    # تخطي إذا كان الطلب من نفس البوت (لتجنب loop)
    if request.path in ['/', '/welcome', '/test', '/url', '/link', '/webhook-url', '/send-welcome']:
        return
    
    if not _welcome_sent:
        # محاولة الحصول على الرابط من الطلب الفعلي
        detected_url = detect_app_url_from_request()
        
        if detected_url and 'localhost' not in detected_url and '127.0.0.1' not in detected_url:
            _app_url_detected = detected_url
            print(f"✅ Detected app URL from request: {detected_url}")
            
            # إرسال رسالة الترحيب مباشرة مع الرابط المكتشف
            _welcome_sent = True
            import threading
            import time
            
            def send_with_detected_url():
                time.sleep(1)  # انتظار قليل
                print(f"📨 Attempting to send welcome message with URL: {_app_url_detected}")
                result = send_welcome_message()
                if not result:
                    print("❌ Failed to send welcome message - URL might be invalid")
            
            threading.Thread(target=send_with_detected_url, daemon=True).start()
        else:
            # محاولة الحصول من متغيرات البيئة
            railway_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or os.environ.get('RAILWAY_STATIC_URL')
            if railway_url:
                if not railway_url.startswith('http'):
                    railway_url = f"https://{railway_url}"
                _app_url_detected = railway_url
                print(f"✅ Found Railway URL from environment: {railway_url}")
                _welcome_sent = True
                
                def send_with_railway_url():
                    import time
                    time.sleep(1)
                    print(f"📨 Attempting to send welcome message with Railway URL: {railway_url}")
                    send_welcome_message()
                
                import threading
                threading.Thread(target=send_with_railway_url, daemon=True).start()
            else:
                print(f"⚠️ Could not detect URL from request: {detected_url}")
                _welcome_sent = True


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # عند التشغيل المحلي فقط، أرسل رسالة (localhost سيكون صحيح)
    on_startup()
    
    print(f"\n🌐 Server starting on port: {port}")
    print("=" * 60)
    
    # Railway uses gunicorn, but keep this for local testing
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # عند التشغيل على Railway/Gunicorn
    # When running on Railway/Gunicorn
    # فقط اطبع معلومات البدء، الرسالة ستُرسل عند أول طلب HTTP
    on_startup()

