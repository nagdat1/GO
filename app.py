"""
TradingView Webhook to Telegram Bot - نسخة مبسطة جداً
"""
from flask import Flask, request, jsonify
import requests
import os
import time
import logging
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# إعدادات
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8361920962:AAFkWchaQStjaD09ayMI8VYm1vadr4p6zEY')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1003214062626')  # Crypto Insight
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Rate limiting
_last_msg_time = 0
_min_delay = 2.0
_recent_msgs = {}
_last_signal = {}

# نظام حفظ الصفقات
STORAGE_FILE = 'trades.json'

def load_trades():
    """تحميل الصفقات من الملف"""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_trades(trades):
    """حفظ الصفقات في الملف"""
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الصفقات: {e}")
        return False

def add_trade(data, signal_type):
    """إضافة صفقة جديدة"""
    trades = load_trades()
    symbol = data.get('symbol', 'UNKNOWN')
    entry_price = data.get('entry_price') or data.get('price', 0)
    timestamp = datetime.now().isoformat()
    
    # إنشاء معرف فريد للصفقة
    trade_id = f"{symbol}_{timestamp}"
    
    trade = {
        'id': trade_id,
        'symbol': symbol,
        'signal': signal_type,
        'entry_price': entry_price,
        'entry_time': timestamp,
        'tp1': data.get('tp1'),
        'tp2': data.get('tp2'),
        'tp3': data.get('tp3'),
        'stop_loss': data.get('stop_loss'),
        'timeframe': data.get('timeframe', 'N/A'),
        'status': 'open',  # open, tp1, tp2, tp3, closed, sl
        'exit_price': None,
        'exit_time': None
    }
    
    trades[trade_id] = trade
    save_trades(trades)
    logger.info(f"✅ تم حفظ الصفقة: {trade_id}")
    return trade_id

def update_trade_status(symbol, signal_type, exit_price):
    """تحديث حالة الصفقة"""
    trades = load_trades()
    updated = False
    
    # البحث عن آخر صفقة مفتوحة لهذا الرمز
    open_trades = [t for t in trades.values() 
                   if t['symbol'] == symbol and t['status'] == 'open']
    
    if open_trades:
        # آخر صفقة مفتوحة
        trade = open_trades[-1]
        trade_id = trade['id']
        
        # تحديث الحالة
        if signal_type in ['TP1_HIT', 'TP1']:
            trade['status'] = 'tp1'
        elif signal_type in ['TP2_HIT', 'TP2']:
            trade['status'] = 'tp2'
        elif signal_type in ['TP3_HIT', 'TP3']:
            trade['status'] = 'closed'  # TP3 = إغلاق كامل
        elif signal_type in ['STOP_LOSS', 'SL']:
            trade['status'] = 'closed'  # SL = إغلاق
        
        trade['exit_price'] = exit_price
        trade['exit_time'] = datetime.now().isoformat()
        
        trades[trade_id] = trade
        save_trades(trades)
        updated = True
        logger.info(f"✅ تم تحديث الصفقة: {trade_id} -> {trade['status']}")
    
    return updated

# دوال مساعدة
def escape_html(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def format_price(price):
    try:
        p = float(price)
        if p >= 1000:
            return f"{p:,.2f}"
        elif p >= 1:
            return f"{p:,.2f}"
        elif p >= 0.01:
            return f"{p:.4f}"
        else:
            return f"{p:.8f}".rstrip('0').rstrip('.')
    except:
        return str(price)

def format_tf(tf):
    if not tf or tf == 'N/A':
        return 'N/A'
    try:
        num = int(tf)
        if num < 60:
            return f"{num} د"
        elif num < 1440:
            return f"{num // 60} س"
        else:
            return f"{num // 1440} ي"
    except:
        return str(tf)

def calc_tp_sl(entry, is_long=True):
    """حساب TP/SL تلقائياً"""
    try:
        entry = float(entry)
        atr = entry * 0.01  # تقريبي 1%
        factor = 2.5
        if is_long:
            return {
                'tp1': entry + (1 * factor * atr),
                'tp2': entry + (2 * factor * atr),
                'tp3': entry + (3 * factor * atr),
                'sl': entry - (1 * factor * atr)
            }
        else:
            return {
                'tp1': entry - (1 * factor * atr),
                'tp2': entry - (2 * factor * atr),
                'tp3': entry - (3 * factor * atr),
                'sl': entry + (1 * factor * atr)
            }
    except:
        return {}

def send_telegram(msg, chat_id):
    """إرسال رسالة إلى Telegram"""
    global _last_msg_time, _min_delay
    
    # Rate limiting
    now = time.time()
    if now - _last_msg_time < _min_delay:
        time.sleep(_min_delay - (now - _last_msg_time))
    _last_msg_time = time.time()
    
    try:
        r = requests.post(API_URL, json={
            "chat_id": str(chat_id),
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
        
        if r.status_code == 200 and r.json().get('ok'):
            logger.info(f"✅ تم الإرسال إلى {chat_id}")
            return True
        else:
            logger.error(f"❌ فشل الإرسال: {r.text}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return False

# تنسيق الرسائل
def format_buy(data):
    symbol = data.get('symbol', 'N/A')
    entry = data.get('entry_price') or data.get('price', 0)
    tp1, tp2, tp3, sl = data.get('tp1'), data.get('tp2'), data.get('tp3'), data.get('stop_loss')
    
    # حساب تلقائي إذا لم تكن موجودة
    if not (tp1 or tp2 or tp3 or sl) and entry:
        calc = calc_tp_sl(entry, True)
        tp1, tp2, tp3, sl = calc.get('tp1'), calc.get('tp2'), calc.get('tp3'), calc.get('sl')
    
    msg = f"🟢 <b>صفقة لونج (LONG)</b> 🟢\n\n"
    msg += f"📊 الرمز: {escape_html(symbol)}\n"
    msg += f"💰 سعر الدخول: <code>{format_price(entry)}</code>\n"
    msg += f"⏰ الوقت: {escape_html(data.get('time', 'N/A'))}\n"
    msg += f"📈 الإطار الزمني: {escape_html(format_tf(data.get('timeframe', 'N/A')))}\n\n"
    
    if tp1 or tp2 or tp3 or sl:
        msg += f"🎯 <b>أهداف الربح:</b>\n"
        if tp1: msg += f"🎯 TP1: <code>{format_price(tp1)}</code>\n"
        if tp2: msg += f"🎯 TP2: <code>{format_price(tp2)}</code>\n"
        if tp3: msg += f"🎯 TP3: <code>{format_price(tp3)}</code>\n"
        msg += "\n"
        if sl: msg += f"🛑 وقف الخسارة: <code>{format_price(sl)}</code>"
    
    return msg

def format_sell(data):
    symbol = data.get('symbol', 'N/A')
    entry = data.get('entry_price') or data.get('price', 0)
    tp1, tp2, tp3, sl = data.get('tp1'), data.get('tp2'), data.get('tp3'), data.get('stop_loss')
    
    if not (tp1 or tp2 or tp3 or sl) and entry:
        calc = calc_tp_sl(entry, False)
        tp1, tp2, tp3, sl = calc.get('tp1'), calc.get('tp2'), calc.get('tp3'), calc.get('sl')
    
    msg = f"🔴 <b>صفقة شورت (SHORT)</b> 🔴\n\n"
    msg += f"📊 الرمز: {escape_html(symbol)}\n"
    msg += f"💰 سعر الدخول: <code>{format_price(entry)}</code>\n"
    msg += f"⏰ الوقت: {escape_html(data.get('time', 'N/A'))}\n"
    msg += f"📈 الإطار الزمني: {escape_html(format_tf(data.get('timeframe', 'N/A')))}\n\n"
    
    if tp1 or tp2 or tp3 or sl:
        msg += f"🎯 <b>أهداف الربح:</b>\n"
        if tp1: msg += f"🎯 TP1: <code>{format_price(tp1)}</code>\n"
        if tp2: msg += f"🎯 TP2: <code>{format_price(tp2)}</code>\n"
        if tp3: msg += f"🎯 TP3: <code>{format_price(tp3)}</code>\n"
        msg += "\n"
        if sl: msg += f"🛑 وقف الخسارة: <code>{format_price(sl)}</code>"
    
    return msg

def format_tp1(data):
    symbol = data.get('symbol', 'N/A')
    entry = data.get('entry_price', 0)
    exit = data.get('exit_price') or data.get('price', 0)
    tp1 = data.get('tp1')
    
    # إذا لم يكن TP1 موجوداً، احسبه من entry_price
    if not tp1 and entry:
        calc = calc_tp_sl(entry, True)  # افترض Long (يمكن تحسينه)
        tp1 = calc.get('tp1')
    
    # إذا لم يكن exit_price موجوداً أو كان قريباً من entry، استخدم TP1
    if not exit or (entry and abs(float(exit) - float(entry)) < 0.01):
        exit = tp1 or exit
    
    time_str = data.get('time', 'N/A')
    
    msg = f"🎯✅ <b>تم ضرب الهدف الأول (TP1)</b> ✅🎯\n\n"
    msg += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry: msg += f"💰 سعر الدخول: <code>{format_price(entry)}</code>\n"
    if exit: msg += f"💰 سعر الخروج: <code>{format_price(exit)}</code>\n"
    if tp1: msg += f"🎯 TP1: <code>{format_price(tp1)}</code>\n"
    msg += f"⏰ الوقت: {escape_html(time_str)}"
    return msg

def format_tp2(data):
    symbol = data.get('symbol', 'N/A')
    entry = data.get('entry_price', 0)
    exit = data.get('exit_price') or data.get('price', 0)
    tp2 = data.get('tp2')
    
    # إذا لم يكن TP2 موجوداً، احسبه من entry_price
    if not tp2 and entry:
        calc = calc_tp_sl(entry, True)  # افترض Long
        tp2 = calc.get('tp2')
    
    # إذا لم يكن exit_price موجوداً أو كان قريباً من entry، استخدم TP2
    if not exit or (entry and abs(float(exit) - float(entry)) < 0.01):
        exit = tp2 or exit
    
    time_str = data.get('time', 'N/A')
    
    msg = f"🎯✅ <b>تم ضرب الهدف الثاني (TP2)</b> ✅🎯\n\n"
    msg += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry: msg += f"💰 سعر الدخول: <code>{format_price(entry)}</code>\n"
    if exit: msg += f"💰 سعر الخروج: <code>{format_price(exit)}</code>\n"
    if tp2: msg += f"🎯 TP2: <code>{format_price(tp2)}</code>\n"
    msg += f"⏰ الوقت: {escape_html(time_str)}"
    return msg

def format_tp3(data):
    symbol = data.get('symbol', 'N/A')
    entry = data.get('entry_price', 0)
    exit = data.get('exit_price') or data.get('price', 0)
    tp3 = data.get('tp3')
    
    # إذا لم يكن TP3 موجوداً، احسبه من entry_price
    if not tp3 and entry:
        calc = calc_tp_sl(entry, True)  # افترض Long
        tp3 = calc.get('tp3')
    
    # إذا لم يكن exit_price موجوداً أو كان قريباً من entry، استخدم TP3
    if not exit or (entry and abs(float(exit) - float(entry)) < 0.01):
        exit = tp3 or exit
    
    time_str = data.get('time', 'N/A')
    
    msg = f"🚀🚀🚀 <b>تم ضرب الهدف الثالث (TP3)</b> 🚀🚀🚀\n\n"
    msg += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry: msg += f"💰 سعر الدخول: <code>{format_price(entry)}</code>\n"
    if exit: msg += f"💰 سعر الخروج: <code>{format_price(exit)}</code>\n"
    if tp3: msg += f"🎯 TP3: <code>{format_price(tp3)}</code>\n"
    msg += f"⏰ الوقت: {escape_html(time_str)}"
    return msg

def format_sl(data):
    symbol = data.get('symbol', 'N/A')
    entry = data.get('entry_price', 0)
    exit = data.get('exit_price') or data.get('price', 0)
    sl = data.get('stop_loss') or exit
    time_str = data.get('time', 'N/A')
    
    msg = f"🛑😔 <b>تم ضرب وقف الخسارة (Stop Loss)</b> 😔🛑\n\n"
    msg += f"📊 الرمز: {escape_html(symbol)}\n"
    if entry: msg += f"💰 سعر الدخول: <code>{format_price(entry)}</code>\n"
    if exit: msg += f"💰 سعر الخروج: <code>{format_price(exit)}</code>\n"
    if sl: msg += f"🛑 Stop Loss: <code>{format_price(sl)}</code>\n"
    msg += f"⏰ الوقت: {escape_html(time_str)}"
    return msg

# منع التكرار
def is_duplicate(data):
    signal = data.get('signal', '').upper()
    symbol = data.get('symbol', '')
    key = f"{signal}_{symbol}"
    now = datetime.now()
    
    # تنظيف القديم
    expired = [k for k, t in _recent_msgs.items() if (now - t).total_seconds() > 600]
    for k in expired:
        del _recent_msgs[k]
    
    # التحقق
    if key in _last_signal:
        last = _last_signal[key]
        if (now - last).total_seconds() < (60 if signal in ['BUY', 'SELL', 'BUY_REVERSE', 'SELL_REVERSE'] else 30):
            return True
    
    _last_signal[key] = now
    _recent_msgs[key] = now
    return False

# Webhook endpoint
@app.route('/webhook', methods=['GET', 'POST'])
@app.route('/personal/<chat_id>/webhook', methods=['GET', 'POST'])
def webhook(chat_id=None):
    if request.method == 'GET':
        return jsonify({"status": "ok", "message": "Webhook active"}), 200
    
    try:
        # استقبال JSON
        raw = request.get_data(as_text=True)
        if not raw:
            return jsonify({"error": "No data"}), 400
        
        # تنظيف JSON
        start = raw.find('{')
        if start == -1:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # استخراج JSON
        brace = 0
        end = start
        for i in range(start, len(raw)):
            if raw[i] == '{':
                brace += 1
            elif raw[i] == '}':
                brace -= 1
                if brace == 0:
                    end = i + 1
                    break
        
        json_str = raw[start:end]
        json_str = re.sub(r'\{\{plot\([^)]+\)\}\}', 'null', json_str)
        json_str = re.sub(r'\{\{[^}]+\}\}', 'null', json_str)
        
        data = json.loads(json_str)
        signal = data.get('signal', '').upper()
        
        if not signal:
            return jsonify({"error": "Signal required"}), 400
        
        # منع التكرار
        if is_duplicate(data):
            logger.warning(f"⚠️ تكرار: {signal} - {data.get('symbol')}")
            return jsonify({"status": "ignored"}), 200
        
        # حفظ الصفقات في الذاكرة
        if signal in ['BUY', 'LONG', 'SELL', 'SHORT', 'BUY_REVERSE', 'SELL_REVERSE']:
            add_trade(data, signal)
        elif signal in ['TP1_HIT', 'TP1', 'TP2_HIT', 'TP2', 'TP3_HIT', 'TP3', 'STOP_LOSS', 'SL']:
            exit_price = data.get('exit_price') or data.get('price', 0)
            update_trade_status(data.get('symbol', ''), signal, exit_price)
        
        # تحديد chat_id
        target_chat = chat_id or CHAT_ID
        if not target_chat:
            return jsonify({"error": "Chat ID required"}), 500
        
        # تنسيق الرسالة
        msg = None
        if signal in ['BUY', 'LONG']:
            msg = format_buy(data)
        elif signal in ['SELL', 'SHORT']:
            msg = format_sell(data)
        elif signal in ['BUY_REVERSE', 'LONG_REVERSE']:
            msg = format_buy(data)  # نفس format_buy
            msg = msg.replace('لونج', 'لونج عكسي').replace('LONG', 'LONG REVERSE')
            msg = "🟠 " + msg.replace("🟢", "🟠", 1)
        elif signal in ['SELL_REVERSE', 'SHORT_REVERSE']:
            msg = format_sell(data)  # نفس format_sell
            msg = msg.replace('شورت', 'شورت عكسي').replace('SHORT', 'SHORT REVERSE')
        elif signal in ['TP1_HIT', 'TP1']:
            msg = format_tp1(data)
        elif signal in ['TP2_HIT', 'TP2']:
            msg = format_tp2(data)
        elif signal in ['TP3_HIT', 'TP3']:
            msg = format_tp3(data)
        elif signal in ['STOP_LOSS', 'SL']:
            msg = format_sl(data)
        else:
            return jsonify({"error": f"Unknown signal: {signal}"}), 400
        
        # إرسال
        if msg:
            # إذا كان chat_id محدد في URL، أرسل له فقط
            # وإلا أرسل لجميع المجموعات من config.py
            if chat_id:
                # إرسال لمجموعة واحدة (من URL)
                if send_telegram(msg, target_chat):
                    return jsonify({"status": "success", "signal": signal, "chat_id": target_chat}), 200
                else:
                    return jsonify({"status": "error"}), 500
            else:
                # إرسال لجميع المجموعات من config.py
                from config import TELEGRAM_CHAT_IDS
                success_count = 0
                for group_chat_id in TELEGRAM_CHAT_IDS:
                    if send_telegram(msg, group_chat_id):
                        success_count += 1
                
                if success_count > 0:
                    return jsonify({
                        "status": "success",
                        "signal": signal,
                        "sent_to": success_count,
                        "total": len(TELEGRAM_CHAT_IDS)
                    }), 200
                else:
                    return jsonify({"status": "error"}), 500
        else:
            return jsonify({"status": "error"}), 500
            
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/trades', methods=['GET'])
def get_trades():
    """الحصول على جميع الصفقات"""
    trades = load_trades()
    status = request.args.get('status', 'all')  # all, open, closed
    
    if status == 'open':
        trades = {k: v for k, v in trades.items() if v['status'] == 'open'}
    elif status == 'closed':
        trades = {k: v for k, v in trades.items() if v['status'] in ['closed', 'tp3', 'sl']}
    
    return jsonify({
        "status": "success",
        "count": len(trades),
        "trades": trades
    }), 200

@app.route('/trades/<symbol>', methods=['GET'])
def get_trades_by_symbol(symbol):
    """الحصول على صفقات رمز معين"""
    trades = load_trades()
    symbol_trades = {k: v for k, v in trades.items() if v['symbol'] == symbol.upper()}
    
    return jsonify({
        "status": "success",
        "symbol": symbol.upper(),
        "count": len(symbol_trades),
        "trades": symbol_trades
    }), 200

@app.route('/trades/stats', methods=['GET'])
def get_trades_stats():
    """إحصائيات الصفقات"""
    trades = load_trades()
    
    stats = {
        "total": len(trades),
        "open": len([t for t in trades.values() if t['status'] == 'open']),
        "tp1": len([t for t in trades.values() if t['status'] == 'tp1']),
        "tp2": len([t for t in trades.values() if t['status'] == 'tp2']),
        "tp3": len([t for t in trades.values() if t['status'] == 'tp3']),
        "closed": len([t for t in trades.values() if t['status'] == 'closed']),
        "sl": len([t for t in trades.values() if t['status'] == 'sl'])
    }
    
    return jsonify({
        "status": "success",
        "stats": stats
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

