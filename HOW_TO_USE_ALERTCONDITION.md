# 📖 كيفية استخدام alertcondition() لإرسال JSON تلقائياً

## ✅ الحل النهائي:

تم تعديل المؤشر لاستخدام `alertcondition()` فقط بدلاً من `alert()`. هذا يمنع TradingView من إرسال الرسالة الافتراضية التي تحتوي على Position Size.

---

## 🎯 خطوات الإعداد (TradingView Alert):

### 1️⃣ افتح المؤشر على TradingView

### 2️⃣ اضغط على أيقونة **Alert** (الجرس 🔔)

### 3️⃣ في نافذة **Create Alert**:

#### أ) اختر **"Webhook URL"** من قائمة **Alert Type**

#### ب) أدخل الرابط:
```
https://go-production-e51a.up.railway.app/personal/8169000394/webhook
```

#### ج) **⚠️ المهم جداً:** اترك حقل **"Message"** **فارغاً تماماً** ✅

**لماذا؟** لأن `alertcondition()` يحتوي على JSON في message field، وإذا ملأت Message field، سيستخدم ما كتبته بدلاً من JSON من `alertcondition()`.

#### د) في **"Condition"**، اختر من القائمة:

**للإشارات:**
- ✅ `BUY Signal for Webhook` (للشراء)
- ✅ `SELL Signal for Webhook` (للبيع)

**للأهداف:**
- ✅ `TP1 Hit for Webhook` (للشراء)
- ✅ `TP2 Hit for Webhook` (للشراء)
- ✅ `TP3 Hit for Webhook` (للشراء)
- ✅ `TP1 Hit (Short) for Webhook` (للبيع)
- ✅ `TP2 Hit (Short) for Webhook` (للبيع)
- ✅ `TP3 Hit (Short) for Webhook` (للبيع)

**لوقف الخسارة:**
- ✅ `Stop Loss Hit for Webhook` (للشراء)
- ✅ `Stop Loss Hit (Short) for Webhook` (للبيع)

**لإغلاق المركز:**
- ✅ `Position Closed for Webhook` (للشراء)
- ✅ `Position Closed (Short) for Webhook` (للبيع)

#### هـ) اضغط **"Create"**

---

## 🔄 للإنشاء السريع (7 Alerts):

### Alert 1: BUY Signal
- Condition: `BUY Signal for Webhook`
- Message: **فارغ**

### Alert 2: SELL Signal
- Condition: `SELL Signal for Webhook`
- Message: **فارغ**

### Alert 3: TP1 Hit
- Condition: `TP1 Hit for Webhook` (أو `TP1 Hit (Short) for Webhook` للبيع)
- Message: **فارغ**

### Alert 4: TP2 Hit
- Condition: `TP2 Hit for Webhook` (أو `TP2 Hit (Short) for Webhook` للبيع)
- Message: **فارغ**

### Alert 5: TP3 Hit
- Condition: `TP3 Hit for Webhook` (أو `TP3 Hit (Short) for Webhook` للبيع)
- Message: **فارغ**

### Alert 6: Stop Loss
- Condition: `Stop Loss Hit for Webhook` (أو `Stop Loss Hit (Short) for Webhook` للبيع)
- Message: **فارغ**

### Alert 7: Position Closed
- Condition: `Position Closed for Webhook` (أو `Position Closed (Short) for Webhook` للبيع)
- Message: **فارغ**

---

## ✅ النتيجة:

عندما يحدث الشرط:
1. ✅ `alertcondition()` يرسل JSON تلقائياً
2. ✅ JSON يحتوي على `{{close}}` (السعر الحقيقي) ✅
3. ✅ JSON يحتوي على `{{plot("TP Line 1")}}` إلخ (TP/SL الحقيقية) ✅
4. ✅ JSON يحتوي على `{{interval}}` (Timeframe الحقيقي) ✅
5. ✅ **لا توجد رسالة افتراضية من strategy()** ✅
6. ✅ **لا يوجد Position Size** ✅

---

## ⚠️ ملاحظات مهمة:

### 1. Message Field يجب أن يكون فارغاً:
- ❌ **لا** تملأ Message field
- ✅ **اتركه فارغاً** تماماً

### 2. Condition يجب أن يكون من `alertcondition()`:
- ✅ اختر من القائمة المنسدلة
- ❌ لا تستخدم "Any alert() function call"

### 3. JSON يرسل تلقائياً:
- ✅ `alertcondition()` يرسل JSON من message field تلقائياً
- ✅ لا حاجة لكتابة JSON يدوياً

---

## 🎉 النتيجة النهائية:

**الرسائل ستصل مع:**
- ✅ السعر الحقيقي (وليس Position Size)
- ✅ TP/SL الكاملة
- ✅ Timeframe الحقيقي
- ✅ جميع البيانات دقيقة 100%

**بعد إعداد Alerts بهذه الطريقة، ستصل الرسائل بشكل تلقائي وكامل! 🚀**

