"""阶段1 第2步：双所比价，计算毛价差（尚未扣手续费与滑点）。

用法: python src\\core\\day02_spread.py [交易所A] [交易所B] [交易对]
例:   python src\\core\\day02_spread.py okx gate BTC/USDT

口径：在 ask 低的一边买入，在 bid 高的一边卖出
      毛价差 = (卖方 bid - 买方 ask) / 买方 ask
"""
import sys

import ccxt

from config import make_exchange

a_id = sys.argv[1] if len(sys.argv) > 1 else "okx"
b_id = sys.argv[2] if len(sys.argv) > 2 else "gate"
symbol = sys.argv[3] if len(sys.argv) > 3 else "BTC/USDT"

tickers = {}
for ex_id in (a_id, b_id):
    try:
        t = make_exchange(ex_id).fetch_ticker(symbol)
    except ccxt.BaseError as e:
        # 单家失败不让程序崩溃，只打印一行原因（403 多为地区限制，换代理节点或换交易所）
        print(f"{ex_id:8} 获取失败：{type(e).__name__}: {str(e)[:120]}")
        continue
    tickers[ex_id] = t
    print(f"{ex_id:8} bid={t['bid']:<12} ask={t['ask']}")

if len(tickers) < 2:
    sys.exit("有交易所没取到行情，无法比价。")

# 两个方向都算：A买B卖、B买A卖
for buy, sell in ((a_id, b_id), (b_id, a_id)):
    ask = tickers[buy]["ask"]
    bid = tickers[sell]["bid"]
    gross = (bid - ask) / ask * 100
    print(f"{buy} 买 → {sell} 卖：毛价差 {gross:+.4f}%")
