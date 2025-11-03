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
    
    # ═══════════════════════════════════════════════════════════════
    # تحليل رسائل المؤشر "غروب الاشارات" وإعادة صياغتها بشكل احترافي
    # ═══════════════════════════════════════════════════════════════
    if message_text:
        import re
        
        # التحقق من أن الرسالة من المؤشر
        is_indicator_message = ('🟢🟢🟢' in message_text or '🔴🔴🔴' in message_text or 
                               '🎯✅🎯' in message_text or '🛑😔🛑' in message_text or 
                               '🔚📊🔚' in message_text or '*BUY SIGNAL*' in message_text or
                               '*SELL SIGNAL*' in message_text or '*TP1 - FIRST TARGET HIT*' in message_text or
                               '*TP2 - SECOND TARGET HIT*' in message_text or '*TP3 - THIRD TARGET HIT*' in message_text or
                               '*STOP LOSS HIT*' in message_text or '*POSITION CLOSED*' in message_text)
        
        if is_indicator_message:
            # استخراج المعلومات من رسالة المؤشر
            formatted_msg = ""
            
            # 1. إشارة شراء (BUY SIGNAL)
            if '*BUY SIGNAL*' in message_text or '🟢🟢🟢' in message_text:
                # استخراج Symbol
                symbol_match = re.search(r'Symbol:\s*([^\n]+)', message_text, re.IGNORECASE)
                symbol = symbol_match.group(1).strip() if symbol_match else None
                
                # استخراج Entry Price
                entry_match = re.search(r'Entry\s+Price:\s*([\d.,]+)', message_text, re.IGNORECASE)
                entry_price = entry_match.group(1).strip() if entry_match else None
                
                # استخراج Time وتحويله
                time_match = re.search(r'Time:\s*([^\n]+)', message_text, re.IGNORECASE)
                time_raw = time_match.group(1).strip() if time_match else None
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                if time_raw:
                    try:
                        # إذا كان timestamp بالميلي ثانية
                        if time_raw.isdigit() and len(time_raw) >= 10:
                            timestamp_ms = int(time_raw)
                            # تحويل من ميلي ثانية إلى ثانية
                            if timestamp_ms > 1000000000000:  # إذا كان بالميلي ثانية
                                timestamp_s = timestamp_ms / 1000
                            else:
                                timestamp_s = timestamp_ms
                            time_str = datetime.fromtimestamp(timestamp_s).strftime('%Y-%m-%d %H:%M')
                        # إذا كان تاريخ نصي
                        else:
                            # محاولة تحليل التاريخ
                            time_str = time_raw
                            # التحقق من أنه تاريخ صحيح وليس نص عادي
                            if 'yyyy' not in time_raw.lower() and 'MM' not in time_raw:
                                # محاولة تحليل تنسيقات تاريخ شائعة
                                try:
                                    # تنسيق: "2025-11-03 04:15:11" أو "2025-11-03 04:15"
                                    if len(time_raw) >= 16 and '-' in time_raw:
                                        time_str = time_raw[:16]  # أخذ أول 16 حرف (YYYY-MM-DD HH:MM)
                                except:
                                    pass
                    except:
                        pass
                
                # استخراج Timeframe
                timeframe_match = re.search(r'Timeframe:\s*([^\n]+)', message_text, re.IGNORECASE)
                timeframe = timeframe_match.group(1).strip() if timeframe_match else None
                
                # استخراج TP1, TP2, TP3
                tp1_match = re.search(r'TP1:\s*([^\n]+)', message_text, re.IGNORECASE)
                tp2_match = re.search(r'TP2:\s*([^\n]+)', message_text, re.IGNORECASE)
                tp3_match = re.search(r'TP3:\s*([^\n]+)', message_text, re.IGNORECASE)
                
                tp1 = tp1_match.group(1).strip() if tp1_match else None
                tp2 = tp2_match.group(1).strip() if tp2_match else None
                tp3 = tp3_match.group(1).strip() if tp3_match else None
                
                # استخراج Stop Loss
                sl_match = re.search(r'Stop\s+Loss:\s*([^\n]+)', message_text, re.IGNORECASE)
                stop_loss = sl_match.group(1).strip() if sl_match else None
                
                # بناء الرسالة بشكل منظم
                formatted_msg = "🟢 *إشارة شراء*\n"
                formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                if symbol:
                    formatted_msg += f"💰 *العملة:* `{symbol}`\n"
                if entry_price:
                    formatted_msg += f"💵 *سعر الدخول:* `{entry_price}`\n"
                
                # إظهار أهداف الربح فقط إذا كانت موجودة
                if tp1 or tp2 or tp3:
                    formatted_msg += "\n📍 *أهداف الربح:*\n"
                    if tp1:
                        formatted_msg += f"   🎯 TP1: `{tp1}`\n"
                    if tp2:
                        formatted_msg += f"   🎯 TP2: `{tp2}`\n"
                    if tp3:
                        formatted_msg += f"   🎯 TP3: `{tp3}`\n"
                
                if stop_loss:
                    formatted_msg += f"\n🛑 *وقف الخسارة:* `{stop_loss}`\n"
                
                if timeframe:
                    formatted_msg += f"\n📈 *الإطار الزمني:* `{timeframe}`\n"
                formatted_msg += f"\n⏰ *الوقت:* `{time_str}`\n"
                formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                
                return formatted_msg
            
            # 2. إشارة بيع (SELL SIGNAL)
            elif '*SELL SIGNAL*' in message_text or '🔴🔴🔴' in message_text:
                # استخراج المعلومات (نفس منطق الشراء)
                symbol_match = re.search(r'Symbol:\s*([^\n]+)', message_text, re.IGNORECASE)
                symbol = symbol_match.group(1).strip() if symbol_match else None
                
                entry_match = re.search(r'Entry\s+Price:\s*([\d.,]+)', message_text, re.IGNORECASE)
                entry_price = entry_match.group(1).strip() if entry_match else None
                
                time_match = re.search(r'Time:\s*([^\n]+)', message_text, re.IGNORECASE)
                time_raw = time_match.group(1).strip() if time_match else None
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                if time_raw:
                    try:
                        # إذا كان timestamp بالميلي ثانية
                        if time_raw.isdigit() and len(time_raw) >= 10:
                            timestamp_ms = int(time_raw)
                            # تحويل من ميلي ثانية إلى ثانية
                            if timestamp_ms > 1000000000000:  # إذا كان بالميلي ثانية
                                timestamp_s = timestamp_ms / 1000
                                else:
                                timestamp_s = timestamp_ms
                            time_str = datetime.fromtimestamp(timestamp_s).strftime('%Y-%m-%d %H:%M')
                        # إذا كان تاريخ نصي
                        else:
                            # محاولة تحليل التاريخ
                            time_str = time_raw
                            # التحقق من أنه تاريخ صحيح وليس نص عادي
                            if 'yyyy' not in time_raw.lower() and 'MM' not in time_raw:
                                # محاولة تحليل تنسيقات تاريخ شائعة
                                try:
                                    # تنسيق: "2025-11-03 04:15:11" أو "2025-11-03 04:15"
                                    if len(time_raw) >= 16 and '-' in time_raw:
                                        time_str = time_raw[:16]  # أخذ أول 16 حرف (YYYY-MM-DD HH:MM)
                                except:
                                    pass
                    except:
                        pass
                
                timeframe_match = re.search(r'Timeframe:\s*([^\n]+)', message_text, re.IGNORECASE)
                timeframe = timeframe_match.group(1).strip() if timeframe_match else None
                
                tp1_match = re.search(r'TP1:\s*([^\n]+)', message_text, re.IGNORECASE)
                tp2_match = re.search(r'TP2:\s*([^\n]+)', message_text, re.IGNORECASE)
                tp3_match = re.search(r'TP3:\s*([^\n]+)', message_text, re.IGNORECASE)
                
                tp1 = tp1_match.group(1).strip() if tp1_match else None
                tp2 = tp2_match.group(1).strip() if tp2_match else None
                tp3 = tp3_match.group(1).strip() if tp3_match else None
                
                sl_match = re.search(r'Stop\s+Loss:\s*([^\n]+)', message_text, re.IGNORECASE)
                stop_loss = sl_match.group(1).strip() if sl_match else None
                
                # بناء الرسالة
                formatted_msg = "🔴 *إشارة بيع*\n"
                formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                if symbol:
                    formatted_msg += f"💰 *العملة:* `{symbol}`\n"
                if entry_price:
                    formatted_msg += f"💵 *سعر الدخول:* `{entry_price}`\n"
                
                # إظهار أهداف الربح فقط إذا كانت موجودة
                if tp1 or tp2 or tp3:
                    formatted_msg += "\n📍 *أهداف الربح:*\n"
                    if tp1:
                        formatted_msg += f"   🎯 TP1: `{tp1}`\n"
                    if tp2:
                        formatted_msg += f"   🎯 TP2: `{tp2}`\n"
                    if tp3:
                        formatted_msg += f"   🎯 TP3: `{tp3}`\n"
                
                if stop_loss:
                    formatted_msg += f"\n🛑 *وقف الخسارة:* `{stop_loss}`\n"
                
                if timeframe:
                    formatted_msg += f"\n📈 *الإطار الزمني:* `{timeframe}`\n"
                formatted_msg += f"\n⏰ *الوقت:* `{time_str}`\n"
                formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                
                return formatted_msg
            
            # 3. ضرب الهدف (TP1, TP2, TP3)
            elif '*TP1 - FIRST TARGET HIT*' in message_text or '*TP2 - SECOND TARGET HIT*' in message_text or '*TP3 - THIRD TARGET HIT*' in message_text or ('🎯✅🎯' in message_text and 'TARGET HIT' in message_text.upper()):
                tp_num = "1" if "TP1" in message_text or "FIRST" in message_text.upper() else \
                         "2" if "TP2" in message_text or "SECOND" in message_text.upper() else \
                         "3" if "TP3" in message_text or "THIRD" in message_text.upper() else "?"
                
                symbol_match = re.search(r'Symbol:\s*([^\n]+)', message_text, re.IGNORECASE)
                symbol = symbol_match.group(1).strip() if symbol_match else None
                
                entry_match = re.search(r'Entry\s+Price:\s*([\d.,]+)', message_text, re.IGNORECASE)
                entry_price = entry_match.group(1).strip() if entry_match else None
                
                exit_match = re.search(r'Exit\s+Price:\s*([\d.,]+)', message_text, re.IGNORECASE)
                exit_price = exit_match.group(1).strip() if exit_match else None
                
                profit_match = re.search(r'Profit:\s*([^\n]+)', message_text, re.IGNORECASE)
                profit = profit_match.group(1).strip() if profit_match else None
                
                time_match = re.search(r'Time:\s*([^\n]+)', message_text, re.IGNORECASE)
                time_raw = time_match.group(1).strip() if time_match else None
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                if time_raw:
                    try:
                        # إذا كان timestamp بالميلي ثانية
                        if time_raw.isdigit() and len(time_raw) >= 10:
                            timestamp_ms = int(time_raw)
                            if timestamp_ms > 1000000000000:
                                timestamp_s = timestamp_ms / 1000
                            else:
                                timestamp_s = timestamp_ms
                            time_str = datetime.fromtimestamp(timestamp_s).strftime('%Y-%m-%d %H:%M')
                        else:
                            time_str = time_raw
                            if 'yyyy' not in time_raw.lower() and 'MM' not in time_raw:
                                try:
                                    # تنسيق: "2025-11-03 04:15:11" أو "2025-11-03 04:15"
                                    if len(time_raw) >= 16 and '-' in time_raw:
                                        time_str = time_raw[:16]  # أخذ أول 16 حرف (YYYY-MM-DD HH:MM)
                                except:
                                    pass
                    except:
                        pass
                
                # بناء الرسالة
                formatted_msg = f"🎯✅ *تم ضرب الهدف {tp_num}*\n"
                formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                if symbol:
                    formatted_msg += f"💰 *العملة:* `{symbol}`\n"
                if entry_price:
                    formatted_msg += f"💵 *سعر الدخول:* `{entry_price}`\n"
                if exit_price:
                    formatted_msg += f"💵 *سعر الهدف:* `{exit_price}`\n"
                if profit:
                    formatted_msg += f"💚 *الربح:* `{profit}`\n"
                
                formatted_msg += f"\n⏰ *الوقت:* `{time_str}`\n"
    formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return formatted_msg

            # 4. ضرب وقف الخسارة (STOP LOSS)
            elif '*STOP LOSS HIT*' in message_text or '🛑😔🛑' in message_text:
                symbol_match = re.search(r'Symbol:\s*([^\n]+)', message_text, re.IGNORECASE)
                symbol = symbol_match.group(1).strip() if symbol_match else None
                
                price_match = re.search(r'Price:\s*([\d.,]+)', message_text, re.IGNORECASE)
                price = price_match.group(1).strip() if price_match else None
                
                time_match = re.search(r'Time:\s*([^\n]+)', message_text, re.IGNORECASE)
                time_raw = time_match.group(1).strip() if time_match else None
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                if time_raw:
                    try:
                        # إذا كان timestamp بالميلي ثانية
                        if time_raw.isdigit() and len(time_raw) >= 10:
                            timestamp_ms = int(time_raw)
                            if timestamp_ms > 1000000000000:
                                timestamp_s = timestamp_ms / 1000
                            else:
                                timestamp_s = timestamp_ms
                            time_str = datetime.fromtimestamp(timestamp_s).strftime('%Y-%m-%d %H:%M')
                        else:
                            time_str = time_raw
                            if 'yyyy' not in time_raw.lower() and 'MM' not in time_raw:
                                try:
                                    # تنسيق: "2025-11-03 04:15:11" أو "2025-11-03 04:15"
                                    if len(time_raw) >= 16 and '-' in time_raw:
                                        time_str = time_raw[:16]  # أخذ أول 16 حرف (YYYY-MM-DD HH:MM)
                                except:
                                    pass
                    except:
                        pass
                
                # بناء الرسالة
                formatted_msg = "🛑 *للأسف تم ضرب وقف الخسارة*\n"
                formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                if symbol:
                    formatted_msg += f"💰 *العملة:* `{symbol}`\n"
                if price:
                    formatted_msg += f"💔 *سعر الإغلاق:* `{price}`\n"
                
                formatted_msg += f"\n⚠️ *يُنصح بمراجعة الاستراتيجية*\n"
                formatted_msg += f"⏰ *الوقت:* `{time_str}`\n"
                formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                
                return formatted_msg
            
            # 5. إغلاق الصفقة (POSITION CLOSED)
            elif '*POSITION CLOSED*' in message_text or '🔚📊🔚' in message_text:
                symbol_match = re.search(r'Symbol:\s*([^\n]+)', message_text, re.IGNORECASE)
                symbol = symbol_match.group(1).strip() if symbol_match else None
                
                price_match = re.search(r'Price:\s*([\d.,]+)', message_text, re.IGNORECASE)
                price = price_match.group(1).strip() if price_match else None
                
                time_match = re.search(r'Time:\s*([^\n]+)', message_text, re.IGNORECASE)
                time_raw = time_match.group(1).strip() if time_match else None
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                if time_raw:
                    try:
                        # إذا كان timestamp بالميلي ثانية
                        if time_raw.isdigit() and len(time_raw) >= 10:
                            timestamp_ms = int(time_raw)
                            if timestamp_ms > 1000000000000:
                                timestamp_s = timestamp_ms / 1000
                            else:
                                timestamp_s = timestamp_ms
                            time_str = datetime.fromtimestamp(timestamp_s).strftime('%Y-%m-%d %H:%M')
                        else:
                            time_str = time_raw
                            if 'yyyy' not in time_raw.lower() and 'MM' not in time_raw:
                                try:
                                    # تنسيق: "2025-11-03 04:15:11" أو "2025-11-03 04:15"
                                    if len(time_raw) >= 16 and '-' in time_raw:
                                        time_str = time_raw[:16]  # أخذ أول 16 حرف (YYYY-MM-DD HH:MM)
                                except:
                                    pass
                    except:
                        pass
                
                # بناء الرسالة
                formatted_msg = "🔒 *إغلاق الصفقة*\n"
                formatted_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                if symbol:
                    formatted_msg += f"💰 *العملة:* `{symbol}`\n"
                if price:
                    formatted_msg += f"💵 *سعر الإغلاق:* `{price}`\n"
                
                formatted_msg += f"\n📌 *التعليمات:* أغلِق الصفقة الآن\n"
                formatted_msg += f"⏰ *الوقت:* `{time_str}`\n"
                formatted_msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                
                return formatted_msg
    
    # تحليل الرسالة واستخراج المعلومات (للرسائل الأخرى غير المؤشر)
    if message_text:
        import re
        
        # تنظيف الرسالة من التفاصيل التقنية
        cleaned_message = message_text
        cleaned_message = re.sub(r'^[^:]*\([^)]+\):\s*', '', cleaned_message)
        cleaned_message = re.sub(r'nagdat\s*\([^)]+\):\s*', '', cleaned_message, flags=re.IGNORECASE)
        
        message_upper = cleaned_message.upper()
        
        # ═══════════════════════════════════════════════════════════════
        # استخراج المعلومات الأساسية أولاً
        # ═══════════════════════════════════════════════════════════════
        
        # استخراج المركز أولاً للتحقق من الإغلاق
        position_match = re.search(r'المركز[^ه]*هو\s*(-?\d+\.?\d*)', cleaned_message) or re.search(r'position[^i]*is\s*(-?\d+\.?\d*)', cleaned_message, re.IGNORECASE)
        position = position_match.group(1) if position_match else None
        
        # استخراج نوع الأمر (buy/sell) من "تم تنفيذ الأمر"
        action_match = re.search(r'تم\s+تنفيذ\s+الأمر\s+(\w+)', cleaned_message, re.IGNORECASE) or re.search(r'order\s+(\w+)', cleaned_message, re.IGNORECASE)
        action = action_match.group(1).lower() if action_match else None
        
        # ═══════════════════════════════════════════════════════════════
        # تحديد نوع الإشارة
        # ═══════════════════════════════════════════════════════════════
        
        signal_category = None
        signal_emoji = "📊"
        signal_title = "Trading Alert"
        
        # تحقق من الإغلاق أولاً (المركز = 0)
        if position:
            try:
                position_float = float(position)
                if position_float == 0:
                    signal_category = "CLOSE"
                    signal_emoji = "🔒"
                    signal_title = "إغلاق صفقة"
            except:
                pass
        
        # إذا لم يكن إغلاق، حدد نوع الصفقة
        if not signal_category:
            # 1. فتح صفقة BUY
            if (action and action in ["buy", "long"]) or (any(word in message_upper for word in ["BUY", "LONG", "شراء"]) and not any(word in message_upper for word in ["CLOSE", "إغلاق", "TP", "SL"])):
                signal_category = "ENTRY_BUY"
                signal_emoji = "🟢"
                signal_title = "إشارة شراء"
            
            # 2. فتح صفقة SELL
            elif (action and action in ["sell", "short"]) or (any(word in message_upper for word in ["SELL", "SHORT", "بيع"]) and not any(word in message_upper for word in ["CLOSE", "إغلاق", "TP", "SL"])):
                signal_category = "ENTRY_SELL"
                signal_emoji = "🔴"
                signal_title = "إشارة بيع"
            
            # 3. إغلاق صفقة (من الكلمات)
            elif any(word in message_upper for word in ["CLOSE", "إغلاق", "EXIT"]):
                signal_category = "CLOSE"
                signal_emoji = "🔒"
                signal_title = "إغلاق صفقة"
        
        # 4. هدف 1
        if not signal_category and any(word in message_upper for word in ["TP1", "TARGET 1", "TAKE PROFIT 1", "الهدف 1", "هدف 1"]):
            signal_category = "TP1"
            signal_emoji = "🎯"
            signal_title = "تحقيق الهدف الأول"
        
        # 5. هدف 2
        if not signal_category and any(word in message_upper for word in ["TP2", "TARGET 2", "TAKE PROFIT 2", "الهدف 2", "هدف 2"]):
            signal_category = "TP2"
            signal_emoji = "🎯🎯"
            signal_title = "تحقيق الهدف الثاني"
        
        # 6. هدف 3
        if not signal_category and any(word in message_upper for word in ["TP3", "TARGET 3", "TAKE PROFIT 3", "الهدف 3", "هدف 3"]):
            signal_category = "TP3"
            signal_emoji = "🎯🎯🎯"
            signal_title = "تحقيق الهدف الثالث"
        
        # 7. وقف خسارة
        if not signal_category and any(word in message_upper for word in ["STOP LOSS", "SL", "STOPLOSS", "وقف الخسارة", "ستوب لوز"]):
            signal_category = "STOP_LOSS"
            signal_emoji = "🛑"
            signal_title = "وقف الخسارة"
        
        # 8. هدف عام (TP بدون رقم)
        if not signal_category and any(word in message_upper for word in ["TP", "TAKE PROFIT", "TARGET", "هدف"]):
            signal_category = "TP"
            signal_emoji = "🎯"
            signal_title = "تحقيق هدف"
        
        # ═══════════════════════════════════════════════════════════════
        # استخراج المعلومات
        # ═══════════════════════════════════════════════════════════════
        
        # استخراج السعر (من بعد @)
        # ملاحظة: قد يكون ما بعد @ هو عدد العقود وليس السعر إذا كان صغيراً
        price_match = re.search(r'@\s*([\d.,]+)', cleaned_message)
        price_raw = price_match.group(1).replace(',', '') if price_match else None
        
        # إذا كان "السعر" صغير جداً (< 100) ويساوي المركز، فهو على الأرجح عدد العقود وليس السعر
        price = None
        if price_raw:
            try:
                price_float = float(price_raw)
                # إذا كان السعر أقل من 100 ويساوي المركز، فهو عدد العقود
                if price_float >= 100 or (position and abs(price_float - float(position)) > 0.01):
                    price = price_raw
                # إذا كان صغيراً جداً (أقل من 1) فهو بالتأكيد ليس سعر عملة
                elif price_float < 1:
                    price = None
    else:
                    price = price_raw
            except:
                price = price_raw
        
        # استخراج العملة (من "على SYMBOL" أو من نهاية الرسالة)
        ticker_match = re.search(r'على\s+([A-Z0-9]+)', cleaned_message, re.IGNORECASE) or re.search(r'([A-Z]{2,}(?:USDT|BTC|ETH|BUSD|USD))', cleaned_message.upper())
        ticker = ticker_match.group(1).upper() if ticker_match else None
        
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
        if position is not None and signal_category not in ["TP1", "TP2", "TP3", "STOP_LOSS", "CLOSE"]:
            try:
                position_float = float(position)
                if abs(position_float) < 0.0001:  # إذا كان قريب من الصفر
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

