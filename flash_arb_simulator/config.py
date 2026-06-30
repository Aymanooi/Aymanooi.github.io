"""
إعدادات كاشف المراجحة (وضع المحاكاة فقط).

كل القيم هنا قابلة للتعديل. لا توجد مفاتيح خاصة ولا تنفيذ فعلي للمعاملات.
"""

from dataclasses import dataclass, field


# عناوين عملات (mints) شائعة على سولانا
MINTS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
}

# عدد المنازل العشرية لكل عملة (لتحويل الوحدات الذرية إلى مبلغ مقروء)
DECIMALS = {
    "SOL": 9,
    "USDC": 6,
    "USDT": 6,
    "JUP": 6,
    "BONK": 5,
    "JTO": 9,
    "RAY": 6,
}


@dataclass
class FeeModel:
    """
    نموذج الرسوم لتقدير الربحية الواقعية لقرض وميضي على سولانا.

    - flash_loan_fee_bps: رسوم القرض الوميضي (نقاط أساس). أمثلة تقريبية:
      Kamino ~0 إلى عدة نقاط، Solend ~30 نقطة. عدّلها حسب البروتوكول.
    - base_tx_fee_sol: رسوم المعاملة الأساسية على سولانا (ثابتة تقريباً).
    - priority_fee_sol: رسوم الأولوية (تتغيّر حسب الازدحام والمنافسة).
    - jito_tip_sol: إكرامية Jito لإدراج الحزمة (اختياري، للمنافسة الحقيقية).
    """

    flash_loan_fee_bps: float = 30.0          # 0.30%
    base_tx_fee_sol: float = 0.000005         # 5000 lamports
    priority_fee_sol: float = 0.0005          # تقدير متحفّظ
    jito_tip_sol: float = 0.0                 # 0 افتراضياً في المحاكاة


@dataclass
class Settings:
    # واجهة Jupiter العامة (quote فقط — قراءة، لا تنفيذ)
    jupiter_base_url: str = "https://lite-api.jup.ag/swap/v1"

    # انزلاق السعر المسموح لكل اقتباس (نقاط أساس)
    slippage_bps: int = 50

    # العملة الأساسية التي نبدأ ونعود إليها في الحلقة
    base_token: str = "USDC"

    # مبلغ البدء (بوحدة العملة الأساسية، مقروء وليس ذرّي)
    base_amount: float = 10_000.0

    # سعر SOL بالدولار لتحويل الرسوم المقوّمة بـ SOL إلى قيمة بالعملة الأساسية.
    # يُحدّث تلقائياً من Jupiter عند التشغيل؛ هذه قيمة احتياطية فقط.
    sol_price_usd: float = 150.0

    # الحد الأدنى لصافي الربح (بالعملة الأساسية) حتى نعتبرها "فرصة"
    min_net_profit: float = 0.0

    fees: FeeModel = field(default_factory=FeeModel)

    # حلقات المراجحة الثلاثية المراد فحصها.
    # كل حلقة: قائمة عملات تبدأ وتنتهي بنفس base_token.
    # مثال USDC -> SOL -> BONK -> USDC
    cycles: list = field(default_factory=lambda: [
        ["USDC", "SOL", "USDC"],            # ذهاب وإياب بسيط (مرجع للتحقق)
        ["USDC", "SOL", "BONK", "USDC"],
        ["USDC", "SOL", "JUP", "USDC"],
        ["USDC", "SOL", "JTO", "USDC"],
        ["USDC", "SOL", "RAY", "USDC"],
        ["USDC", "USDT", "SOL", "USDC"],
    ])
