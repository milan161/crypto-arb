"""crypto-arb 仪表盘后端（FastAPI，端口见 .env 的 DASH_BACKEND_PORT，默认 8105）。

后台线程循环运行价差扫描（复用 core/day03_scanner 的逻辑），网页通过 /api/* 读取结果。
启动：双击程序根目录 start_dashboard.bat；或在程序根目录执行
    python src\\backend\\app.py
"""
import csv
import os
import sys
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

# 含 core/ 的目录（本地 = src/，ARM = 程序根），只用来放进 sys.path
SRC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_ROOT / "core"))

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

import day03_scanner as sc  # noqa: E402
from config import LOG_DIR  # noqa: E402

PORT = int(os.getenv("DASH_BACKEND_PORT", "8105"))   # 端口在 .env 配置，避开 ARB 下其他程序
HISTORY_LEN = 720    # 每个交易对保留最近 720 轮（约 3 小时）

LOCK = threading.Lock()
STOP = threading.Event()
STATE = {
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "rounds": 0,
    "last_round_at": None,
    "round_seconds": None,
    "fail_count": 0,
    "exchanges": {},
    "latest": [],
    "history": {s: deque(maxlen=HISTORY_LEN) for s in sc.SYMBOLS},
    "stats": {s: {"n": 0, "pos": 0, "max_gross": None} for s in sc.SYMBOLS},
    "log_path": "",
}


def scan_loop():
    exs = sc.init_exchanges()
    with LOCK:
        STATE["exchanges"] = {e: ("ok" if e in exs else "failed") for e in sc.EXCHANGES}
    if len(exs) < 2:
        print("可用交易所不足两家，扫描未启动。")
        return

    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"dashboard_{datetime.now():%Y%m%d}.csv"
    new_file = not log_path.exists()
    f = open(log_path, "a", newline="", encoding="utf-8-sig")
    writer = csv.writer(f)
    if new_file:
        writer.writerow(["time", "symbol", "buy", "sell", "ask", "bid",
                         "gross%", "fee_buy%", "fee_sell%", "slippage%", "cost%", "net%"])
    STATE["log_path"] = str(log_path)

    try:
        while not STOP.is_set():
            t0 = time.time()
            now = datetime.now().strftime("%H:%M:%S")
            rows, fails = [], 0
            for symbol in sc.SYMBOLS:
                quotes = sc.fetch_quotes(exs, symbol)
                listed = [e for e, ex in exs.items() if symbol in ex.markets]
                fails += len(set(listed) - set(quotes))
                if len(quotes) < 2:
                    continue
                best = sc.evaluate(exs, symbol, quotes)[0]
                rows.append(best)
                writer.writerow([now, symbol, best["buy"], best["sell"], best["ask"], best["bid"]]
                                + [round(best[k] * 100, 5) for k in
                                   ("gross", "fee_buy", "fee_sell", "slippage", "cost", "net")])
            f.flush()

            with LOCK:
                for r in rows:
                    s = r["symbol"]
                    STATE["history"][s].append(
                        {"t": now, "gross": r["gross"], "net": r["net"], "buy": r["buy"], "sell": r["sell"]})
                    st = STATE["stats"][s]
                    st["n"] += 1
                    st["pos"] += 1 if r["gross"] > 0 else 0
                    st["max_gross"] = r["gross"] if st["max_gross"] is None else max(st["max_gross"], r["gross"])
                STATE["latest"] = rows
                STATE["rounds"] += 1
                STATE["fail_count"] += fails
                STATE["last_round_at"] = now
                STATE["round_seconds"] = round(time.time() - t0, 1)

            STOP.wait(sc.INTERVAL_SEC)
    finally:
        f.close()


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=scan_loop, daemon=True).start()
    yield
    STOP.set()


app = FastAPI(title="crypto-arb dashboard", lifespan=lifespan)


@app.get("/api/status")
def status():
    with LOCK:
        return {
            "started_at": STATE["started_at"],
            "rounds": STATE["rounds"],
            "last_round_at": STATE["last_round_at"],
            "round_seconds": STATE["round_seconds"],
            "fail_count": STATE["fail_count"],
            "exchanges": STATE["exchanges"],
            "log_path": STATE["log_path"],
            "params": {
                "exchanges": sc.EXCHANGES,
                "symbols": sc.SYMBOLS,
                "slippage": sc.SLIPPAGE_BUFFER,
                "threshold": sc.THRESHOLD,
                "interval_sec": sc.INTERVAL_SEC,
            },
        }


@app.get("/api/spreads")
def spreads():
    with LOCK:
        out = []
        for r in STATE["latest"]:
            st = STATE["stats"][r["symbol"]]
            out.append({**r,
                        "max_gross": st["max_gross"],
                        "pos_ratio": st["pos"] / st["n"] if st["n"] else 0})
        return out


@app.get("/api/history")
def history(symbol: str = "BTC/USDT"):
    with LOCK:
        return list(STATE["history"].get(symbol, []))


if __name__ == "__main__":
    print(f"crypto-arb 后端启动：http://127.0.0.1:{PORT}  （关闭此窗口即停止）")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
