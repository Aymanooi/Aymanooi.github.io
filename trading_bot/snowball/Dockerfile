FROM python:3.11-slim

# مكتبات النظام التي تحتاجها numpy/pandas/xgboost
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# انسخ كود البوت (ضع snowball_v22_FINAL.py بجانب هذا الملف)
COPY snowball_v22_FINAL.py .

# قاعدة البيانات + السجلّات تبقى محفوظة عبر volume
VOLUME ["/app/data"]

CMD ["python", "-u", "snowball_v22_FINAL.py"]
