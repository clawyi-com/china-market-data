<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 热点、北向、板块归属与分钟资金流

按需读取：[§3.1 热点](#hot)、[§3.2 北向](#northbound)、[§3.3 板块归属](#boards)、[§3.4 分钟资金流](#minute)。`<skill目录>` 指技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)，其他章节编号见 [SKILL.md](../SKILL.md)。

<a id="hot"></a>

### 3.1 同花顺热点 — 当日强势股 + 题材归因 reason tags（独家）

**核心价值：** 不只告诉你"哪些走强"，还告诉你**"为什么走强"** —— 同花顺编辑部人工运营的题材标签。

实现位于 [scripts/ths_hot_reason.py](../scripts/ths_hot_reason.py)，需要 requests、pandas。单次请求直接取指定日期，没有分页；无需读取源码：

```bash
python3 "<skill目录>/scripts/ths_hot_reason.py" --date 2026-09-25 --output hot-reasons.json
```

省略 `--date` 时按本机今天生成 YYYY-MM-DD；显式日期原样传递，不新增格式校验。保留原 HTTP URL、timeout=10、errocode 判断及下表 11 个字段改名；不转换价格/涨幅字符串、不换算量额、不拆分题材标签，额外字段保持原值。空 data 返回原无列空 DataFrame，下面选列示例需在有数据时运行。原函数没有新增 HTTP 状态/完整性校验，某些异常载荷也可能被视为空表，不能据此断言当天没有热点。

CLI 始终保存完整表格，stdout 只给路径、行数、三条预览；省略输出路径则当前目录生成 `ths-hot-*.json`，不覆盖已有文件。JSON 使用 columns/columns_index/dtypes/index/attrs/data，data 为按列顺序排列的行数组，保留重名列与嵌套值；非有限值/缺失值/日期用 `$float` / `$missing` / `$date_type` 显式标记。Python API 仍返回 DataFrame。

保存优先硬链接、否则独占创建后复制；等待成功退出再读，强制终止可能留下半成品。请求、解析和保存失败写 stderr，非零退出。Python 组合调用先执行路径初始化：

```python
from ths_hot_reason import ths_hot_reason

# 用法
df = ths_hot_reason("2026-05-09")
print(f"当日强势股: {len(df)} 只")
print(df[["代码", "名称", "涨幅%", "题材归因"]].head(10))
```

#### 同花顺热点字段速查

| 原字段 | 中文 | 说明 |
|---|---|---|
| code | 代码 | 6 位股票代码 |
| name | 名称 | 简称 |
| **reason** | **题材归因** | **核心字段，人工运营 tags，如"算力租赁+Token工厂+AI政务"** |
| zhangfu | 涨幅% | 当日涨幅 |
| huanshou | 换手率% | 当日换手 |
| chengjiaoe | 成交额 | 元 |
| chengjiaoliang | 成交量 | 股 |
| ddejingliang | 大单净量 | 主力净流入指标 |
| close | 收盘价 | 元 |
| zhangdie | 涨跌额 | 元 |
| market | 市场 | 沪/深/北 |

<a id="northbound"></a>

### 3.2 同花顺北向资金 — 当日分钟流向与本地已保存历史

**按需求选命令：** 看今天/盘中的沪深股通流向用 `realtime`；看本地已积累的历史用 `history`。查询不会自动积累历史，无缓存时不能满足历史走势需求；需要保存时再使用下方显式保存命令。

> **⚠️ 深股通实时流向近期不可靠（2026-07 实测）：** 沪股通(hgt)分钟序列完整，但深股通(sgt)
> 常只回传零星几个点、末值量级异常。根因是北向自 2024-08 起收紧盘中实时披露，非本代码问题。
> 结论：**hgt 可用于当日情绪，sgt 仅供参考**；要权威北向数据用 HKEX 官方日统计
> （`hkex.com.hk/chi/csm/DailyStat/data_tab_daily_YYYYMMDDc.js`，见文末「备用源速查」）。

> **已知行业性问题：** eastmoney 全系北向数据自 2024-08 后净买额字段返回 NaN/0，属上游断供。已改为**本地 CSV 自缓存模式**——实时查询默认不写缓存；显式保存后逐步积累历史，日期与保存方式见下文。

实现位于 [scripts/northbound.py](../scripts/northbound.py)，需要 requests、pandas。通常只需下面两种查询，无需读取源码：

```bash
python3 "<skill目录>/scripts/northbound.py" realtime --output northbound-minutes.json
python3 "<skill目录>/scripts/northbound.py" history --count 20 --output northbound-history.json
```

**需要积累历史时才执行：** `realtime --save-date` 查询后保存最后一个完整分钟点；`save` 写入调用方提供的数值，不联网。下列日期与数值仅作示例，执行前替换为核实后的数据。

```bash
python3 "<skill目录>/scripts/northbound.py" realtime --save-date 2026-09-25 --output northbound-with-cache.json
python3 "<skill目录>/scripts/northbound.py" save 2026-09-25 --hgt 1.2 --sgt -0.3
```

**日期与缓存：** realtime 默认只取分钟表、不写 CSV；显式 `--save-date` 才按原示例取 `df.dropna().iloc[-1]` 写缓存。短 sgt 序列可能使“最后完整点”早于最后一个 hgt 点，这并不保证是收盘数。空表不写缓存；非空但没有完整点时按旧示例失败。接口只有时刻，不会可靠地推断所属交易日，必须自行核对 `--save-date`；上述日期/数值及下方原示例日期仅演示命令。save 是手动写入/更新原值（亿元），不联网；history 只读本地已采集数据，不补抓历史。

默认缓存路径保持 `~/.tradingagents/cache/northbound_daily.csv`（Python Path.home），与工作目录无关；访问缓存路径会创建父目录，历史不存在则返回无列空表。保存按日期键更新，同日替换，按日期字符串排序；旧文件只保留逗号分隔恰好三个字段的行。历史列名为 date/hgt/sgt，单位仍为亿元；history 仍用 pandas.tail(n)，默认 20，负 n 的旧语义也保留。CSV 保存仍是旧版直接覆写，无并发锁、原子发布或失败回滚；请串行调用。CSV 与 CLI 的 JSON 文件不是一个事务：缓存已成功写入后 JSON 保存失败，缓存更新仍保留。

分钟表以 time 数组长度为准，hgt/sgt 较长则截断，较短则用 None 补齐；字段为 time/hgt_yi/sgt_yi，不额外转换或校验数值。原 HTTP/JSON 错误识别与数据可靠性限制保留，不能只凭成功返回判断源数据有效。

realtime/history 始终完整保存 JSON（columns/columns_index/dtypes/index/attrs/data，data 为行数组），stdout 仅给路径、行数、三条预览；省略输出则当前目录生成 `northbound-*.json`，不覆盖已有路径。NaN/NA/日期等使用显式标记，历史 tail 的原索引保留。save 直接写 CSV，stdout 返回缓存路径和日期。JSON 保存优先硬链接，否则独占创建并复制；等待成功退出再读，强制终止可能留下半成品；这项保证不适用于 CSV。失败写 stderr，CLI 非零退出。

Python 组合调用先执行路径初始化，再导入；四个原函数和返回类型保留：

```python
from northbound import hsgt_realtime, _northbound_cache_path, _save_northbound_snapshot, _load_northbound_history

# 用法 1: 实时分钟流向
df = hsgt_realtime()
print(f"分钟点数: {len(df)}")
print(df.tail(5))

# 用法 2: 显式保存最后完整分钟点（不保证是收盘值；示例日期须核对替换）
if not df.empty:
    last = df.dropna().iloc[-1]
    _save_northbound_snapshot("2026-05-17", last["hgt_yi"], last["sgt_yi"])

# 用法 3: 读取历史
hist = _load_northbound_history(20)
print(hist)
```

<a id="boards"></a>

### 3.3 东财 slist — 个股所属板块/概念归属（V3.2.2 替换百度）

**核心价值：** 一次调用拿到个股所属的全部板块（行业 + 概念 + 地域混合），含板块代码（BK码）、当日涨跌幅、板块龙头股。题材归因、板块联动分析必备。

> **V3.2.2 替换说明：** 百度 PAE `getrelatedblock` 接口已失效（实测返回 `ResultCode 10003` + 空数组，#18），改用东财 `slist` 个股所属板块接口（`spt=3`，一次请求拿全，零鉴权）。东财把行业/概念/地域混在**一个列表**里返回，板块名本身已自解释（如「食品饮料」是行业、「贵州板块」是地域、「酿酒概念」是概念），AI 直接用板块名做题材归因即可。

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，共享 `_eastmoney` 的会话与限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" boards 600519 --output boards.json
```

此函数只用 em_market_code 判市场，secid 的代码部分仍原样拼接；**优先传纯 6 位代码**，不要误以为它和 minute 一样自动剥离 SH/.SH 等写法。保留单次 spt=3/pz=200 请求、dict/list 两种 diff 结构、原顺序及缺失字段默认值；不会分类行业/概念/地域，也不转换涨幅类型。total 按实际返回条数，concept_tags 是所有板块名。

CLI 始终保存完整 JSON，stdout 只给路径、行数和三条预览；省略输出路径时当前目录生成 `eastmoney-signals-*.json`，已有文件不覆盖。非有限浮点用 `$float` 显式标记。原函数捕获请求/JSON 解析异常后会打印 WARN 并返回空结构；CLI 将 WARN 转到 stderr 并退出 1，不保存空结果、不生成成功摘要；正常响应中的空数据仍保存并退出 0。返回结构错误等未捕获异常也非零退出。此处仅识别原函数已报告的请求/解析失败，没有新增 HTTP/业务状态验证，正常退出不能单独证明源数据有效。

`--min-interval 1.5` 可调整本次调用的共享间隔，至少 1 秒；调用结束恢复原间隔，不清空请求时间戳。仅限单进程串行调用，不保证并发/多进程限流。JSON 优先硬链接发布，不支持时独占创建后复制；等待成功退出再读，强制终止可能留下半成品。

Python 组合调用先执行路径初始化，再导入：

```python
from eastmoney_signals import eastmoney_concept_blocks

# 用法
blocks = eastmoney_concept_blocks("600519")
print(f"共 {blocks['total']} 个板块")
print("板块归属:", blocks["concept_tags"])
# → ['食品饮料', '白酒Ⅲ', '白酒Ⅱ', '贵州板块', '酿酒概念', 'HS300_', ...]
```

> **注意：** 东财不区分行业/概念/地域类型（混在一个列表返回）。如需精确分类可按板块名判断，或另查全市场板块清单（`clist` + `m:90+t:1/2/3`）——但后者每次需多发请求、大页易触发风控，不推荐在批量场景用。

<a id="minute"></a>

### 3.4 东财 push2 — 个股资金流向（分钟级）

盘中实时分钟级资金流（主力/大单/中单/小单/超大单净流入）。

> **V3.1 替换说明：** 百度 PAE `fundflow` 和 `fundsortlist` 接口已于 2026-05 下线（返回 null），改用东财 push2 资金流 API。日级资金流见 Layer 4.5 `stock_fund_flow_120d()`。

实现同样位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" minute 000858 --output minute-flow.json
```

该函数用 em_secid 规范化代码并保留市场，支持原有前后缀/聚宽写法。沪 ETF/B 股路由保持正确，但 ETF 不保证有个股资金流覆盖。返回字段为 time/main_net/small_net/mid_net/large_net/super_net，数值 float、单位元；保留原顺序，不新增日期过滤、分页或汇总。短于六段的行仍按旧规则跳过，第七段及之后忽略；坏数值转换会报错，非有限浮点没有新增业务拒绝。

CLI 始终保存完整 JSON，stdout 只给路径、行数和三条预览；省略输出路径时当前目录生成 `eastmoney-signals-*.json`，已有文件不覆盖。非有限浮点用 `$float` 显式标记。原函数捕获请求/JSON 解析异常后会打印 WARN 并返回空结构；CLI 将 WARN 转到 stderr 并退出 1，不保存空结果、不生成成功摘要；正常响应中的空数据仍保存并退出 0。返回结构错误等未捕获异常也非零退出。此处仅识别原函数已报告的请求/解析失败，没有新增 HTTP/业务状态验证，正常退出不能单独证明源数据有效。

`--min-interval 1.5` 可调整本次调用的共享间隔，至少 1 秒；调用结束恢复原间隔，不清空请求时间戳。仅限单进程串行调用，不保证并发/多进程限流。JSON 优先硬链接发布，不支持时独占创建后复制；等待成功退出再读，强制终止可能留下半成品。

Python 组合调用先执行路径初始化，再导入：

仅报告最后返回记录的时间和主力字段值，不跨分钟求和；这既不证明是全天总额，也不证明字段口径已核实。

```python
import math
from eastmoney_signals import eastmoney_fund_flow_minute

realtime = eastmoney_fund_flow_minute("000858")
if not realtime:
    print("未取得分钟资金流；不能判定为零流入")
else:
    last = realtime[-1]
    value = last.get("main_net")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        print(f"最后返回记录 {last.get('time', '时刻缺失')}：主力字段值 {value/1e4:.2f} 万元")
        print("交易日期及累计/期间口径需核实，未计算全天合计")
    else:
        print("最后返回记录的主力字段缺失或非有限，不能当作零")
```

> **注意：** push2 资金流金额单位是**元**（非万元），使用时注意换算。`klt=1` 分钟级，`klt=101` 日级。
