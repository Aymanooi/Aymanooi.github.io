import time
import sys
from datetime import datetime
from colorama import init, Fore, Style

from config import (
    API_KEY, API_SECRET, PASSPHRASE, IS_DEMO,
    LEVERAGE, CAPITAL_RATIO, STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    EMA_FAST, EMA_SLOW, RSI_PERIOD, RSI_BUY_MAX, RSI_SELL_MIN,
    TIMEFRAME, SCAN_INTERVAL, TOP_PAIRS_COUNT, MAX_POSITIONS
)
from okx_client import OKXClient
from strategy import get_signal

init(autoreset=True)


def log(msg, color=Fore.WHITE):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.CYAN}[{ts}]{Style.RESET_ALL} {color}{msg}{Style.RESET_ALL}")


def print_header():
    mode = "DEMO 🧪" if IS_DEMO == "1" else "LIVE 💰"
    print(f"""
{Fore.YELLOW}{'='*55}
  OKX TRADING BOT  |  {mode}
  Leverage: {LEVERAGE}x | SL: {STOP_LOSS_PCT*100}% | TP: {TAKE_PROFIT_PCT*100}%
  Strategy: EMA({EMA_FAST}/{EMA_SLOW}) + RSI({RSI_PERIOD})
{'='*55}{Style.RESET_ALL}
""")


def run():
    if not API_KEY or not API_SECRET or not PASSPHRASE:
        print(f"{Fore.RED}خطأ: يرجى إضافة API Key في ملف config.py{Style.RESET_ALL}")
        sys.exit(1)

    client = OKXClient(API_KEY, API_SECRET, PASSPHRASE, IS_DEMO)
    print_header()
    log("البوت يعمل الآن...", Fore.GREEN)

    scan_count = 0
    while True:
        try:
            scan_count += 1
            log(f"فحص #{scan_count} | جارٍ تحليل السوق...", Fore.YELLOW)

            # Check current positions
            positions = client.get_all_positions()
            active_pairs = {p["instId"] for p in positions}

            if len(active_pairs) >= MAX_POSITIONS:
                log(f"صفقة مفتوحة: {', '.join(active_pairs)}", Fore.BLUE)
                time.sleep(SCAN_INTERVAL)
                continue

            # Get balance
            balance = client.get_balance()
            log(f"الرصيد المتاح: {balance:.4f} USDT", Fore.GREEN)

            if balance < 1:
                log("الرصيد أقل من 1 USDT، انتظار...", Fore.RED)
                time.sleep(SCAN_INTERVAL)
                continue

            # Get top pairs
            pairs = client.get_top_pairs(TOP_PAIRS_COUNT)
            if not pairs:
                log("فشل في جلب الأزواج، إعادة المحاولة...", Fore.RED)
                time.sleep(SCAN_INTERVAL)
                continue

            log(f"تحليل {len(pairs)} زوج...", Fore.CYAN)

            signal_found = False
            for inst_id in pairs:
                if inst_id in active_pairs:
                    continue

                candles = client.get_candles(inst_id, bar=TIMEFRAME, limit=60)
                if not candles:
                    continue

                signal = get_signal(
                    candles,
                    ema_fast=EMA_FAST,
                    ema_slow=EMA_SLOW,
                    rsi_period=RSI_PERIOD,
                    rsi_buy_max=RSI_BUY_MAX,
                    rsi_sell_min=RSI_SELL_MIN
                )

                if not signal:
                    continue

                # Get current price
                ticker = client.get_ticker(inst_id)
                if not ticker:
                    continue
                price = float(ticker["last"])

                # Set leverage
                client.set_leverage(inst_id, LEVERAGE)

                # Calculate contract size
                sz = client.calculate_contracts(
                    inst_id, balance, price, LEVERAGE, CAPITAL_RATIO
                )
                if sz <= 0:
                    log(f"{inst_id}: الرصيد غير كافٍ للدخول", Fore.RED)
                    continue

                # Place order
                result = client.place_order(
                    inst_id, signal, sz, price, STOP_LOSS_PCT, TAKE_PROFIT_PCT
                )

                if result["code"] == "0":
                    direction = "شراء 📈" if signal == "buy" else "بيع 📉"
                    sl = price * (1 - STOP_LOSS_PCT) if signal == "buy" else price * (1 + STOP_LOSS_PCT)
                    tp = price * (1 + TAKE_PROFIT_PCT) if signal == "buy" else price * (1 - TAKE_PROFIT_PCT)
                    log(f"✅ صفقة {direction} | {inst_id}", Fore.GREEN)
                    log(f"   السعر: {price} | وقف: {sl:.4f} | هدف: {tp:.4f}", Fore.GREEN)
                    log(f"   العقود: {sz} | رافعة: {LEVERAGE}x", Fore.GREEN)
                    signal_found = True
                    break
                else:
                    log(f"فشل الأمر على {inst_id}: {result.get('msg', '')}", Fore.RED)

            if not signal_found:
                log("لا توجد إشارات حالياً، انتظار...", Fore.YELLOW)

            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            log("إيقاف البوت...", Fore.RED)
            break
        except Exception as e:
            log(f"خطأ: {e}", Fore.RED)
            time.sleep(30)


if __name__ == "__main__":
    run()
