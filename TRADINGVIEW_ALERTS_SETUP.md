# إعداد TradingView Alerts للـ Webhook

## خطوات الإعداد

### 1. إعداد Alert لإشارة BUY

1. افتح المؤشر على TradingView
2. اضغط على أيقونة **Alert** (الجرس 🔔)
3. اختر **Webhook URL**
4. أدخل الرابط: `https://your-app.railway.app/webhook`
5. في حقل **Message**، استخدم الكود التالي:

```json
{"signal":"BUY","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

6. اختر **Condition**: `BUY Signal for Webhook`
7. اضغط **Create**

---

### 2. إعداد Alert لإشارة SELL

1. نفس الخطوات السابقة
2. في حقل **Message**:

```json
{"signal":"SELL","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

3. اختر **Condition**: `SELL Signal for Webhook`

---

### 3. إعداد Alert لـ TP1 Hit

1. في حقل **Message**:

```json
{"signal":"TP1_HIT","symbol":"{{ticker}}","entry_price":{{plot("Entry Line")}},"exit_price":{{plot("TP Line 1")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. اختر **Condition**: `TP1 Hit for Webhook` أو `TP1 Hit (Short) for Webhook`

---

### 4. إعداد Alert لـ TP2 Hit

1. في حقل **Message**:

```json
{"signal":"TP2_HIT","symbol":"{{ticker}}","entry_price":{{plot("Entry Line")}},"exit_price":{{plot("TP Line 2")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. اختر **Condition**: `TP2 Hit for Webhook` أو `TP2 Hit (Short) for Webhook`

---

### 5. إعداد Alert لـ TP3 Hit

1. في حقل **Message**:

```json
{"signal":"TP3_HIT","symbol":"{{ticker}}","entry_price":{{plot("Entry Line")}},"exit_price":{{plot("TP Line 3")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. اختر **Condition**: `TP3 Hit for Webhook` أو `TP3 Hit (Short) for Webhook`

---

### 6. إعداد Alert لـ Stop Loss

1. في حقل **Message**:

```json
{"signal":"STOP_LOSS","symbol":"{{ticker}}","price":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. اختر **Condition**: `Stop Loss Hit for Webhook` أو `Stop Loss Hit (Short) for Webhook`

---

### 7. إعداد Alert لـ Position Closed

1. في حقل **Message**:

```json
{"signal":"CLOSE","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","timeframe":"{{interval}}"}
```

2. اختر **Condition**: `Position Closed for Webhook` أو `Position Closed (Short) for Webhook`

---

## ملاحظات مهمة

1. **استبدل الرابط**: استبدل `https://your-app.railway.app/webhook` برابط Railway الخاص بك
2. **Plot Names**: تأكد من أن أسماء الـ Plots في المؤشر تطابق:
   - `TP Line 1`
   - `TP Line 2`
   - `TP Line 3`
   - `SL Line`
   - `Entry Line`
3. **التأكد من البيانات**: بعد إنشاء Alert، اختبره بمراقبة Logs في Railway
4. **Format**: تأكد من أن JSON صحيح (بدون أخطاء)

---

## اختبار الـ Alerts

بعد إنشاء جميع الـ Alerts:

1. انتظر ظهور إشارة
2. تحقق من Logs في Railway Dashboard
3. تحقق من رسالة Telegram
4. إذا لم تصل الرسالة، تحقق من:
   - صحة Webhook URL
   - صحة JSON في Message
   - صحة TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID

---

## Troubleshooting

### المشكلة: الرسالة لا تصل

**الحل:**
- تحقق من Logs في Railway
- تحقق من صحة JSON في Alert Message
- تأكد من أن Webhook URL صحيح

### المشكلة: رسالة خطأ في JSON

**الحل:**
- تأكد من أن جميع الأقواس `{}` صحيحة
- تأكد من أن الأرقام بدون علامات اقتباس
- استخدم `{{close}}` وليس `"{{close}}"`

### المشكلة: البيانات غير صحيحة

**الحل:**
- تحقق من أن أسماء الـ Plots صحيحة
- تأكد من أن `{{ticker}}` و `{{time}}` و `{{interval}}` صحيحة

