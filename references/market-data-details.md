<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 盘后包、逐笔、均线与复权

按需读取：[§1.3 盘后包](#daily-package)、[§1.4 分笔](#ticks)、[§1.5 百度日线](#baidu)、[§1.6 复权](#adjust)、[§1.7 mootdx 留档](#mootdx)。其他章节编号及 Python 路径初始化见 [SKILL.md](../SKILL.md)。`<skill目录>` 指技能根目录，不是 references 目录。

<a id="daily-package"></a>

### 1.3 通达信官网盘后包 — 某交易日全市场日线含成交额（V3.9.0 新增 · #52）

通达信官网每天发布的增量数据包（HTTP 下载约 2.7MB），一次拿到**沪深北全部证券**当日的昨收、开高低收、成交量（股）、
成交额（元）。它走 HTTP，和 §1.7 失效的 TCP 行情命令是两条路。适合收盘后全市场截面筛选、每日落库。
二进制布局参考 [jing2uo/tdx2db](https://github.com/jing2uo/tdx2db)（MIT），已与腾讯收盘价对拍。
非交易日、或当天包还没发布（通常收盘后数小时）抛 `ValueError`，不返回空表。

实现位于 [scripts/tdx_daily_package.py](../scripts/tdx_daily_package.py)，需要 requests、pandas；直接执行，无需读取源码：

```bash
python3 "<skill目录>/scripts/tdx_daily_package.py" 2026-09-18
python3 "<skill目录>/scripts/tdx_daily_package.py" 20260918 --output daily-market.json
```

CLI 始终保存完整 JSON：未指定 `--output` 时在当前工作目录创建 `tdx-daily-*.json`；指定路径的父目录须存在，不覆盖旧文件。stdout 只输出绝对路径、总行数和前三条预览（`preview_only=true`），全市场分析须读取完整文件。错误写 stderr 并返回非零退出码。

显式输出优先原子发布；文件系统不支持硬链接时改用独占创建并复制，仍不覆盖旧文件，但写入期间目标可能已可见。请等 CLI 成功退出后读取；捕获到写入错误会清理本次创建的半成品，进程被强制终止时可能留下未完成文件。

文件包含 `columns`、`dtypes`、`index`（RangeIndex 名称、起止、步长）、`attrs` 和完整 `data`；字段为 `date / market / code / name / prev_close / open / high / low / close / volume / amount / source / source_url / fetched_at`。个股成交量为**股**、成交额为**元**；指数等特殊代码的成交量保留通达信原值。价格保留 4 位小数，成交额保留 2 位。

历史包实测 2022-01-04、2023-01-03 可取，2021-01-04 已 404，并非逐日覆盖保证。2022-05-06 之前可只有沪深；从该日开始缺北交所文件会报错。仍逐市场校验有价记录下限（沪 10000、深 3000、北 50），不将残缺市场当作全市场返回。代码/序号重复、文件缺失或截断、坏名称、非有限数值等保持原校验；收盘价 ≤0 的无价记录仍跳过。404 抛 `ValueError`，坏包或网络错误按原规则报错，不新增重试或降级。

Python 组合调用：先在同一进程执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，导入后仍返回原生 DataFrame：

<!-- v39-tdx-package:start -->
```python
from tdx_daily_package import tdx_daily_package
```
<!-- v39-tdx-package:end -->

```python
snap = tdx_daily_package("2026-09-18")
print(len(snap), snap[snap.code == "600519"][["close", "volume", "amount"]])
```

<a id="ticks"></a>

### 1.4 腾讯逐笔成交 — 当日分笔明细（V3.10.0 新增 · 替代 §1.7 mootdx `transaction`）

§1.7 mootdx `transaction()` 2026-09 起返回空（#52）后的逐笔来源：腾讯行情页「成交明细」接口，一页 70 笔，逐页翻到空页为止，
全天 60–70 页、约 10–20 秒。

- **只有最近一个交易日**，没有历史；覆盖沪深个股（含创业板、科创板）与 ETF。北交所、指数没有，直接抛 `ValueError`。
- 是约 3 秒一笔的**分笔**（同一时刻撮合的多笔合并成一笔），不是交易所 Level-2 逐笔委托 / 逐笔成交。
  09:25 那一笔就是开盘集合竞价的撮合结果。
- `volume` 单位「手」（科创板也是手）、`amount` 单位元；`side`：B = 主动买、S = 主动卖、M = 中性（集合竞价、盘后定价多为 M）。
- 收盘后 15:05–15:30 的盘后定价（固定价格）成交也在结果里（`time` 晚于 15:00:59 的行）；实测沪深主板、创业板、科创板、ETF 都有，
  不计入腾讯行情的当日成交额。
- **完整性核对：** 收盘后调用时，连续竞价段（≤ 15:00:59）的成交额合计要与腾讯行情快照的当日成交额相符，差超过 `快照成交额 × 0.1% + 1000 元` 抛 `RuntimeError`
  （2026-09-22 实测 000001 / 600519 / 300750 / 688981 / 159915 / 000002 / 603286 相差 0–285 元）。
  判定依据是两次快照成交额是否相同：相同时核对（也可能是午休或停牌），不同时不做金额核对；日期跨日仍报错。
- 腾讯偶尔缓存了盘后某一页的旧版本，会缺几笔盘后成交（实测 300750 缺 6 笔、159915 缺 7 笔，都在 15:14 以后），
  缺的序号记在 `frame.attrs["missing_seq"]`；连续竞价段缺号直接抛 `RuntimeError`，稍后重试。
- 开盘前（9:25 撮合前）调用可能拿不到上一交易日的逐笔。
- 数据校验：逐笔与快照时刻必须在 00:00:00–23:59:59 内；逐笔价格、成交量、成交额及快照成交额不能为负，否则抛 `RuntimeError`，CLI 失败且不保存文件。`change` 仍允许负数；不按交易时段过滤记录，保留盘后成交。此为迁移后的错误校验修复。

实现位于 [scripts/tencent_ticks.py](../scripts/tencent_ticks.py)，需要 requests、pandas；直接运行，无需读取源码：

```bash
python3 "<skill目录>/scripts/tencent_ticks.py" 000001
python3 "<skill目录>/scripts/tencent_ticks.py" 510300 --output ticks.json
```

CLI 始终将完整 JSON 保存到新文件：省略 `--output` 时在当前工作目录创建 `tencent-ticks-*.json`，指定路径时父目录须存在、不覆盖旧文件。stdout 只给绝对路径、总行数与三条预览（`preview_only=true`）；分析全部成交须读取文件。错误写 stderr，退出码非零。

文件包含 `columns / dtypes / index / attrs / data`，保留原始列顺序、RangeIndex、数据及 `attrs.missing_seq`，不能忽略该属性而把盘后缺笔当作完整数据。数据列为 `date / code / time / seq / price / change / volume / amount / side / source / source_url / fetched_at`。Python 导入仍返回原生 DataFrame。

显式输出优先原子发布；不支持硬链接时独占创建并复制，不覆盖已有路径，但写入期间目标可能可见。等待 CLI 成功退出后再读取；可捕获写入错误会清理半成品，强制终止可能留下未完成文件。

保留逐页请求顺序、每个非空页后等待 0.1 秒、最多 300 页及两次行情快照核对，不新增重试、过滤或截断。代码支持原有前缀/后缀与聚宽写法；裸 `000001` 为平安银行，指数、北交所按原规则拒绝。CLI 不提供历史日期参数。

Python 组合调用：先在同一进程执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，然后导入：

<!-- v310-tencent-ticks:start -->
```python
from tencent_ticks import tencent_ticks
```
<!-- v310-tencent-ticks:end -->

```python
ticks = tencent_ticks("000001")                     # 平安银行最近一个交易日全部分笔
auction = ticks[ticks.time < "09:30:00"]            # 开盘集合竞价撮合那一笔（科创板在 09:25:0x）
buy = ticks.loc[ticks.side == "B", "amount"].sum()  # 主动买入额
etf = tencent_ticks("510300")                       # ETF 同样可用
```

<a id="baidu"></a>

### 1.5 百度股市通 K线 — 带MA5/MA10/MA20（V3.0 新增）

**核心价值：** 返回时自带均线数据，无需本地计算。

实现位于 [scripts/baidu_kline_with_ma.py](../scripts/baidu_kline_with_ma.py)，仅需 requests（不依赖 pandas），无需读取源码：

```bash
python3 "<skill目录>/scripts/baidu_kline_with_ma.py" 600519 --output baidu-bars.json
```

CLI 始终保存完整 JSON；省略 `--output` 时在当前工作目录创建 `baidu-kline-*.json`。指定路径的父目录须存在，不覆盖已有文件。stdout 只给绝对路径、原始 rows 项数与前三项预览（`preview_only=true`），完整数据须读取文件。输出发布沿用 §1.3 的独占创建兼容规则，等待 CLI 成功后再读取；错误写 stderr，退出码非零。

正常响应返回 `{"keys": ..., "rows": [...]}`：keys 必须为非空字段名列表，顺序及 MA5/MA10/MA20 等字段原样保留；rows 仅按分号拆分，内部字段不解析、不转数值、不排序，保留夹杂的空行和尾部分号产生的空字符串。至少有一条非空记录才可成功；`row_count` 仍是原始数组长度，不代表有效 K 线根数，也不保证源数据完整。

固定 `ktype="1"` 日线，代码原样传递，不新增前后缀归一化、指数/ETF 兼容承诺或分页。`--start-time` 对应原 `start_time` 参数，省略为空，传值不做日期转换；不假定它是标准日期格式。保持原请求头和 10 秒超时，无新增重试。

已修复旧版“错误响应变空结果”的问题：非 2xx 抛 `requests.HTTPError`，保留 HTTP 状态及可用的风控原因；顶层/嵌套业务错误、验证码要求、非 JSON 或异常数据结构抛 `RuntimeError`。结构完整但所有行均为空白时抛 `ValueError`。CLI 均退出非零、不创建结果文件，不把 `ResultCode=0` 单独当作成功依据。收到 `hit risk` 时应报告数据源拒绝并按备用源路由处理，不能当作零条正常行情。

Python 组合调用：先执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，然后导入；原示例不变：

```python
from baidu_kline_with_ma import baidu_kline_with_ma

# 用法
data = baidu_kline_with_ma("600519")
print("字段:", data["keys"][:10])
print("最近5根K线:", data["rows"][-5:])
# keys 包含: time, open, close, high, low, volume, amount, ma5avgprice, ma10avgprice, ma20avgprice 等
```

<a id="adjust"></a>

### 1.6 新浪复权因子 — qfq / hfq（V3.7.0 新增）

**核心价值：** §1.7 `tdx_client().bars()`、§1.2 `tencent_kline(adjust='')`、§1.3 `tdx_daily_package()` 返回的是**不复权**数据，跨除权日直接比价必然出错。
本端点给出复权因子序列，一次 HTTP、约 1.8KB、零鉴权。

实现位于 [scripts/sina_adjust.py](../scripts/sina_adjust.py)，取因子和 list 模式需要 requests，DataFrame 模式另需 pandas。无需读取脚本源码：

```bash
python3 "<skill目录>/scripts/sina_adjust.py" factors 600519 --kind qfq --output factors-qfq.json
python3 "<skill目录>/scripts/sina_adjust.py" apply --bars raw-bars.json --factors factors-qfq.json --kind qfq --output adjusted.json
```

`raw-bars.json` 为不复权 K 线对象列表，例如 `[{"date":"2015-01-05","close":202.52}]`；因子文件为 `[{"date":"1900-01-01","factor":1.0}, ...]`。可直接使用 `factors` 命令生成的完整文件。`--kind` 默认 qfq，必须与因子文件种类一致；hfq 取数和计算均指定 `--kind hfq`。因子本身不携带种类，不会自动推断。`--price-key` 可重复指定，替换默认 open/high/low/close 字段。

CLI 始终全量落盘，stdout 只给路径、行数、种类及三条预览；省略 `--output` 时在当前目录生成 `sina-adjust-*.json`。指定输出父目录须存在，不覆盖旧文件；失败退出非零。保存优先原子硬链接，不支持时独占创建并复制，需等待成功退出再读；强制终止可能留下半成品。非有限数值使用保留单键标记 `{"$float":"NaN"}` / `Infinity` / `-Infinity`，apply 读取时还原；这不代表这些因子有效，原函数未新增数值校验。

CLI 的 apply 输入为 JSON 对象列表，不接受其他行情脚本带 columns/attrs/data 的完整文件封装；请取其 `data` 列表，或通过 Python API 传入原生 DataFrame。Python 返回类型与输入一致；支持 `date`/`datetime`，按日期排序、保留非 RangeIndex 及名称，沿用旧版不保留 DataFrame attrs 的行为。默认只调整价格，不修改量额。空因子抛 ValueError，早于最早因子或因子为零抛 RuntimeError；不能把未复权结果继续当作已复权值使用。

先在同一进程执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，然后：

```python
from sina_adjust import sina_adjust_factor, apply_adjust

# 用法
qfq = sina_adjust_factor("600519", "qfq")
hfq = sina_adjust_factor("600519", "hfq")
print(len(qfq), "条 | 最新", qfq[0], "| 最早", qfq[-1])
# 实测 2026-08-19：33 条
#   qfq 最新 {'date': '2026-06-26', 'factor': 1.0}          ← 前复权以最新为基准
#   hfq 最早 {'date': '1900-01-01', 'factor': 1.0}          ← 后复权以最早为基准

bars = [{"date": "2015-01-05", "close": 202.52}]         # 茅台当日不复权收盘价
print(apply_adjust(bars, qfq, kind="qfq"))                # → 143.46（前复权，除法）
print(apply_adjust(bars, hfq, kind="hfq"))                # → 1274.28（后复权，乘法）
```

**方向实测对照（2026-08-19，以 baostock `adjustflag` 为基准交叉验证）**

| 日期 | 不复权 | baostock 前复权 | `raw × qfq` | `raw ÷ qfq` |
|------|--------|----------------|-------------|-------------|
| 2015-01-05 | 202.52 | **143.46** | 285.90 ❌ | **143.46** ✅ |
| 2026-08-14 | 1341.99 | 1341.99 | 1341.99 ✅ | 1341.99 ✅ |

> `qfq` 因子恒 ≥ 1 且越往历史越大，**乘上去会把历史价格放大**，必须做除法。
> 2026 那行两种算法都对，是因为最新日因子恰为 1.0 —— **只用最近日期做验证会漏掉这个 bug**。
>
> ⚠️ **hfq 的基准与 baostock 不同**：新浪 `raw × hfq` 与 baostock 后复权价差一个**恒定倍数**
> （实测 1.1582，2015 与 2026 两点一致）。后复权序列整体缩放不影响收益率与形态，
> 但**不要把新浪后复权价与其它源的后复权价直接比数值**。

> ⚠️ **北交所无复权因子**：实测 `bj920982` 返回 **404**（新浪未提供北交所的 qfq/hfq 文件），
> 本函数会抛 `HTTPError`。北交所标的请改用 §1.3 通达信盘后包的不复权日线，并自行按分红送转推导。
>
> **自检口径（实测 2026-08-19 校准）：**
> - `qfq` 序列**最新**一条因子恒为 `1.0`；`hfq` 序列**最早**一条恒为 `1.0`。
> - 同一日期上 **`qfq(d) × hfq(d)` 恒等于一个常数**（该标的全期总复权系数，茅台实测 `8.882513`）。
>   ⚠️ 两者**不是倒数**（乘积不为 1），比值 `hfq/qfq` 也**不恒定**（茅台 33 个日期有 32 种取值）——
>   两个基准不同的归一化序列，只有乘积守恒。
> 不满足以上任一条，说明响应被截断或标的代码写错。

<a id="mootdx"></a>

### 1.7 mootdx — K线 + 五档盘口 + 逐笔成交（⚠️ 2026-09 起行情命令失效，留档）

TCP 二进制协议，连通达信服务器(7709)，无需注册；不保证免限流、封禁或网络可达。

> **⚠️ 2026-09 起本节普遍取不到数（#52）：** 通达信公开服务器 TCP 仍可达，但 `bars` / `quotes` / `transaction`
> 返回 0 行（2026-09-20 逐台实测内置 10 台，全部如此）；`tdx_client()` 会在约 1 分钟测速后抛出带指引的 RuntimeError。
> 替代：**K 线 → §1.2 `tencent_kline()`**（沪深日周月前/后复权 + 1~60 分钟）或 **§1.3 `tdx_daily_package()`**（沪深北全市场某日含成交额，北交所日线只能走这里）；
> **实时价 → §1.1 腾讯**；**五档 →「备用源速查」中的交易所官方接口**；**逐笔 → §1.4 `tencent_ticks()`**（只有当日）。财务与 F10（§6.1 / §6.2 / §7.2）不受影响。以下代码保留，服务器恢复后可照常使用。

实现与命令入口：[scripts/tdx_client.py](../scripts/tdx_client.py)。直接运行，不必读取实现：

```bash
python3 "<skill目录>/scripts/tdx_client.py" bars --params '{"symbol":"688017","frequency":9,"offset":10}' --output bars.json
python3 "<skill目录>/scripts/tdx_client.py" quotes --params '{"symbol":["688017","300476"]}' --output quotes.json
python3 "<skill目录>/scripts/tdx_client.py" transaction --params '{"symbol":"688017","date":"20260502"}' --output trades.json
```

同一入口支持 `finance`、`F10C`、`F10`；财务/F10 自动用 finance 验活，其余用 bars。`--market` 默认 std；`--check bars|finance` 可显式覆盖。`--params` JSON 对象逐项原样传给 mootdx 方法，不改代码、不代填方法参数；frequency 必须按下方表格指定。上游方法的异常或空结果仍按原行为返回，不新增清洗、重试或“修复服务端”。

CLI 始终将完整结果保存到新 JSON 文件，省略 `--output` 则在当前目录生成 `mootdx-*.json`，不覆盖已有路径。stdout 仅给路径、类型对应的条数/字符数及预览：DataFrame/列表前三行，文本前 200 字。错误退出非零；选服/调用产生的 stdout 转到 stderr。保存优先原子硬链接，兼容模式独占创建后复制，须等待成功退出再读取；强制终止可能留下半成品。

DataFrame 文件保存 `columns`、列名/dtype、`dtypes` 列表、`index`（类型/dtype/名称/值，日期索引另有时区和频率）、`attrs`、`data` 行数组；每行按 columns 顺序排列，保留重复列。日期值用 `{"$date_type":"Timestamp","iso":"..."}`（或 datetime/date），缺失值用 `{"$missing":"NA"}` / `NaT`，非有限浮点用 `{"$float":"NaN"}` / `Infinity` / `-Infinity`。列表/文本/dict 保留原结构。MultiIndex、分类类型或无法明确表示的对象会报错，不静默转字符串；这类结果请用原生 Python API。Python 客户端能力与返回对象均不受 CLI 格式限制。

Python 用法（先执行路径初始化）：

```python
from tdx_client import tdx_client

client = tdx_client()  # 见 Prerequisites 的 tdx_client() helper（规避 0.11.x BESTIP bug；等价 Quotes.factory(market='std')）

# === K线数据 ===
# ⚠️ 参数名是 frequency（不是 category！传 category 会被 **kwargs 静默吞掉，
#    永远退化成默认 frequency=9 日线，拿不到分钟数据）。
# mootdx 0.11.7 实测频率值表：
#   0=5分钟  1=15分钟  2=30分钟  3=60分钟(1小时)  4=日线  5=周线  6=月线
#   8=1分钟  9=日线(默认)  10=季线  11=年线        （7=1分钟除权口径,少用）
klines = client.bars(symbol='688017', frequency=9, offset=10)    # 日线
min1   = client.bars(symbol='688017', frequency=8, offset=240)   # 1分钟（一个交易日≈240根）
min5   = client.bars(symbol='688017', frequency=0, offset=48)    # 5分钟
# 返回: open, close, high, low, vol, amount, datetime
# ⚠️ 复权：bars 返回【不复权】原始价（通达信原始数据，无 adjust 参数）。
#    跨除权除息日做估值/回测前需自行复权，或改用带前复权的日K数据源（腾讯财经）。

# === 实时报价 ===
quotes = client.quotes(symbol=['688017', '300476'])
# 返回 46 个字段:
#   price(现价), open, high, low, last_close(昨收)
#   bid1~bid5, ask1~ask5, bid_vol1~bid_vol5, ask_vol1~ask_vol5
#   vol(成交量), amount(成交额), servertime

# === 逐笔成交（非交易时间返回空）===
trades = client.transaction(symbol='688017', date='20260502')
# 返回: time, price, vol, num, buyorsell(0买/1卖/2中性)
```

**mootdx 不提供 PE / PB / 市值 / 换手率 / 涨跌停价** — 这些走腾讯财经。

---
