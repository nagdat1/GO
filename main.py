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
    return jsonify({
        "service": "TradingView to Telegram Bot",
        "status": "running",
        "endpoints": {
            "/webhook": "POST - Receive TradingView alerts",
            "/test": "GET - Send test message to Telegram",
            "/": "GET - This page"
        },
        "telegram_chat_id": TELEGRAM_CHAT_ID,
        "instructions": "Add /webhook URL to TradingView Alert webhook field"
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🤖 TradingView to Telegram Bot")
    print("=" * 60)
    print(f"\n📱 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"\n🌐 Server starting on port: {port}")
    print(f"📡 Webhook URL: https://your-app.railway.app/webhook")
    print(f"\n✅ To test: https://your-app.railway.app/test")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)

