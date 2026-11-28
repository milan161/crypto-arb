"""阶段2 第1步：订单簿深度 —— 一笔单子真正的成交均价是多少？

扫描器看的是第一档 bid / ask，但第一档往往只挂了很少的量。
下单量一大，就会吃到第二档、第三档，成交均价比第一档更差，差的这部分就是"滑点"。

用法（程序根目录执行）:
    python src\\core\\day04_depth.py                        # 默认 okx、gate、bitget，BTC 等五个币
    python src\\core\\day04_depth.py --notional 10000       # 每笔 10000 USDT
    python src\\core\\day04_depth.py --symbols BTC/USDT SOL/USDT --notional 2000 --levels 20

输出：对每家交易所、每个币，模拟"买入 / 卖出 notional 这么多 USDT"，算出
    成交均价、相对第一档的滑点（%）、吃到了几档、深度是否够。
并保存到 logs\\depth_日期.csv。
"""
import argparse
import csv
from datetime import datetime

import ccxt

from config import LOG_DIR, make_exchange, with_retry

# ===== 可调参数 =====
EXCHANGES = ["okx", "gate", "bitget"]
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT"]
NOTIONALS = [1000, 10000]   # 模拟的单笔金额（USDT），可用 --notional 覆盖
LEVELS = 20                 # 取订单簿前多少档
# ====================


def walk_book(levels, notional):
    """沿着订单簿一档一档吃，直到花完 notional（USDT）。

    levels: [[价格, 数量], ...]，买入时传 asks（从低到高），卖出时传 bids（从高到低）
    返回: (成交均价, 吃到的档数, 是否吃满, 实际成交金额)
    """
    remaining = notional
    spent = 0.0       # 已经成交的金额（USDT）
    qty = 0.0         # 已经成交的币数量
    used = 0
    for lv in levels:
        # 有的交易所（如 OKX）每档除了价格、数量还带额外字段，只取前两个
        price, amount = lv[0], lv[1]
        level_value = price * amount
        take_value = min(remaining, level_value)
        qty += take_value / price
        spent += take_value
        remaining -= take_value
        used += 1
        if remaining <= 1e-9:
            break
    if qty == 0:
        return None, 0, False, 0.0
    return spent / qty, used, remaining <= 1e-9, spent


def slippage_pct(avg_price, top_price, side):
    """相对第一档的不利偏离，正数 = 吃亏。买入均价越高越亏，卖出均价越低越亏。"""
    if side == "buy":
        return (avg_price - top_price) / top_price * 100
    return (top_price - avg_price) / top_price * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", default=SYMBOLS)
    ap.add_argument("--notional", nargs="+", type=float, default=NOTIONALS, help="单笔金额 USDT，可给多个")
    ap.add_argument("--levels", type=int, default=LEVELS)
    args = ap.parse_args()

    exs = {}
    for ex_id in EXCHANGES:
        try:
            ex = make_exchange(ex_id)
            with_retry(ex.load_markets, label=f"{ex_id} load_markets")
            exs[ex_id] = ex
            print(f"[初始化] {ex_id:6} OK")
        except ccxt.BaseError as e:
            print(f"[初始化] {ex_id:6} 失败，跳过：{type(e).__name__}")
    if not exs:
        raise SystemExit("没有可用的交易所。")

    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"depth_{datetime.now():%Y%m%d}.csv"
    new_file = not log_path.exists()
    f = open(log_path, "a", newline="", encoding="utf-8-sig")
    w = csv.writer(f)
    if new_file:
        w.writerow(["time", "exchange", "symbol", "side", "notional", "top_price",
                    "avg_price", "slippage%", "levels_used", "enough"])

    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n=== 订单簿深度 {now}（取前 {args.levels} 档）===")
    print(f"{'交易所':8}{'交易对':11}{'方向':5}{'金额USDT':>10}{'第一档价':>13}{'成交均价':>13}{'滑点':>9}{'吃档数':>7}  深度")

    for symbol in args.symbols:
        for ex_id, ex in exs.items():
            if symbol not in ex.markets:
                continue
            try:
                ob = with_retry(ex.fetch_order_book, symbol, args.levels, tries=2, label=f"{ex_id} {symbol}")
            except ccxt.BaseError as e:
                print(f"{ex_id:8}{symbol:11}取订单簿失败：{type(e).__name__}")
                continue
            for notional in args.notional:
                for side, book in (("buy", ob["asks"]), ("sell", ob["bids"])):
                    if not book:
                        continue
                    avg, used, enough, spent = walk_book(book, notional)
                    if avg is None:
                        continue
                    top = book[0][0]
                    slip = slippage_pct(avg, top, side)
                    flag = "够" if enough else f"不够(只成交 {spent:.0f})"
                    print(f"{ex_id:8}{symbol:11}{side:5}{notional:>10.0f}{top:>13.6g}{avg:>13.6g}"
                          f"{slip:>8.4f}%{used:>7}  {flag}")
                    w.writerow([now, ex_id, symbol, side, notional, top,
                                round(avg, 8), round(slip, 5), used, enough])
    f.close()
    print(f"\n明细已写入 {log_path}")
    print("提示：计划里的滑点缓冲是 0.05%。看看上面哪些行的滑点已经超过它？")


if __name__ == "__main__":
    main()
