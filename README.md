# TradingView Webhook to Telegram Bot

Python application that receives trading signals from TradingView via webhook and forwards them to Telegram.

## ⚠️ مشكلة Position Size vs Price (السعر الحقيقي)

### المشكلة:
TradingView Alert يرسل أحياناً **Position Size** (حجم المركز) بدلاً من **Price** (سعر العملة الحقيقي).

**مثال:**
- ❌ Position Size: `3,979,480` (حجم المركز)
- ✅ Real Price: `0.05` (سعر العملة الحقيقي)

### الحل: استخدام JSON في Alert Message

**يجب استخدام JSON في TradingView Alert Message field للحصول على السعر الحقيقي!**

---

## 📋 خطوات الإعداد (TradingView Alert):

### 1️⃣ افتح المؤشر على TradingView

### 2️⃣ اضغط على أيقونة **Alert** (الجرس 🔔)

### 3️⃣ في نافذة Create Alert:

#### أ) اختر **"Webhook URL"** من قائمة **Alert Type**

#### ب) أدخل الرابط:
```
https://go-production-e51a.up.railway.app/personal/8169000394/webhook
```

#### ج) ⚠️ **المهم جداً:** في حقل **"Message"**، الصق هذا الكود:

**للإشارة BUY:**
```json
{"signal":"BUY","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

**للإشارة SELL:**
```json
{"signal":"SELL","symbol":"{{ticker}}","entry_price":{{close}},"tp1":{{plot("TP Line 1")}},"tp2":{{plot("TP Line 2")}},"tp3":{{plot("TP Line 3")}},"stop_loss":{{plot("SL Line")}},"time":"{{time}}","timeframe":"{{interval}}"}
```

#### د) في **"Condition"**، اختر:
- `BUY Signal for Webhook` (للشراء)
- `SELL Signal for Webhook` (للبيع)

---

## ✅ ما يحدث بعد الإعداد الصحيح:

1. ✅ السعر الحقيقي يظهر (ليس Position Size)
2. ✅ TP/SL الكاملة تظهر
3. ✅ Timeframe الحقيقي يظهر
4. ✅ جميع البيانات دقيقة 100%

---

## ⚠️ إذا لم تستخدم JSON:

- ❌ السعر قد يكون Position Size (رقم كبير)
- ❌ TP/SL لن تظهر
- ❌ Timeframe سيكون "N/A"

---

## 📖 ملاحظات إضافية:

- أسماء الـ Plots في JSON يجب أن تطابق أسماء الـ Plots في المؤشر
- JSON يجب أن يكون في سطر واحد
- تأكد من أن `{{close}}` موجود في JSON (هذا السعر الحقيقي)

---

**بعد تطبيق هذا الحل، ستصل الرسائل مع السعر الحقيقي والبيانات الكاملة! 🚀**
