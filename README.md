# TradingView Webhook to Telegram Bot

نظام لاستقبال إشارات التداول من TradingView وإرسالها إلى Telegram Bot.

## المميزات

- ✅ استقبال إشارات التداول من TradingView عبر Webhook
- ✅ إرسال رسائل Telegram تلقائياً
- ✅ دعم جميع الإشارات السبع:
  - BUY Signal (إشارة شراء)
  - SELL Signal (إشارة بيع)
  - TP1 Hit (الهدف الأول)
  - TP2 Hit (الهدف الثاني)
  - TP3 Hit (الهدف الثالث)
  - Stop Loss (وقف الخسارة)
  - Position Closed (إغلاق المركز)
- ✅ حساب النسب المئوية تلقائياً
- ✅ بيانات ديناميكية لكل عملة

## المتطلبات

- Python 3.11+
- حساب Telegram Bot
- حساب Railway (للنشر)

## التثبيت والإعداد

### 1. إنشاء Telegram Bot

1. افتح [@BotFather](https://t.me/BotFather) على Telegram
2. أرسل `/newbot` واتبع التعليمات
3. احفظ `Bot Token`
4. أرسل `/mybots` → اختر البوت → API Token

### 2. الحصول على Chat ID

1. أرسل رسالة للبوت
2. افتح هذا الرابط (استبدل `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. ابحث عن `"chat":{"id":123456789}` وانسخ الرقم

### 3. إعداد المشروع محلياً (اختياري)

```bash
# Clone المشروع
git clone <repository-url>
cd <project-folder>

# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# تثبيت المكتبات
pip install -r requirements.txt

# إنشاء ملف .env
cp .env.example .env

# تعديل .env وإضافة:
# TELEGRAM_BOT_TOKEN=your_token
# TELEGRAM_CHAT_ID=your_chat_id
```

### 4. النشر على Railway

1. اذهب إلى [Railway.app](https://railway.app)
2. أنشئ مشروع جديد
3. اختر "Deploy from GitHub" أو "Empty Project"
4. أضف المتغيرات التالية في Settings → Variables:
   - `TELEGRAM_BOT_TOKEN`: رمز البوت
   - `TELEGRAM_CHAT_ID`: معرف المحادثة
5. Railway سيتعرف تلقائياً على `requirements.txt` و `runtime.txt`

### 5. الحصول على Webhook URL

بعد النشر على Railway:
1. اذهب إلى Settings → Domains
2. انسخ الرابط (مثل: `https://your-app.railway.app`)
3. Webhook URL سيكون: `https://your-app.railway.app/webhook`

## إعداد TradingView

### تعديل ملف المؤشر

أضف الكود التالي في نهاية ملف المؤشر Pine Script:

```pine
// ═══════════════════════════════════════════════════════════════════════════
// 🔗 Webhook Integration - إرسال الإشارات إلى Webhook
// ═══════════════════════════════════════════════════════════════════════════

webhook_url = "https://your-app.railway.app/webhook"

// Function to send webhook
send_webhook(signal_type, symbol, entry_price, tp1, tp2, tp3, stop_loss, time_str, timeframe_str) =>
    var url = webhook_url
    var json_data = '{"signal":"' + signal_type + '","symbol":"' + symbol + '","entry_price":' + str.tostring(entry_price) + ',"tp1":' + str.tostring(tp1) + ',"tp2":' + str.tostring(tp2) + ',"tp3":' + str.tostring(tp3) + ',"stop_loss":' + str.tostring(stop_loss) + ',"time":"' + time_str + '","timeframe":"' + timeframe_str + '"}'
    request.security(syminfo.tickerid, timeframe.period, json_data, lookahead=barmerge.lookahead_off)

// عند BUY Signal
if buySignal and TPSType == "ATR" and tradeDateIsAllowed
    time_str = str.tostring(time, "yyyy-MM-dd HH:mm")
    timeframe_str = str.tostring(timeframe.multiplier) + str.tostring(timeframe.period)
    send_webhook("BUY", syminfo.ticker, close, tp1Line, tp2Line, tp3Line, slLine, time_str, timeframe_str)

// عند SELL Signal
if sellSignal and TPSType == "ATR" and tradeDateIsAllowed
    time_str = str.tostring(time, "yyyy-MM-dd HH:mm")
    timeframe_str = str.tostring(timeframe.multiplier) + str.tostring(timeframe.period)
    send_webhook("SELL", syminfo.ticker, close, tp1Line, tp2Line, tp3Line, slLine, time_str, timeframe_str)
```

**ملاحظة:** Pine Script لا يدعم HTTP requests مباشرة. ستحتاج إلى استخدام TradingView Alerts لإرسال Webhook.

### إعداد TradingView Alerts

1. افتح المؤشر على TradingView
2. اضغط على "Alert" (أيقونة الجرس)
3. اختر "Webhook URL"
4. أدخل: `https://your-app.railway.app/webhook`
5. في Message، استخدم التنسيق التالي:

**لإشارة BUY:**
```
{"signal":"BUY","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**لإشارة SELL:**
```
{"signal":"SELL","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

## تنسيق البيانات

### BUY/SELL Signal:
```json
{
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "entry_price": 42850.50,
  "tp1": 43300.75,
  "tp2": 43750.25,
  "tp3": 44200.50,
  "stop_loss": 42150.00,
  "time": "2024-01-15 14:30",
  "timeframe": "15m"
}
```

### TP1/TP2/TP3 Hit:
```json
{
  "signal": "TP1_HIT",
  "symbol": "BTCUSDT",
  "entry_price": 42850.50,
  "exit_price": 43300.75,
  "time": "2024-01-15 15:30",
  "timeframe": "15m"
}
```

### Stop Loss:
```json
{
  "signal": "STOP_LOSS",
  "symbol": "BTCUSDT",
  "price": 42150.00,
  "time": "2024-01-15 17:20",
  "timeframe": "15m"
}
```

### Position Closed:
```json
{
  "signal": "CLOSE",
  "symbol": "BTCUSDT",
  "price": 43500.00,
  "time": "2024-01-15 16:45",
  "timeframe": "15m"
}
```

## الاختبار

```bash
# اختبار محلي
python main.py

# اختبار Webhook (استبدل البيانات)
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "signal": "BUY",
    "symbol": "BTCUSDT",
    "entry_price": 42850.50,
    "tp1": 43300.75,
    "tp2": 43750.25,
    "tp3": 44200.50,
    "stop_loss": 42150.00,
    "time": "2024-01-15 14:30",
    "timeframe": "15m"
  }'
```

## الأمان

- استخدم `WEBHOOK_SECRET` في الإنتاج للتحقق من الطلبات
- استخدم HTTPS دائماً
- لا تشارك `TELEGRAM_BOT_TOKEN` أو `TELEGRAM_CHAT_ID`

## الدعم

إذا واجهت أي مشاكل، تأكد من:
1. صحة `TELEGRAM_BOT_TOKEN` و `TELEGRAM_CHAT_ID`
2. أن Webhook URL يعمل (اختبره عبر curl)
3. أن TradingView Alert يرسل البيانات بشكل صحيح

## الترخيص

هذا المشروع مفتوح المصدر.

