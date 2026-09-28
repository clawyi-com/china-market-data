<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 期货、期权、会员排名与贵金属

查询§13.1–§13.7时读取本文；七个CLI与Python导入见 [脚本入口](#commands)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

A 股之外的商品与股指衍生品：交易所官方日行情、商品期权、会员持仓排名，加新浪日 K 与实时行情、A50 期指与上海金交所现货。
实现集中在 [scripts/futures_data.py](../scripts/futures_data.py)，直接运行 CLI 无需读取实现；Python 组合调用先执行「Python 脚本路径初始化」。

| 函数 | 覆盖 | 说明 |
|---|---|---|
| `futures_daily(date, exchange)` | 上期所 SHFE / 上期能源 INE / 郑商所 CZCE / 中金所 CFFEX / 广期所 GFEX | 一行一个合约：开高低收、结算、昨结、成交量、持仓、成交额（万元） |
| `options_daily(date, exchange)` | 同上五所的商品期权 / 股指期权 | 行权价、看涨看跌、Delta、隐含波动率（逐合约或按系列） |
| `futures_position_rank(date, exchange, symbol=None)` | SHFE / INE / CZCE / CFFEX | 成交量 / 持买单 / 持卖单前 20 名会员 |
| `futures_realtime(symbols)` | 全部六家（含大商所） | 新浪实时价 / 盘口；`RB0` 主力连续、`CU2610` 具体合约 |
| `futures_kline(symbol, start, end)` | 全部六家（含大商所） | 新浪日 K：单个合约或主力连续的逐日开高低收、结算、成交量、持仓（V3.10.0） |
| `a50_futures()` | 富时中国 A50 | 新浪连续合约报价；价格变化不直接证明外资资金流或情绪 |
| `sge_spot(instrument)` | 上海黄金交易所 | 现货日线 2016-12 至今：`Au99.99` / `Au(T+D)` / `Ag(T+D)` … |

中金所期权分支不提供 Delta 或隐含波动率；随附实现将 `delta`、`iv_pct`、`series_iv_pct` 设为 None，不把缺失值补零或当成已计算结果。

**边界：** 大商所（DCE）官网有 JS 反爬（纯 HTTP 返回 412），官方日行情未接入；大商所品种（豆粕 M、铁矿 I…）的逐日 K 线用 `futures_kline`（新浪），实时用 `futures_realtime`。
各所实测可用起点：上期所 2002-01-07 起（2021 年及以前无成交额，`turnover_10k` 为 None）；上期能源 2018-03 开业；
郑商所 2015-09-21 起（更早是另一套格式，未接入）；中金所 2010-04-16 开业即有；广期所 2022-12 开业。
上期所的官方文件里混着上期能源的品种，已按能源中心同日文件剔除，SHFE 与 INE 两次调用不会重复；能源中心对照文件在它开始发布之后缺失时抛错，不会把能源品种算进上期所。
中金所持仓排名按各品种上市日确定当天应有的品种（IF 2010-04-16 … TL 2023-04-21），已上市品种缺文件抛错，不返回部分品种。
中金所日行情 / 期权的 CSV 里没有交易日列，用同目录 `index.xml` 每行的 tradingday 核对，并逐合约比对成交量 / 收盘价 / 持仓量，对不上抛错。
非交易日 / 未发布 / 该品种当时未上市抛 `ValueError`；交易所返回其他日期、表头改变、代码重复、文件不全抛 `RuntimeError`。
ETF 期权不在这里，见 Layer 9。

<a id="commands"></a>

### 13.1–13.7 脚本入口

依赖 requests、pandas，复用随附 `_market_common.py`：

```bash
python3 "<skill目录>/scripts/futures_data.py" daily 2026-09-18 SHFE --output futures.json
python3 "<skill目录>/scripts/futures_data.py" options 2026-09-18 CFFEX --output options.json
python3 "<skill目录>/scripts/futures_data.py" rank 2026-09-18 CZCE --symbol SR --output rank.json
python3 "<skill目录>/scripts/futures_data.py" realtime RB0 IF0 M0 --output quotes.json
python3 "<skill目录>/scripts/futures_data.py" kline M0 --start 2026-09-01 --end 2026-09-18 --output kline.json
python3 "<skill目录>/scripts/futures_data.py" a50 --output a50.json
python3 "<skill目录>/scripts/futures_data.py" spot --instrument 'Au(T+D)' --output spot.json
```

CLI 保存完整 DataFrame（列/dtype/索引/attrs/来源/全部行），终端仅预览前三行；现有输出路径不覆盖，异常非零退出且不保存。rank 的 symbol 只在完整源校验后过滤，筛选无匹配时仍按原行为保存空表。现货少量 OHLC 异常日期保留在 attrs，不因 JSON 输出丢失。CLI 不增加重试、缓存、交易日推断或自动降级。

<!-- v39-futures:start -->
```python
from futures_data import (
    futures_daily, options_daily, futures_position_rank, futures_realtime,
    futures_kline, a50_futures, sge_spot,
)
```
<!-- v39-futures:end -->

```python
cu = futures_daily("2026-09-18", "SHFE")
io_opt = options_daily("2026-09-18", "CFFEX")                  # 沪深300 股指期权 IO
rank = futures_position_rank("2026-09-18", "CFFEX", symbol="IF2610")
live = futures_realtime(["RB0", "M0", "IF0"])                   # M0 = 大商所豆粕主力
m_hist = futures_kline("M0", start="2026-01-01")                # 大商所豆粕主力连续的逐日 K 线
print(a50_futures()[["datetime", "last"]], sge_spot("Au99.99").tail(3))
```

---
