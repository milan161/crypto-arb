# crypto-arb · 币圈中性策略学习项目

和群里的小伙伴们一起，用 Python 一步步写币圈套利程序。节奏不赶，每一步都用自己的数据验证。

研究方向是三类中性收益：**资金费率套利**、**Pendle Boros 费率锁定**、**LP + 对冲**。第一周先从最基础的跨所现货价差入手，把行情接入和成本计算打牢。

> 本项目仅用于学习交流，不构成投资建议。

## 学习笔记

| 篇目 | 内容 |
|---|---|
| [00 环境搭建](docs/00_环境搭建.md) | venv、目录约定、代理、密钥安全 |
| [01 价差扫描器](docs/01_价差扫描器.md) | 净价差公式、手算核对、403 与超时排查 |
| [02 第一周验收与仪表盘](docs/02_第一周验收与仪表盘.md) | 30 分钟实测数据、网页仪表盘、目录整理 |
| [03 订单簿深度与滑点](docs/03_订单簿深度与滑点.md) | 第二周：用真实订单簿检验 0.05% 的滑点缓冲，一笔账 |

## 第一周的结论

okx / gate / bitget 三家，BTC、ETH、SOL、DOGE、XRP 五个币，连续 30 分钟、580 个数据点：

- 平均毛价差 0.007% ～ 0.018%，最大 0.115%
- 两边手续费 + 滑点缓冲约 0.40%
- **净价差全部为负**：主流币跨所现货搬砖不可行

## 快速开始

本仓库是程序根目录下的 `src/`。推荐的本地结构：

```
crypto/              ← 程序根，自己建
├── src/             ← 把本仓库克隆到这里
├── .venv/
├── .env             ← 从 src/.env.example 复制过来填写
├── data/
└── logs/
```

```powershell
mkdir crypto; cd crypto
git clone https://github.com/milan161/crypto-arb.git src
python -m venv .venv
.venv\Scripts\activate
pip install -r src\requirements.txt
copy src\.env.example .env        # 打开 .env，填上自己的代理地址
python src\core\day01_ticker.py okx BTC/USDT
```

看到 `okx  BTC/USDT  last=...  bid=...  ask=...` 就说明环境通了。

扫描器：

```powershell
python src\core\day03_scanner.py --once          # 扫一轮
python src\core\day03_scanner.py --minutes 30    # 连续 30 分钟
```

网页仪表盘（需要 Node.js LTS）：

```powershell
cd src\frontend
npm install
cd ..\..
python src\backend\app.py            # 窗口一：后端
cd src\frontend; npm run dev         # 窗口二：前端
```

浏览器打开 http://localhost:5185 。端口被占用时，改 `.env` 里的 `DASH_BACKEND_PORT` / `DASH_FRONTEND_PORT`。

## 目录

```
src/
├── core/            config.py、day01~03 扫描器、day04 订单簿深度
├── backend/app.py   仪表盘后端（FastAPI）
├── frontend/        仪表盘前端（Vue 3 + Naive UI + ECharts）
├── docs/            学习笔记
├── requirements.txt
└── .env.example
```

## 几条纪律

1. API Key 永不开提币权限，密钥只放 `.env`，绝不提交。
2. 下单只在测试网做，实盘只用亏了也不心疼的小钱。
3. 只晒收益、不讲成本和风险的内容，一律当广告看。

每周五在群里发三句话：这周完成了什么、卡在哪一步、代码能不能复现。卡住了贴报错原文，大家一起看。
