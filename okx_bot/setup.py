"""Setup wizard - run this first to enter your API credentials"""
import re

CONFIG_FILE = "config.py"

def update_config(key, value):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        rf'^({key}\s*=\s*).*$',
        f'{key} = "{value}"',
        content,
        flags=re.MULTILINE
    )
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(content)

print("=" * 50)
print("  OKX Bot - إعداد بيانات الدخول")
print("=" * 50)
print()

api_key = input("API Key: ").strip()
api_secret = input("API Secret: ").strip()
passphrase = input("Passphrase: ").strip()

print()
mode = input("الوضع (1=تجريبي، 0=حقيقي) [اضغط Enter للتجريبي]: ").strip()
if mode not in ("0", "1"):
    mode = "1"

update_config("API_KEY", api_key)
update_config("API_SECRET", api_secret)
update_config("PASSPHRASE", passphrase)
update_config("IS_DEMO", mode)

mode_label = "تجريبي 🧪" if mode == "1" else "حقيقي 💰"
print()
print(f"✅ تم الحفظ! الوضع: {mode_label}")
print("الآن شغّل البوت: python bot.py")
