<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 腾讯实时行情与 K 线

按任务阅读：[§1.1 实时行情](#quote)、[§1.2 K 线](#kline)。其他章节编号见 [SKILL.md](../SKILL.md)；本文 `<skill目录>` 始终指技能根目录。

<a id="quote"></a>

### 1.1 腾讯财经 API — PE/PB/市值/换手率/涨跌停/指数/ETF

HTTP GET，GBK 编码，`~` 分隔 88 个字段；不保证免限流或封禁，需控制请求频率。

实现位于 [scripts/tencent_quote.py](../scripts/tencent_quote.py)，直接运行，无需读取源码。仅需 Python 3.9+ 标准库。以下 `<skill目录>` 指技能根目录（SKILL.md 所在目录），执行时替换为实际路径：

```bash
python3 "<skill目录>/scripts/tencent_quote.py" 688017 300476 002463
python3 "<skill目录>/scripts/tencent_quote.py" sh000001 sh000300 sz399006 510050 510300
# 完整结果保存到新文件，终端只显示路径、数量和前三条预览
python3 "<skill目录>/scripts/tencent_quote.py" 688017 300476 --output quotes.json
```

腾讯报价保留 `quote_time`（源字段30，UTC+8）、`quote_time_raw`、`fetched_at`（UTC）与 `source`。源时间缺失/非法时 quote_time 为 null；抓取时间不能替代行情时间。原 is_stale 仅为零成交启发式标志，不能单凭 false 认定报价新鲜。

`tencent_quote()` 当前不返回五档买卖价量；需要五档时按「备用源速查」使用交易所官方接口。

返回 `{输入代码: 行情字段}`。代码按字符串传入；裸 `000001` 是平安银行，上证指数必须用 `sh000001`。显式 `sh000001` / `sz000001` 可同时查询，返回键保留入参写法。支持裸六位码及 `sh` / `sz` / `bj` 前缀，不把后缀写法直接传给本函数。

成交额 `amount_wan` 为万元，`float_mcap_yi` / `mcap_yi` 为流通 / 总市值（亿元），涨跌幅与换手率为百分数。保留原有 `is_stale` / `stale_reason` 检测；标记为陈旧的报价须核查。返回可能缺少请求的代码，应核对结果键；原函数会跳过短报文，空结果不等于价格为零。

CLI 的 stdout 只输出 JSON，错误写 stderr 并返回非零退出码。超过 20 个输入代码须指定 `--output`，文件保存完整结果，不覆盖已有文件，父目录须已存在；相对路径基于当前工作目录。非有限数值用 `$float` 对象标记，如 `{"$float": "Infinity"}`；可选值为 `NaN`、`Infinity`、`-Infinity`，不混同缺失值。参数帮助用 `--help`。

指定 JSON 输出会在取数前拒绝已有文件、目录和悬空符号链接。腾讯报价先写临时文件，再独占发布；可捕获的写入失败会清理自身半成品。硬链接不可用时降级为独占创建并复制，读取方须等待 CLI 成功退出。

#### Python 组合调用

先在同一个 Python 进程执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，然后导入：

```python
from tencent_quote import tencent_quote
```

随后可调用 `quotes = tencent_quote(["sh000001", "sz000001", "510300"])`。函数返回原生 dict，不做 CLI 序列化，导入本身不会联网。CLI 在独立进程运行，不会向当前 Python 进程导入函数。批量查询将代码放在同一次调用中，不逐只并发启动进程。

#### 腾讯财经字段索引速查（实测校准 2026-05-03）

| 索引 | 含义 | 示例 |
|------|------|------|
| 1 | 名称 | 绿的谐波 |
| 3 | 当前价 | 224.12 |
| 4 | 昨收 | 215.01 |
| 5 | 今开 | 214.10 |
| 9-18 | 买一~买五(价+量) | |
| 19-28 | 卖一~卖五(价+量) | |
| 31 | 涨跌额 | 9.11 |
| 32 | 涨跌幅% | 4.24 |
| 33 | 最高 | 229.62 |
| 34 | 最低 | 214.10 |
| 37 | 成交额(万) | 187040 |
| 38 | 换手率% | 4.55 |
| **39** | **PE(TTM)** | 300.45 |
| **43** | **振幅%（不是PB！）** | 7.22 |
| **44** | **流通市值(亿)** | 410.88 |
| **45** | **总市值(亿)** | 410.88 |
| **46** | **PB(市净率)** | 11.51 |
| **47** | **涨停价** | 258.01 |
| **48** | **跌停价** | 172.01 |
| 49 | 量比 | 1.20 |
| **52** | **PE(静)** | 314.76 |

> **踩坑提醒一：** 网上很多教程把索引 43 写成 PB，实测是振幅%。PB 在索引 46。
>
> **踩坑提醒二（2026-07-26 修正）：** **44 是流通市值、45 才是总市值**，此前本表标反了。
> 多数股票两者相等，所以看不出来；但**总股本 ≠ 流通股本的票（科创板/次新股/有限售股）会差出数倍**。
> 实测中船特气(688146)：`f[44]=356.15亿`(流通股本 1.45亿股)、`f[45]=1300.61亿`(总股本 5.29亿股)，**差 3.65 倍**。
> 用市值做筛选时取错会把大市值公司误判成小盘股。可用 `f[45] ÷ 现价` 反推总股本核对（与东财 `f84` 一致）。
> 参考：东财 push2 的 `f116`=总市值 / `f117`=流通市值 方向与腾讯相反，实测确认无误，勿混用。

<a id="kline"></a>

### 1.2 腾讯 K 线 — 日/周/月前后复权 + 1~60 分钟（V3.9.0 新增 · #52）

§1.7 mootdx K 线失效（#52）后的主力 K 线源。三个入口是同一后端、限流各自独立：某入口返回空或异常时冷却 120 秒、换下一个，
三个都不可用才抛错（#52 实测单入口约 600 次后返回空 JSON）。**只支持沪深**：腾讯对北交所只返回最新 1 根日线、
区间和分钟线都是空的（2026-09-20 实测 920021 / 920982 / 920185），函数遇北交所代码直接抛 `ValueError`，北交所日线用 §1.3。

| 参数 | 说明 |
|---|---|
| `period` | `day` / `week` / `month`：默认前复权，可 `adjust='hfq'` 或 `adjust=''`（不复权）；`m1` / `m5` / `m15` / `m30` / `m60`：只有不复权、只能取最近 ≤320 根 |
| `start` / `end` | 仅日周月可用，自动按段翻页（单段 <640 根）；不给 `start` 时取最近 `count` 根（≤640） |
| 返回列 | `code` / `adjust` / `date` / `open` / `high` / `low` / `close` / `volume`（手）；分钟线另有 `turnover_rate_pct`，日期列名为 `datetime` |

> ⚠️ **腾讯前复权是等差口径**（逐次减去每股分红）：茅台 2020-01-02 原始价 1130.00、腾讯 qfq 870.741，差额正是此后累计分红；
> 高分红老股早年会被减成负数（茅台 2015 年约 -117.6）。本函数遇到 ≤0 价格直接抛错。**长区间回测请取 `adjust=''`，
> 再用 §1.6 的比例因子复权**。本接口**没有成交额**，需要成交额用 §1.3。

实现位于 [scripts/tencent_kline.py](../scripts/tencent_kline.py)，仅需 requests、pandas（复用原依赖）。直接运行，无需读取源码；`<skill目录>` 替换为技能根目录（SKILL.md 所在目录）：

```bash
python3 "<skill目录>/scripts/tencent_kline.py" 600519 --count 5
python3 "<skill目录>/scripts/tencent_kline.py" 600519 --adjust none --start 2025-01-01 --end 2025-12-31 --output daily.json
python3 "<skill目录>/scripts/tencent_kline.py" 300750 --period m5 --count 96 --output minute.json
python3 "<skill目录>/scripts/tencent_kline.py" sh000001 --period week --count 5
```

CLI 的 `--adjust none`（或空字符串）对应 Python 的 `adjust=""`；省略时仍由周期决定默认复权。`--count` 控制最近根数，给定 `--start` 后按日期范围分页，不用它截断区间数据。

stdout 输出 JSON：`columns`、`dtypes`、`index`（RangeIndex 的名称、起止、步长）、`attrs` 和完整 `data`。日周月有 `date` / `adjust` 列；分钟线为 `datetime`，不额外补 `adjust`。`source_url` 保留所有实际成功入口，`fetched_at` 保留原始抓取时间；非有限值用 `$float` 对象显式表示。Python 导入调用仍返回原生 DataFrame。

不指定 `--output` 时，≤20 行直接输出完整 JSON；超过 20 行自动保存到当前工作目录的 `tencent-kline-*.json`。指定 `--output` 时始终保存完整文件，父目录须存在，不覆盖旧文件。保存后 stdout 只给出绝对路径、总行数和前三条预览（`preview_only=true`）；分析完整区间时读取文件，不把预览当完整数据。错误写 stderr，退出码非零。

显式输出优先原子发布；文件系统不支持硬链接时改用独占创建并复制，仍不覆盖旧文件，但写入期间目标可能已可见。请等 CLI 成功退出后读取；捕获到写入错误会清理本次创建的半成品，进程被强制终止时可能留下未完成文件。

入口冷却状态只在同一 Python 进程内共享；多次导入不会重置，重新启动 CLI 不继承上次状态。批量任务在一个 Python 进程内串行调用，不逐只启动 CLI。**没有新增重试或降级**：保留三个入口原顺序、120 秒冷却；参数错误、取得数据后的结构/日期/数值校验错误仍按原规则抛出，不用原始价替代异常的复权数据。

Python 组合调用：先在同一进程执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，再导入：

<!-- v39-tencent-kline:start -->
```python
from tencent_kline import tencent_kline
```
<!-- v39-tencent-kline:end -->

```python
day = tencent_kline("600519", start="2025-01-01")            # 前复权日线，自动分段
raw = tencent_kline("600519", adjust="", count=250)            # 不复权 → 可交给 §1.6 apply_adjust
m5 = tencent_kline("300750", period="m5", count=96)           # 最近 96 根 5 分钟线
idx = tencent_kline("sh000001", period="week", count=100)     # 指数（上证指数要写 sh 前缀）
```
