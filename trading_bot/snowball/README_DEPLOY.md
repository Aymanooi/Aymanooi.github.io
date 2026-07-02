# 🚀 تشغيل البوت حقيقياً 24/7 على خادم VPS

هذه الحزمة تُشغّل `snowball_v22_FINAL.py` تشغيلاً حقيقياً ومستمراً (يعيد نفسه تلقائياً عند أي انقطاع).

> ⚠️ **تحذير مالي:** هذا البوت يتداول عقوداً آجلة برافعة تصل إلى x20.
> قد تخسر رأس مالك بالكامل. ابدأ بـ `PAPER_TRADING = True` لمدة أسبوعين على الأقل
> قبل تحويله إلى `False`.

---

## الخطوة 1 — استأجر خادم VPS
أي مزود يكفي (DigitalOcean / Contabo / Hetzner / Vultr). المواصفات الدنيا:
- 2 vCPU، 2–4 GB RAM، نظام Ubuntu 22.04
- اختر منطقة قريبة من سيرفرات OKX (سنغافورة / طوكيو) لأقل تأخير

## الخطوة 2 — انسخ الملفات إلى الخادم
ضع هذه الملفات معاً في مجلد واحد على الخادم:
```
snowball_v22_FINAL.py
requirements.txt
Dockerfile
docker-compose.yml
.env.example
.gitignore
```

## الخطوة 3 — ثبّت Docker
```bash
curl -fsSL https://get.docker.com | sh
```

## الخطوة 4 — ضع مفاتيحك
```bash
cp .env.example .env
nano .env        # املأ OKX_API_KEY و OKX_SECRET_KEY و OKX_PASSPHRASE
```

## الخطوة 5 — شغّله 24/7 بأمر واحد
```bash
docker compose up -d --build
```

## المتابعة والتحكم
```bash
docker compose logs -f          # متابعة السجلّات الحيّة
docker compose restart          # إعادة تشغيل
docker compose down             # إيقاف
```

---

## 🔴 التحويل إلى تداول حقيقي (بعد فترة المحاكاة)
في `snowball_v22_FINAL.py` غيّر:
```python
PAPER_TRADING: bool = False
```
ثم أعد البناء:
```bash
docker compose up -d --build
```

---

## بديل بدون Docker (systemd)
```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install -r requirements.txt
```
أنشئ خدمة `/etc/systemd/system/snowball.service`:
```ini
[Unit]
Description=Snowball Trading Bot
After=network-online.target

[Service]
WorkingDirectory=/root/snowball
EnvironmentFile=/root/snowball/.env
ExecStart=/usr/bin/python3 -u /root/snowball/snowball_v22_FINAL.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
ثم:
```bash
sudo systemctl enable --now snowball
sudo journalctl -u snowball -f
```

---

## 🔐 أمان المفاتيح (مهم جداً)
- في إعدادات OKX API: فعّل **التداول** فقط، وعطّل **السحب** نهائياً.
- قيّد المفتاح بعنوان IP الخاص بخادمك (IP Whitelist).
- لا ترفع `.env` إلى GitHub أبداً (محمي مسبقاً عبر `.gitignore`).
