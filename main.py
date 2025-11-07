"""
TradingView Webhook to Telegram Bot - نسخة مبسطة
"""
from flask import Flask, request, jsonify
from telegram_bot import (
    send_message,
    send_message_to_all_groups,
    format_buy_signal,
    format_sell_signal,
    format_buy_reverse_signal,
    format_sell_reverse_signal,
    format_tp1_hit,
    format_tp2_hit,
    format_tp3_hit,
    format_stop_loss_hit
)
from config import WEBHOOK_PORT, DEBUG, get_config_status
import logging
import json
import re
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Simple cache to prevent duplicate messages (last 5 minutes)
recent_messages = {}
last_signal_time = {}  # لتتبع آخر إشارة لكل رمز

def get_message_key(data: dict) -> str:
    """Generate a unique key for a message to detect duplicates"""
    signal = data.get('signal', '')
    symbol = data.get('symbol', '')
    entry_price = data.get('entry_price', 0)
    
    # استخدام السعر أيضاً لتجنب التكرار في نفس الثانية
    # تقريب السعر لأقرب 2 أرقام عشرية
    try:
        price_rounded = round(float(entry_price), 2) if entry_price else 0
    except:
        price_rounded = 0
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # بالثواني بدلاً من الدقائق
    return f"{signal}_{symbol}_{price_rounded}_{timestamp}"

def is_recent_duplicate(message_key: str, data: dict) -> bool:
    """Check if message was sent recently (within last 30 seconds for same signal)"""
    current_time = datetime.now()
    signal = data.get('signal', '')
    symbol = data.get('symbol', '')
    
    # تنظيف الرسائل القديمة (أكثر من 10 دقائق) لتوفير الذاكرة
    keys_to_remove = []
    for key, sent_time in recent_messages.items():
        time_diff = (current_time - sent_time).total_seconds()
        if time_diff > 600:  # 10 minutes
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del recent_messages[key]
    
    # التحقق من التكرار بناءً على نوع الإشارة
    signal_key = f"{signal}_{symbol}"
    
    # للإشارات الرئيسية (BUY, SELL, etc.)، منع التكرار لمدة 60 ثانية (زيادة لتجنب spam)
    if signal in ['BUY', 'SELL', 'BUY_REVERSE', 'SELL_REVERSE', 'LONG', 'SHORT', 'LONG_REVERSE', 'SHORT_REVERSE']:
        if signal_key in last_signal_time:
            last_time = last_signal_time[signal_key]
            time_diff = (current_time - last_time).total_seconds()
            if time_diff < 60:  # 60 seconds (زيادة من 30 لتجنب spam)
                logger.warning(f"⚠️ تم تجاهل إشارة متكررة: {signal} لـ {symbol} (آخر إشارة قبل {time_diff:.1f} ثانية)")
                return True
        last_signal_time[signal_key] = current_time
    
    # للإشارات TP/SL، منع التكرار لمدة 30 ثانية (زيادة من 15)
    elif signal in ['TP1_HIT', 'TP2_HIT', 'TP3_HIT', 'STOP_LOSS', 'TP1', 'TP2', 'TP3', 'SL']:
        if signal_key in last_signal_time:
            last_time = last_signal_time[signal_key]
            time_diff = (current_time - last_time).total_seconds()
            if time_diff < 30:  # 30 seconds (زيادة من 15)
                logger.warning(f"⚠️ تم تجاهل إشارة متكررة: {signal} لـ {symbol} (آخر إشارة قبل {time_diff:.1f} ثانية)")
                return True
        last_signal_time[signal_key] = current_time
    
    # التحقق من المفتاح الأساسي
    if message_key in recent_messages:
        last_sent = recent_messages[message_key]
        time_diff = (current_time - last_sent).total_seconds()
        if time_diff < 60:  # 1 minute
            return True
    
    recent_messages[message_key] = current_time
    return False

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    config_status = get_config_status()
    return jsonify({
        "status": "ok",
        "message": "TradingView Webhook to Telegram Bot is running",
        "config": {
            "telegram_bot_token": "✓ Set" if config_status['telegram_bot_token'] else "✗ Missing",
            "telegram_chat_id": "✓ Set" if config_status['telegram_chat_id'] else "✗ Missing"
        }
    }), 200

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Webhook endpoint للبوت - للرد على الأوامر مثل /start"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "ok"}), 200
        
        message = data.get('message', {})
        chat = message.get('chat', {})
        text = message.get('text', '')
        chat_id = str(chat.get('id', ''))
        
        # الرد على الأوامر
        if text.startswith('/start'):
            from telegram_bot import send_message
            welcome_msg = (
                "🤖 <b>مرحباً! أنا بوت إشارات التداول</b>\n\n"
                "✅ البوت يعمل بشكل صحيح\n"
                "📊 سأرسل إشارات التداول من TradingView تلقائياً\n\n"
                "💡 <b>الأوامر المتاحة:</b>\n"
                "/start - عرض هذه الرسالة\n"
                "/help - عرض المساعدة\n"
                "/status - حالة البوت"
            )
            send_message(welcome_msg, chat_id)
            return jsonify({"status": "ok"}), 200
        
        elif text.startswith('/help'):
            from telegram_bot import send_message
            help_msg = (
                "📖 <b>مساعدة - بوت إشارات التداول</b>\n\n"
                "🔹 <b>كيف يعمل البوت:</b>\n"
                "• يستقبل إشارات من TradingView\n"
                "• يرسل إشارات التداول تلقائياً\n"
                "• يعرض TP/SL والأسعار\n\n"
                "🔹 <b>أنواع الإشارات:</b>\n"
                "• 🟢 صفقة لونج (BUY)\n"
                "• 🔴 صفقة شورت (SELL)\n"
                "• 🟠 صفقات عكسية (REVERSE)\n"
                "• 🎯 أهداف الربح (TP1, TP2, TP3)\n"
                "• 🛑 وقف الخسارة (SL)\n\n"
                "💡 البوت يعمل تلقائياً، لا حاجة لإرسال أوامر!"
            )
            send_message(help_msg, chat_id)
            return jsonify({"status": "ok"}), 200
        
        elif text.startswith('/status'):
            from telegram_bot import send_message
            status_msg = (
                "✅ <b>حالة البوت: نشط</b>\n\n"
                "🤖 البوت يعمل بشكل صحيح\n"
                "📊 جاهز لاستقبال الإشارات من TradingView\n"
                "⚡ Rate limiting: مفعّل\n"
                "🔒 حماية من spam: مفعّلة"
            )
            send_message(status_msg, chat_id)
            return jsonify({"status": "ok"}), 200
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Error in telegram webhook: {e}")
        return jsonify({"status": "ok"}), 200  # دائماً نرد OK حتى لا يحاول Telegram إعادة الإرسال

@app.route('/webhook', methods=['POST', 'GET'])
@app.route('/personal/<chat_id>/webhook', methods=['POST', 'GET'])
def webhook(chat_id=None):
    """
    Main webhook endpoint - نسخة مبسطة
    يتوقع JSON بسيط مع signal واضح
    """
    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "message": "Webhook endpoint is active",
            "chat_id_from_url": chat_id
        }), 200
    
    try:
        # Get JSON data
        data = None
        try:
            if request.is_json:
                data = request.get_json(force=False)
            else:
                raw_data = request.get_data(as_text=True)
                logger.info(f"📥 Raw data received: {raw_data[:200]}...")  # Log first 200 chars
                
                if raw_data:
                    # Try to extract JSON from raw data (in case there's extra text)
                    # Look for JSON object starting with {
                    start_idx = raw_data.find('{')
                    if start_idx != -1:
                        # Find matching closing brace
                        brace_count = 0
                        end_idx = start_idx
                        for i in range(start_idx, len(raw_data)):
                            if raw_data[i] == '{':
                                brace_count += 1
                            elif raw_data[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        json_str = raw_data[start_idx:end_idx]
                        
                        # Replace TradingView placeholders that weren't substituted
                        # {{plot("...")}} -> null
                        json_str = re.sub(r'\{\{plot\([^)]+\)\}\}', 'null', json_str)
                        json_str = re.sub(r'\{\{[^}]+\}\}', 'null', json_str)  # Any other {{...}}
                        
                        logger.info(f"📥 Cleaned JSON: {json_str[:200]}...")
                        data = json.loads(json_str)
                    else:
                        # Try parsing the whole thing
                        data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing JSON: {e}")
            logger.error(f"❌ Raw data: {request.get_data(as_text=True)[:500]}")
            return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing data: {e}")
            logger.error(f"❌ Raw data: {request.get_data(as_text=True)[:500]}")
            return jsonify({"error": f"Error processing request: {str(e)}"}), 400
        
        if not data or not isinstance(data, dict):
            logger.error(f"❌ Invalid data format: {type(data)} - {data}")
            return jsonify({"error": "No valid data received"}), 400
        
        # Get signal type (required)
        signal = data.get('signal', '').upper()
        if not signal:
            return jsonify({"error": "Signal type is required"}), 400
        
        # Check for duplicates
        message_key = get_message_key(data)
        if is_recent_duplicate(message_key, data):
            logger.warning(f"⚠️ Duplicate message ignored: {message_key}")
            return jsonify({"status": "ignored", "message": "Duplicate"}), 200
        
        logger.info(f"✅ New signal: {signal} for {data.get('symbol', 'N/A')}")
        
        # Route to appropriate formatter
        message = None
        
        if signal == 'BUY' or signal == 'LONG':
            message = format_buy_signal(data)
        elif signal == 'SELL' or signal == 'SHORT':
            message = format_sell_signal(data)
        elif signal == 'BUY_REVERSE' or signal == 'LONG_REVERSE':
            message = format_buy_reverse_signal(data)
        elif signal == 'SELL_REVERSE' or signal == 'SHORT_REVERSE':
            message = format_sell_reverse_signal(data)
        elif signal == 'TP1_HIT' or signal == 'TP1':
            message = format_tp1_hit(data)
        elif signal == 'TP2_HIT' or signal == 'TP2':
            message = format_tp2_hit(data)
        elif signal == 'TP3_HIT' or signal == 'TP3':
            message = format_tp3_hit(data)
        elif signal == 'STOP_LOSS' or signal == 'SL':
            message = format_stop_loss_hit(data)
        else:
            return jsonify({"error": f"Unknown signal type: {signal}"}), 400
        
        # Send message
        if message:
            # إذا كان chat_id محدد في URL، أرسل له فقط
            # وإلا أرسل لجميع المجموعات من config.py
            if chat_id:
                # إرسال لمجموعة واحدة (من URL)
                logger.info(f"📤 إرسال لمجموعة واحدة من URL: {chat_id}")
                success = send_message(message, chat_id)
                if success:
                    return jsonify({"status": "success", "signal": signal, "chat_id": chat_id}), 200
                else:
                    return jsonify({"status": "error", "message": "Failed to send to Telegram"}), 500
            else:
                # إرسال لجميع المجموعات من config.py
                from config import TELEGRAM_CHAT_IDS
                if not TELEGRAM_CHAT_IDS:
                    logger.error("❌ No chat IDs available - يجب تحديد Chat IDs في config.py")
                    return jsonify({
                        "error": "No chat IDs available",
                        "message": "يجب تحديد Chat IDs في config.py أو استخدام /personal/<chat_id>/webhook"
                    }), 500
                
                logger.info(f"📤 إرسال لجميع المجموعات ({len(TELEGRAM_CHAT_IDS)} مجموعة)")
                result = send_message_to_all_groups(message, TELEGRAM_CHAT_IDS)
                if result['success'] > 0:
                    return jsonify({
                        "status": "success",
                        "signal": signal,
                        "sent_to": result['success'],
                        "total": result['total'],
                        "results": result['results']
                    }), 200
                else:
                    return jsonify({"status": "error", "message": "Failed to send to all groups"}), 500
        else:
            return jsonify({"status": "error", "message": "Failed to format message"}), 500
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Startup message
from config import get_config_status
from telegram_bot import send_startup_message
import time
import os

config_status = get_config_status()
if config_status["all_set"]:
    logger.info("Configuration validated successfully")
    time.sleep(2)
    send_startup_message()
else:
    logger.warning("⚠️ Configuration incomplete")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=WEBHOOK_PORT, debug=DEBUG)
