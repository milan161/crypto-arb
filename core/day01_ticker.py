"""阶段0 完成标准：一条命令拉到 BTC/USDT ticker。

用法（在项目根目录执行）: python src\\core\\day01_ticker.py [交易所] [交易对]
例: python src\\core\\day01_ticker.py okx BTC/USDT
"""
import sys

from config import make_exchange, with_retry

exchange_id = sys.argv[1] if len(sys.argv) > 1 else "okx"
symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC/USDT"

ex = make_exchange(exchange_id)
with_retry(ex.load_markets, label=f"{exchange_id} load_markets")
t = with_retry(ex.fetch_ticker, symbol, label=exchange_id)  # 公开行情接口，不需要密钥
print(f"{exchange_id:8} {symbol}  last={t['last']}  bid={t['bid']}  ask={t['ask']}")
