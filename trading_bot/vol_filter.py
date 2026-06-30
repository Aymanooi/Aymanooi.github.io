"""
[9] Volatility Filter — فلتر التقلّب.

يمنع الدخول في بيئتين خطرتين:
  • تقلّب مرتفع جدًا (السعر جنوني → وقف الخسارة يُضرب بسهولة).
  • تقلّب منخفض جدًا (السوق ميت → لا حركة تُذكر، والرسوم تأكل الربح).

نقبل التداول فقط ضمن نطاق تقلّب "صحّي".
"""
import pandas as pd


def volatility_ok(df: pd.DataFrame, i: int, low_q=0.20, high_q=0.90) -> bool:
    """هل تقلّب الشمعة i ضمن النطاق الصحّي (بين النسبتين المئويتين)؟"""
    if "atr_pct" not in df.columns:
        return True
    series = df["atr_pct"].iloc[:i + 1]
    if len(series) < 50 or pd.isna(series.iloc[-1]):
        return False
    lo = series.quantile(low_q)
    hi = series.quantile(high_q)
    val = series.iloc[-1]
    return bool(lo <= val <= hi)
