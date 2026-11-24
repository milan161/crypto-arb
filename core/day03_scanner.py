"""阶段1 第4步：多交易所、多交易对的净价差扫描器（同步版，只看不下单）。

用法（项目根目录执行）:
    python src\\core\\day03_scanner.py
    python src\\core\\day03_scanner.py --once            # 只扫一轮，便于手算核对
    python src\\core\\day03_scanner.py --minutes 30      # 连续运行 30 分钟（阶段1完成标准）

净价差口径（与计划书一致）:
    净价差 = (卖方 bid - 买方 ask) / 买方 ask - 买方 taker - 卖方 taker - 滑点缓冲
"""
import argparse
import csv
import time
from datetime import datetime
from itertools import permutations

import ccxt

from config import LOG_DIR, make_exchange, with_retry

# ===== 可调参数：改这里，不改逻辑 =====
EXCHANGES = ["okx", "gate", "bitget"]   # 美国节点下 bybit 会 403；用日本节点可加回 "bybit"
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT"]
SLIPPAGE_BUFFER = 0.0005   # 滑点缓冲 0.05%
THRESHOLD = 0.0            # 净价差 > 阈值 才标记为机会
INTERVAL_SEC = 10          # 每轮间隔
# ====================================


def init_exchanges():
    """创建实例并 load_markets 一次；失败的交易所跳过，不影响其他。"""
    exs = {}
    for ex_id in EXCHANGES:
        try:
            ex = make_exchange(ex_id)
            with_retry(ex.load_markets, label=f"{ex_id} load_markets")
            exs[ex_id] = ex
            print(f"[初始化] {ex_id:6} OK，市场数 {len(ex.markets)}")
        except ccxt.BaseError as e:
            print(f"[初始化] {ex_id:6} 失败，本次跳过：{type(e).__name__}: {str(e)[:100]}")
    return exs


def taker_fee(ex, symbol):
    """从 ccxt 市场信息读 taker 费率（默认档位，未计 VIP/平台币折扣）。"""
    return ex.markets[symbol].get("taker") or 0.001


def fetch_quotes(exs, symbol):
    quotes = {}
    for ex_id, ex in exs.items():
        if symbol not in ex.markets:
            continue
        try:
            t = with_retry(ex.fetch_ticker, symbol, tries=2, label=f"{ex_id} {symbol}")
            if t["bid"] and t["ask"]:
                quotes[ex_id] = t
        except ccxt.BaseError as e:
            print(f"  {ex_id} {symbol} 取价失败：{type(e).__name__}")
    return quotes


def evaluate(exs, symbol, quotes):
    """枚举所有 买所→卖所 组合，返回按净价差排序的结果。"""
    rows = []
    for buy, sell in permutations(quotes, 2):
        ask = quotes[buy]["ask"]
        bid = quotes[sell]["bid"]
        gross = (bid - ask) / ask
        fee_b = taker_fee(exs[buy], symbol)
        fee_s = taker_fee(exs[sell], symbol)
        cost = fee_b + fee_s + SLIPPAGE_BUFFER
        rows.append({
            "symbol": symbol, "buy": buy, "sell": sell, "ask": ask, "bid": bid,
            "gross": gross, "fee_buy": fee_b, "fee_sell": fee_s,
            "slippage": SLIPPAGE_BUFFER, "cost": cost, "net": gross - cost,
        })
    return sorted(rows, key=lambda r: r["net"], reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--minutes", type=float, default=0, help="运行时长，0 表示一直运行")
    args = ap.parse_args()

    exs = init_exchanges()
    if len(exs) < 2:
        raise SystemExit("可用交易所不足两家，无法比价。")

    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"scanner_{datetime.now():%Y%m%d}.csv"
    new_file = not log_path.exists()
    f = open(log_path, "a", newline="", encoding="utf-8-sig")
    writer = csv.writer(f)
    if new_file:
        writer.writerow(["time", "symbol", "buy", "sell", "ask", "bid",
                         "gross%", "fee_buy%", "fee_sell%", "slippage%", "cost%", "net%"])

    end = time.time() + args.minutes * 60 if args.minutes else None
    rounds = 0
    try:
        while True:
            rounds += 1
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n=== 第 {rounds} 轮 {now} ===")
            print(f"{'交易对':10}{'买入所':7}{'卖出所':7}{'毛价差':>10}{'成本':>9}{'净价差':>10}")
            for symbol in SYMBOLS:
                quotes = fetch_quotes(exs, symbol)
                if len(quotes) < 2:
                    print(f"{symbol:10}可用报价不足两家，跳过")
                    continue
                best = evaluate(exs, symbol, quotes)[0]  # 每个交易对只显示最优方向
                flag = "  ★机会" if best["net"] > THRESHOLD else ""
                print(f"{symbol:10}{best['buy']:7}{best['sell']:7}"
                      f"{best['gross']*100:>9.4f}%{best['cost']*100:>8.3f}%"
                      f"{best['net']*100:>9.4f}%{flag}")
                writer.writerow([now, symbol, best["buy"], best["sell"], best["ask"], best["bid"]]
                                + [round(best[k] * 100, 5) for k in
                                   ("gross", "fee_buy", "fee_sell", "slippage", "cost", "net")])
            f.flush()
            if args.once or (end and time.time() >= end):
                break
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        print("\n手动停止。")
    finally:
        f.close()
        print(f"共运行 {rounds} 轮，明细已写入 {log_path}")


if __name__ == "__main__":
    main()
