# إشارات TradingView JSON - الإعدادات

هذا الملف يحتوي على جميع الإشارات الـ 7 بتنسيق JSON جاهزة للاستخدام في TradingView Alert Message field.

---

## 📝 ملاحظات مهمة:

1. **استبدل القيم** في JSON بالقيم الفعلية من Pine Script
2. استخدم المتغيرات من Pine Script مثل:
   - `{{ticker}}` - رمز العملة
   - `{{close}}` - السعر الحالي
   - `{{time}}` - الوقت
   - `{{interval}}` - الإطار الزمني
   - المتغيرات الخاصة بك من الاستراتيجية

3. **انسخ JSON** إلى حقل "Message" في إعدادات Alert في TradingView

---

## 1️⃣ إشارة BUY (شراء)

```json
{"signal":"BUY","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{tp1_price}},"tp2":{{tp2_price}},"tp3":{{tp3_price}},"stop_loss":{{stop_loss_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**مثال مع قيم:**
```json
{"signal":"BUY","symbol":"BTCUSDT","entry_price":42850.50,"tp1":43300.75,"tp2":43750.25,"tp3":44200.50,"stop_loss":42150.00,"time":"2024-01-15 14:30:00","timeframe":"15m"}
```

---

## 2️⃣ إشارة SELL (بيع)

```json
{"signal":"SELL","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{tp1_price}},"tp2":{{tp2_price}},"tp3":{{tp3_price}},"stop_loss":{{stop_loss_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**مثال مع قيم:**
```json
{"signal":"SELL","symbol":"BTCUSDT","entry_price":42850.50,"tp1":42400.25,"tp2":41950.75,"tp3":41500.50,"stop_loss":43550.00,"time":"2024-01-15 14:30:00","timeframe":"15m"}
```

---

## 3️⃣ إشارة TP1_HIT (الهدف الأول تم تحقيقه)

```json
{"signal":"TP1_HIT","symbol":"{{ticker}}","entry_price":{{entry_price}},"exit_price":{{tp1_price}},"tp1":{{tp1_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**أو يمكن استخدام:**
```json
{"signal":"TP1","symbol":"{{ticker}}","entry_price":{{entry_price}},"exit_price":{{tp1_price}},"tp1":{{tp1_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**مثال مع قيم:**
```json
{"signal":"TP1_HIT","symbol":"BTCUSDT","entry_price":42850.50,"exit_price":43300.75,"tp1":43300.75,"time":"2024-01-15 15:45:00","timeframe":"15m"}
```

---

## 4️⃣ إشارة TP2_HIT (الهدف الثاني تم تحقيقه)

```json
{"signal":"TP2_HIT","symbol":"{{ticker}}","entry_price":{{entry_price}},"exit_price":{{tp2_price}},"tp2":{{tp2_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**أو يمكن استخدام:**
```json
{"signal":"TP2","symbol":"{{ticker}}","entry_price":{{entry_price}},"exit_price":{{tp2_price}},"tp2":{{tp2_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**مثال مع قيم:**
```json
{"signal":"TP2_HIT","symbol":"BTCUSDT","entry_price":42850.50,"exit_price":43750.25,"tp2":43750.25,"time":"2024-01-15 16:30:00","timeframe":"15m"}
```

---

## 5️⃣ إشارة TP3_HIT (الهدف الثالث تم تحقيقه)

```json
{"signal":"TP3_HIT","symbol":"{{ticker}}","entry_price":{{entry_price}},"exit_price":{{tp3_price}},"tp3":{{tp3_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**أو يمكن استخدام:**
```json
{"signal":"TP3","symbol":"{{ticker}}","entry_price":{{entry_price}},"exit_price":{{tp3_price}},"tp3":{{tp3_price}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**مثال مع قيم:**
```json
{"signal":"TP3_HIT","symbol":"BTCUSDT","entry_price":42850.50,"exit_price":44200.50,"tp3":44200.50,"time":"2024-01-15 17:15:00","timeframe":"15m"}
```

---

## 6️⃣ إشارة STOP_LOSS (وقف الخسارة)

```json
{"signal":"STOP_LOSS","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**أو يمكن استخدام:**
```json
{"signal":"SL","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**مثال مع قيم:**
```json
{"signal":"STOP_LOSS","symbol":"BTCUSDT","price":42150.00,"time":"2024-01-15 15:20:00","timeframe":"15m"}
```

---

## 7️⃣ إشارة CLOSE (إغلاق المركز)

```json
{"signal":"CLOSE","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**أو يمكن استخدام:**
```json
{"signal":"POSITION_CLOSED","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**مثال مع قيم:**
```json
{"signal":"CLOSE","symbol":"BTCUSDT","price":44000.00,"time":"2024-01-15 18:00:00","timeframe":"15m"}
```

---

## 🔧 كيفية استخدامها في Pine Script:

### مثال للإشارة BUY:

```pinescript
if condition_buy
    alert_message = '{"signal":"BUY","symbol":"' + syminfo.ticker + '","entry_price":' + str.tostring(close) + ',"tp1":' + str.tostring(tp1) + ',"tp2":' + str.tostring(tp2) + ',"tp3":' + str.tostring(tp3) + ',"stop_loss":' + str.tostring(sl) + ',"time":"' + str.tostring(time, "yyyy-MM-dd HH:mm:ss") + '","timeframe":"' + timeframe.period + '"}'
    alert(alert_message, alert.freq_once_per_bar)
```

### مثال للإشارة TP1_HIT:

```pinescript
if ta.crossover(close, tp1)
    alert_message = '{"signal":"TP1_HIT","symbol":"' + syminfo.ticker + '","entry_price":' + str.tostring(entry_price) + ',"exit_price":' + str.tostring(tp1) + ',"tp1":' + str.tostring(tp1) + ',"time":"' + str.tostring(time, "yyyy-MM-dd HH:mm:ss") + '","timeframe":"' + timeframe.period + '"}'
    alert(alert_message, alert.freq_once_per_bar)
```

---

## 📋 ملخص الحقول المطلوبة لكل إشارة:

| الإشارة | الحقول المطلوبة |
|---------|-----------------|
| **BUY** | signal, symbol, entry_price, tp1, tp2, tp3, stop_loss, time, timeframe |
| **SELL** | signal, symbol, entry_price, tp1, tp2, tp3, stop_loss, time, timeframe |
| **TP1_HIT** | signal, symbol, entry_price, exit_price (أو tp1), time, timeframe |
| **TP2_HIT** | signal, symbol, entry_price, exit_price (أو tp2), time, timeframe |
| **TP3_HIT** | signal, symbol, entry_price, exit_price (أو tp3), time, timeframe |
| **STOP_LOSS** | signal, symbol, price, time, timeframe |
| **CLOSE** | signal, symbol, price, time, timeframe |

---

## ⚠️ نصائح مهمة:

1. **تأكد من صحة JSON**: استخدم JSON validator للتأكد من صحة التنسيق
2. **لا تستخدم مسافات إضافية**: JSON يجب أن يكون في سطر واحد بدون مسافات (أو استخدم minified JSON)
3. **استخدم المتغيرات الديناميكية**: استبدل القيم الثابتة بمتغيرات من Pine Script
4. **اختبر الإشارات**: تأكد من أن كل إشارة تعمل بشكل صحيح قبل الاستخدام

---

## 🔗 Webhook URL:

استخدم هذا الرابط في إعدادات TradingView Alert:
- **للـ Chat ID المحدد**: `https://your-domain.com/personal/YOUR_CHAT_ID/webhook`
- **للـ Chat ID الافتراضي**: `https://your-domain.com/webhook`

---

تم إنشاء هذا الملف بواسطة: TradingView Webhook Bot
التاريخ: 2024

