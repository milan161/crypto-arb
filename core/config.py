"""统一读取项目根目录的 .env 配置。换机器只需补 .env，不改代码。

路径约定（与 D:\\Study\\ARB\\README.md 一致）：
    SRC_ROOT  = 含 backend/ core/ frontend/ 的目录（本地 = src/，ARM = 程序根）
    PROJ_ROOT = 含 data/ logs/ docs/ .env 的目录（本地 = src 的父目录）
data / logs 一律用 PROJ_ROOT 拼，不要写死成 src/data。
"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv

_CORE_DIR = Path(__file__).resolve().parent
SRC_ROOT = _CORE_DIR.parent
PROJ_ROOT = SRC_ROOT.parent if SRC_ROOT.name == "src" else SRC_ROOT
ROOT = PROJ_ROOT  # 兼容旧名
DATA_DIR = PROJ_ROOT / "data"
LOG_DIR = PROJ_ROOT / "logs"
load_dotenv(PROJ_ROOT / ".env")


def get(name: str, required: bool = False):
    v = os.getenv(name)
    if required and not v:
        raise RuntimeError(f"缺少环境变量 {name}，请在 .env 中配置")
    return v or None


def make_exchange(exchange_id: str, sandbox: bool = False, timeout_ms: int = 30000, **extra):
    """创建 ccxt 交易所实例：自动限频、30 秒超时、自动带上 .env 里的代理。"""
    import ccxt

    params = {"enableRateLimit": True, "timeout": timeout_ms, **extra}
    proxy = get("HTTPS_PROXY")
    if proxy:
        params["httpsProxy"] = proxy
    ex = getattr(ccxt, exchange_id)(params)
    if sandbox:
        ex.set_sandbox_mode(True)
    return ex


def with_retry(func, *args, tries: int = 3, wait: float = 2.0, label: str = "", **kwargs):
    """网络类错误（超时、断线）自动重试；其他错误（如 403 地区限制）直接抛出，重试没用。"""
    import ccxt

    for i in range(1, tries + 1):
        try:
            return func(*args, **kwargs)
        except ccxt.NetworkError as e:
            # 注意：ccxt 把部分 403 归为 RateLimitExceeded（NetworkError 子类），403 重试也无用
            if "403" in str(e) or i == tries:
                raise
            print(f"  [重试 {i}/{tries - 1}] {label} {type(e).__name__}，{wait:.0f} 秒后再试")
            time.sleep(wait)
            wait *= 2
