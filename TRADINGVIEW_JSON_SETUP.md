# كيفية استخدام JSON في TradingView Alert - دليل مفصل

## ⚠️ المشكلة الحالية:
الرسائل النصية من TradingView لا تحتوي على TP/SL، لذلك تظهر رسالة:
```
⚠️ Note: TP/SL data not available from text alert.
```

## ✅ الحل:
استخدم JSON في TradingView Alert Message field.

---

## 📋 خطوات الإعداد التفصيلية:

### 1️⃣ إعداد Alert لإشارة BUY

1. افتح المؤشر على TradingView
2. اضغط على أيقونة **Alert** (الجرس 🔔) في أعلى الشاشة
3. في نافذة Alert:
   - اختر **"Webhook URL"** من قائمة Alert Type
   - أدخل الرابط:
     ```
     https://go-production-e51a.up.railway.app/personal/8169000394/webhook
     ```
4. في حقل **"Message"**، الصق هذا الكود:

```json
{"signal":"BUY","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

5. في **"Condition"**، اختر: `BUY Signal for Webhook`
6. اضغط **"Create"**

---

### 2️⃣ إعداد Alert لإشارة SELL

1. نفس الخطوات السابقة
2. في حقل **"Message"**:

```json
{"signal":"SELL","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

3. في **"Condition"**، اختر: `SELL Signal for Webhook`

---

### 3️⃣ إعداد Alert لـ TP1 Hit

1. في حقل **"Message"**:

```json
{"signal":"TP1_HIT","symbol":"{{ticker}}","entry_price":{{plot("Entry Line")}},"exit_price":{{plot("TP Line 1")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. في **"Condition"**، اختر: `TP1 Hit for Webhook` (للشراء) أو `TP1 Hit (Short) for Webhook` (للبيع)

---

### 4️⃣ إعداد Alert لـ TP2 Hit

1. في حقل **"Message"**:

```json
{"signal":"TP2_HIT","symbol":"{{ticker}}","entry_price":{{plot("Entry Line")}},"exit_price":{{plot("TP Line 2")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. في **"Condition"**، اختر: `TP2 Hit for Webhook` أو `TP2 Hit (Short) for Webhook`

---

### 5️⃣ إعداد Alert لـ TP3 Hit

1. في حقل **"Message"**:

```json
{"signal":"TP3_HIT","symbol":"{{ticker}}","entry_price":{{plot("Entry Line")}},"exit_price":{{plot("TP Line 3")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. في **"Condition"**، اختر: `TP3 Hit for Webhook` أو `TP3 Hit (Short) for Webhook`

---

### 6️⃣ إعداد Alert لـ Stop Loss

1. في حقل **"Message"**:

```json
{"signal":"STOP_LOSS","symbol":"{{ticker}}","price":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. في **"Condition"**، اختر: `Stop Loss Hit for Webhook` أو `Stop Loss Hit (Short) for Webhook`

---

### 7️⃣ إعداد Alert لـ Position Closed

1. في حقل **"Message"**:

```json
{"signal":"CLOSE","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. في **"Condition"**، اختر: `Position Closed for Webhook` أو `Position Closed (Short) for Webhook`

---

## ⚠️ ملاحظات مهمة جداً:

### 1. أسماء الـ Plots يجب أن تطابق تماماً:
- `TP Line 1` ✅
- `TP Line 2` ✅
- `TP Line 3` ✅
- `SL Line` ✅
- `Entry Line` ✅

**تحقق من أسماء الـ Plots في المؤشر:**
- في السطر 673: `plot(..., title = "TP Line 1", ...)`
- في السطر 674: `plot(..., title = "TP Line 2", ...)`
- في السطر 675: `plot(..., title = "TP Line 3", ...)`
- في السطر 677: `plot(..., title = "SL Line", ...)`
- في السطر 676: `plot(..., title = "Entry Line", ...)`

### 2. JSON يجب أن يكون صحيحاً:
- ✅ بدون مسافات إضافية
- ✅ جميع الأقواس `{}` موجودة
- ✅ الأرقام بدون علامات اقتباس: `{{close}}` وليس `"{{close}}"`
- ✅ النصوص مع علامات اقتباس: `"{{ticker}}"` وليس `{{ticker}}`

### 3. المتغيرات الخاصة بـ TradingView:
- `{{ticker}}` - اسم الرمز (مثل BTCUSDT)
- `{{close}}` - سعر الإغلاق الحالي
- `{{time}}` - الوقت الحالي
- `{{interval}}` - الإطار الزمني (مثل 15m)
- `{{plot("TP Line 1")}}` - قيمة TP Line 1
- `{{plot("TP Line 2")}}` - قيمة TP Line 2
- `{{plot("TP Line 3")}}` - قيمة TP Line 3
- `{{plot("SL Line")}}` - قيمة SL Line
- `{{plot("Entry Line")}}` - قيمة Entry Line

---

## 📝 مثال على JSON صحيح:

```json
{"signal":"BUY","symbol":"BTCUSDT","entry_price":42850.50,"tp1":43300.75,"tp2":43750.25,"tp3":44200.50,"stop_loss":42150.00,"time":"2024-01-15 14:30","timeframe":"15m"}
```

---

## 🧪 للاختبار:

بعد إعداد Alert:
1. انتظر ظهور إشارة على TradingView
2. تحقق من Logs في Railway Dashboard
3. يجب أن ترى في Logs:
   ```
   INFO:main:Received data: {'signal': 'BUY', 'symbol': 'BTCUSDT', ...}
   ```
4. يجب أن تصل رسالة على Telegram مع TP/SL كاملة

---

## ❌ الأخطاء الشائعة:

### الخطأ: "TP/SL data not available"
**السبب:** لم تستخدم JSON في Alert Message
**الحل:** استخدم JSON في Message field كما هو موضح أعلاه

### الخطأ: "Unknown signal type"
**السبب:** JSON غير صحيح أو signal name خاطئ
**الحل:** تحقق من JSON واسم signal (BUY, SELL, TP1_HIT, إلخ)

### الخطأ: "plot name not found"
**السبب:** اسم الـ Plot في JSON لا يطابق اسم الـ Plot في المؤشر
**الحل:** تحقق من أسماء الـ Plots في المؤشر واستخدمها كما هي

---

## ✅ بعد الإعداد الصحيح:

ستصلك رسائل كاملة مثل:

```
🟢🟢🟢 BUY SIGNAL 🟢🟢🟢

📊 Symbol: BTCUSDT
💰 Entry Price: 42850.50
⏰ Time: 2024-01-15 14:30
📈 Timeframe: 15m

🎯 Take Profit Targets:
🎯 TP1: 43300.75 (+1.05%)
🎯 TP2: 43750.25 (+2.10%)
🎯 TP3: 44200.50 (+3.15%)

🛑 Stop Loss: 42150.00 (-1.63%)
```

---

**بالتوفيق! 🚀**

