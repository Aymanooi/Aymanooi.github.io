# ☁️ تشغيل البوت 24/7 مجاناً على Oracle Cloud Always Free

خادم Linux مجاني **للأبد** يعمل بلا توقف. تحتاج فقط: **متصفح** + **بطاقة** للتحقق (بدون أي خصم — Always Free).

---

## الجزء 1 — إنشاء الحساب (مرة واحدة)

1. ادخل: **https://www.oracle.com/cloud/free/**
2. اضغط **Start for free**.
3. املأ بياناتك:
   - اختر بلدك بدقة (يحدد منطقة الخادم).
   - أدخل بريداً حقيقياً وفعّله.
4. **التحقق بالبطاقة**: يطلب بطاقة (Visa/Mastercard). يسحب مبلغاً رمزياً (~1$) ثم **يعيده** — للتأكد أنك إنسان فقط. لن تُحاسَب على Always Free.
5. اختر كلمة مرور قوية وأكمل التسجيل.

> ملاحظة: إن لم تملك بطاقة، توجد بطاقات بنكية رقمية مجانية في معظم الدول. هذا الحاجز الوحيد المتبقي.

---

## الجزء 2 — إنشاء الخادم المجاني

1. من لوحة التحكم: القائمة (☰) → **Compute** → **Instances** → **Create Instance**.
2. **الاسم**: `snowball-bot`.
3. **Image and shape**:
   - Image: **Canonical Ubuntu 22.04**.
   - Shape: اضغط **Change shape** → اختر:
     - **Ampere (ARM)** → `VM.Standard.A1.Flex` → 1 OCPU + 6 GB RAM (الأقوى مجاناً)،
     - أو إن ظهر "Out of capacity" اختر **AMD** → `VM.Standard.E2.1.Micro` (مجاني دائماً ومتوفر غالباً).
4. **Networking**: اتركه افتراضياً (ينشئ شبكة جديدة).
5. **SSH keys**: اختر **Save private key** و **Save public key** → نزّل الملفين واحتفظ بهما (مهم!).
6. اضغط **Create**. انتظر دقيقة حتى تصبح الحالة **Running**.

---

## الجزء 3 — الدخول للخادم (من المتصفح مباشرة)

1. أعلى يمين لوحة التحكم، اضغط أيقونة **Cloud Shell** (`>_`). تفتح طرفية Linux داخل متصفحك.
2. ارفع مفتاحك الخاص: في Cloud Shell، قائمة الإعدادات → **Upload** → اختر ملف المفتاح الخاص (`.key`).
3. اتصل بالخادم (استبدل `<IP>` بعنوان الخادم الظاهر في صفحة الـ Instance):
```bash
chmod 600 ssh-key-*.key
ssh -i ssh-key-*.key ubuntu@<IP>
```
اكتب `yes` عند السؤال أول مرة.

---

## الجزء 4 — نقل ملفات البوت

أسهل طريقة — انسخ ملفات الكيت إلى الخادم. اختر إحدى الطريقتين:

**الطريقة أ (رفع مباشر):** في Cloud Shell ارفع `snowball-deploy.zip` (Upload)، ثم:
```bash
scp -i ssh-key-*.key snowball-deploy.zip ubuntu@<IP>:~
ssh -i ssh-key-*.key ubuntu@<IP>
sudo apt update && sudo apt install -y unzip
unzip snowball-deploy.zip && cd snowball-deploy
```

**الطريقة ب (من مستودع خاص على GitHub):** ضع الكيت في مستودع GitHub **خاص (Private)** ثم على الخادم:
```bash
git clone https://github.com/<user>/<private-repo>.git
cd <private-repo>
```

---

## الجزء 5 — التشغيل 24/7

```bash
# تثبيت Docker
curl -fsSL https://get.docker.com | sh

# وضع المفاتيح
cp .env.example .env
nano .env            # املأ OKX_API_KEY / OKX_SECRET_KEY / OKX_PASSPHRASE  (Ctrl+O ثم Enter ثم Ctrl+X)

# تشغيل دائم (يعيد نفسه تلقائياً عند أي توقف)
sudo docker compose up -d --build
```

تأكد أنه يعمل:
```bash
sudo docker compose logs -f      # متابعة حيّة (Ctrl+C للخروج — البوت يستمر)
```

✅ الآن البوت يعمل 24/7 ويعيد تشغيل نفسه تلقائياً، حتى لو أغلقت المتصفح أو طفئ جهازك.

---

## الجزء 6 — أمان مفاتيح OKX (لا تتجاوزه)

عند إنشاء مفتاح API في OKX:
- فعّل صلاحية **Trade** فقط.
- **عطّل Withdraw** نهائياً (حتى لو سُرق المفتاح لا يستطيع أحد سحب أموالك).
- قيّد المفتاح بعنوان IP الخاص بخادم Oracle (IP Whitelist).

---

## ⚠️ تذكير أخير
البوت مضبوط على `PAPER_TRADING = True`. اتركه أسبوعين في المحاكاة وراقب النتائج.
حوّله إلى `False` للتداول الحقيقي **فقط** بعد أن تثق بأدائه، وبمبلغ تتحمّل خسارته بالكامل.
الرافعة x10–x20 تربح بسرعة وتخسر أسرع.
```bash
nano snowball_v22_FINAL.py   # غيّر PAPER_TRADING إلى False
sudo docker compose up -d --build
```
