<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 龙虎榜、解禁、板块排名与组合观察

按需读取：[§3.5 个股龙虎榜](#dragon)、[§3.6 解禁](#lockup)、[§3.7 行业排名](#industry)、[§3.8 板块资金](#board-flow)、[§3.9 全市场龙虎榜](#daily-dragon)、[§3.10 组合示例](#workflow)。`<skill目录>` 指技能根目录。Python 调用先做 [路径初始化](../SKILL.md#python-脚本路径初始化)。

下文“与前节相同”的公共规则：东财串行共享会话，`--min-interval` 至少 1 秒，仅同进程生效；CLI 完整新文件不覆盖、父目录须存在，等成功退出后读取，不把三条预览当全部数据；原 helper 可能将业务错误转为空列表，空结果不证明无记录。其他章节见 [SKILL.md](../SKILL.md)。

<a id="dragon"></a>

### 3.5 龙虎榜席位 — 个股上榜记录 + 买卖席位 TOP5 + 机构动向

直连东财 datacenter API，不依赖第三方封装。

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，共用东财会话、重试与限流。只需 requests：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" dragon 2026-05-17 002475 --look-back 30 --output dragon.json
```

日期为查询截止日，回看按日历天计算；代码沿用原始输入，不自动规范化，使用纯 6 位。记录单页最多 50 条，按服务端日期倒序；只查询首条记录所属日期的买卖席位，各请求 10 条、展示前 5 条。机构统计遍历请求返回的全部席位，**不是仅前 5 条**；机构代码整数 0 / 字符串 "0" 均识别，买榜只计 BUY、卖榜只计 SELL，避免双重统计。金额单位万元、保留一位小数，换手率保留两位小数；机构净额用已舍入的买卖额相减。无记录时不查询席位，返回空记录/席位和零机构统计。

CLI 保存完整 records/seats/institution，stdout 仅给文件路径、记录条数和每组前三条预览；使用完整数据须读取文件。未指定输出时在当前目录生成新 JSON，不覆盖已有文件；非有限浮点以 $float 标记。--min-interval 与前两节相同，失败非零退出、不生成结果文件。原数据中心 helper 未校验业务状态，部分错误载荷仍可能变成空列表，不能仅凭空记录判断“没有上榜”；不新增分页、去重或席位补全。

Python 组合调用先初始化脚本路径，再导入；原例子保留：

```python
from eastmoney_signals import dragon_tiger_board

# 用法
data = dragon_tiger_board("002475", "2026-05-17")
print(f"近30日上榜 {len(data['records'])} 次")
for r in data["records"]:
    print(f"  {r['date']}: {r['reason']}")
if data["seats"]["buy"]:
    print("买入席位 TOP5:")
    for s in data["seats"]["buy"]:
        print(f"  {s['name']}: 买{s['buy_amt']}万 卖{s['sell_amt']}万 净{s['net']}万")
```

> **ST 股注意：** 5% 涨跌停更容易触发龙虎榜（"连续三日偏离值累计达12%"），科创板 20% 涨跌停则较少触发。

<a id="lockup"></a>

### 3.6 限售解禁日历 — 历史解禁 + 未来 90 天待解禁

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，沿用共享东财限流与重试：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" lockup 2026-05-17 002475 --forward-days 90 --output lockup.json
```

返回 history/upcoming 两组完整记录。**history 沿用原实现，只按代码查询、日期倒序取一页 15 条，并未限制 FREE_DATE ≤ trade_date，可能包含未来记录**，不能当成严格历史截面。upcoming 按起点至起点加 forward_days 日历天、两端包含，日期升序单页 20 条。两组可以重叠，不去重、不新增分页。代码原样传入，使用纯 6 位；保留原请求顺序，先取 history，再解析日期、查询 upcoming。

字段 date 为原日期字符串前十位；type 用 FREE_SHARES_TYPE；shares/able_shares 单位万股，ratio 是小数比例（展示百分比时 ×100）。字段原值不转型，缺失用默认值，显式 None 不补零；保留原排序与重复记录。

CLI 始终完整保存 JSON，stdout 的 row_count 分别列出 history/upcoming 条数，两组各仅预览前三条。省略输出路径时自动创建新文件，不覆盖旧文件，非有限浮点以 $float 标记；--min-interval 与前节相同。请求/解析失败非零退出、不生成结果文件；数据中心 helper 仍可能将错误业务载荷转成空列表，空结果不证明没有解禁。Python 组合调用先初始化脚本路径：

```python
from eastmoney_signals import lockup_expiry

# 用法
data = lockup_expiry("002475", "2026-05-17")
print(f"历史解禁 {len(data['history'])} 批")
for h in data["history"][:5]:
    print(f"  {h['date']}: {h['type']} 数量={h['shares']}")
if data["upcoming"]:
    print(f"未来90天待解禁 {len(data['upcoming'])} 批")
else:
    print("未来90天无待解禁")
```

**限售股类型参考：**
- 首发原股东限售股份（IPO 后 1-3 年）
- 首发机构配售股份（IPO 战略配售）
- 定向增发机构配售股份（6-18 个月）
- 股权激励限售股份

<a id="industry"></a>

### 3.7 行业板块排名（V3.0 改用东财 — 同花顺加了反爬401）

东财行业板块涨跌幅排名，一次调用看全市场行业轮动。

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，共享东财会话/限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" industry --top-n 20 --output industry.json
```

行业命令完整分页（每页100，上限50页），确认取得数等于服务端 total 后再排名。重复代码、提前空页、业务错误或总数变化时失败，不发布部分排名。top_n 必须为正；涨幅转有限数值，0% 保留，缺失单列 missing。top/bottom 都按涨幅降序，bottom 最后一条最弱；rank 为有效涨幅排名。leader 是 f140 股票代码，leader_change 为 f136。

行业/概念的今日或5日涨幅用 `board-quotes --board-type concept --period 5d --top-n 20`。默认 push2；失败后可显式尝试一次 `--source dataapi`。dataapi 的百分数原值除100（136→1.36%），仅返回代码、名称、涨幅；涨跌家数和领涨股字段为空。5日查询在两源下都将这些当日字段设为 null，避免误作5日指标。此接口属于同一供应商，不保证独立抗故障。不要用按主力净额排序的 board-flow 代替涨幅排名。

完整 JSON 保留 source、fetched_at、quote_time（未知为 null）、total、fetched_count、ranked_count、missing、complete、ranking_complete；complete 仅表示记录数取齐，ranking_complete=false 表示有缺失涨幅（数量为 missing_count，原值保留在 missing[].change_pct_raw）。排名仅含涨幅有效记录，不按题材名称筛除。完整分页仍不是同一时刻的原子快照；盘中涨幅排序变化引起重复页时会失败。抓取时间不是交易日。输出保护、自动文件及 --min-interval 规则同前节。异常不保存文件。Python 组合调用先初始化脚本路径：

```python
from eastmoney_signals import industry_comparison

# 用法
data = industry_comparison(20)
print(f"共 {data['total']} 个行业")
print("\nTOP 10 涨幅:")
for r in data["top"][:10]:
    print(f"  {r['rank']}. {r['name']}: {r['change_pct']}% 涨{r['up_count']}跌{r['down_count']} 领涨{r['leader']}")
print("\nBOTTOM 5 跌幅:")
for r in data["bottom"][-5:]:
    print(f"  {r['rank']}. {r['name']}: {r['change_pct']}%")
```

<a id="board-flow"></a>

### 3.8 板块资金流向（行业/概念/地域 × 今日/5日/10日）

东财板块资金流向——主力净流入额/净占比 + 超大/大/中/小单四档，覆盖行业、概念、地域三类板块，今日/5日/10日三个周期。与 §3.7 板块排名**同源同接口**（push2 `clist`），只是补请求了资金流字段（`f62/f184/f66...`）。走 `em_get` 限流防封。

实现位于同一 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" board-flow --board-type concept --period 5d --top-n 250 --output board-flow.json
```

board-type 为 industry/concept/region；period 为 today/5d/10d，**没有 3d**。按对应主力净额字段倒序，金额原值单位元、main_pct 为百分数；today 才有超大/大/中/小单四档，5d 无四档，10d 还省略领涨股字段、返回 leader 空字符串。主力净额不在本地重算。

保留每页 200 条和按需翻页：首次始终请求，未达到 top_n 才继续；达到首轮声明 total、后续空页或不足 200 条停止。total 取首轮声明值与已获取条数最大值，rows 最后按 top_n 切片；total 不等于 rows 长度。0/负 top_n 保留原切片语义。保持服务端顺序、不去重、不新增无限重复页防护；调用大 top_n 时须留意源异常。CLI 完整保存 board_type/period/total/rows，stdout 仅预览前三条；row_count 是实际保存 rows 数。

两命令异常均非零退出、不创建结果文件；无异常的空结构仍正常保存，不将其视作已验证的数据覆盖。非有限浮点用 $float 标记，指定文件不覆盖、未指定时自动生成；完整分析须读结果文件。Python 组合调用：

```python
from eastmoney_signals import board_fund_flow

# 用法
d = board_fund_flow("industry", "today", 10)
print(f"行业板块今日主力净流入 TOP{len(d['rows'])}（共 {d['total']} 个）:")
for r in d["rows"]:
    print(f"  {r['rank']}. {r['name']}: 主力 {r['main_net']/1e8:.2f}亿 ({r['main_pct']}%) "
          f"涨跌{r['change_pct']}% 超大{r['super_large_net']/1e8:.2f}亿 领涨{r['leader']}")

# 概念板块 5 日资金流
concept_5d = board_fund_flow("concept", "5d", 10)
# 地域板块 10 日资金流
region_10d = board_fund_flow("region", "10d", 10)
```

<a id="daily-dragon"></a>

### 3.9 全市场龙虎榜

每日全市场龙虎榜汇总——当日所有触发龙虎榜的股票 + 上榜原因 + 买卖净额 + 换手率。

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，共享东财限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" daily-dragon --date 2026-05-16 --min-net-buy 5000 --output daily-dragon.json
```

省略 --date 时沿用本地系统当天日期，不自动寻找最近交易日。请求单页最多 500 条、按 BILLBOARD_NET_AMT 降序；不分页、不按股票代码去重（同股多个上榜原因均保留）。净买入下限单位万元，**先用未舍入金额筛选，等于下限也保留**；原例子中的“>5000”文字实际对应 ≥5000。输出买入/卖出/净买入为万元、保留一位；涨跌幅/换手率两位。close 原值或 0，代码/名称/原因沿用原字段。

非空响应的 date 取首条原始记录日期，即使该条被筛掉；total_records 为筛选后条数。源返回空时附带原 note；筛选后变空时不新增 note。数据中心 helper 未验证业务状态，原 note 的“非交易日或盘后未更新”不是空结果成因证明。

CLI 始终全量保存 date/total_records/stocks/可选 note，stdout 只给保存条数和前三条预览；省略输出路径时自动创建文件，指定路径不覆盖。非有限浮点用 $float 标记；--min-interval、异常非零退出与输出保护沿用前节。Python 组合调用先初始化脚本路径：

```python
from eastmoney_signals import daily_dragon_tiger

# 用法
data = daily_dragon_tiger("2026-05-16")
print(f"{data['date']} 龙虎榜共 {data['total_records']} 条记录")
for s in data["stocks"][:10]:
    print(f"  {s['code']} {s['name']}: {s['reason']} | 净买{s['net_buy_wan']}万 涨跌{s['change_pct']}%")

# 只看净买入 > 5000 万的
data = daily_dragon_tiger("2026-05-16", min_net_buy=5000)
print(f"\n净买入 > 5000万: {data['total_records']} 条")
```

<a id="workflow"></a>

### 3.10 信号层组合用法：题材、北向与行业资金分别观察

先按 [Python 路径初始化](../SKILL.md#python-脚本路径初始化) 设置技能 scripts 路径，然后执行下方完整代码块。调用串行进行，不保存北向日历史；各源异常仍抛出，不把失败填成零。示例取各接口当前响应，报告前须核对各来源交易日和采样时刻，不把不同日期的结果联合解释。

热点标签频次仅描述标签分布；北向没有可靠交易日期，逐列保留最后有效点的时刻，不称收盘数、不拼总额；行业涨幅与板块主力净额分别输出，不能据此证明题材因果关系。行业资金同源于东财，是补充字段，不是独立来源验证。

```python
from collections import Counter
import math
from ths_hot_reason import ths_hot_reason
from northbound import hsgt_realtime
from eastmoney_signals import industry_comparison, board_fund_flow

# 题材标签分布；空表或字段缺失不冒充“当日无热点”。
df_hot = ths_hot_reason()
counts = Counter()
if "题材归因" not in df_hot.columns or df_hot["题材归因"].dropna().empty:
    print("未取得可用题材标签，不能判定当日无热点")
else:
    for value in df_hot["题材归因"].dropna():
        counts.update(tag.strip() for tag in str(value).split("+") if tag.strip())
    if counts:
        print("返回样本题材频次:", counts.most_common(10))
    else:
        print("未取得可用题材标签，不能判定当日无热点")

# 两个通道独立保留时刻；不把缺失填零、不推断收盘、不写缓存。
df_north = hsgt_realtime()
north_points = {}
for column, label in [("hgt_yi", "沪股通"), ("sgt_yi", "深股通")]:
    point = None
    if {"time", column}.issubset(df_north.columns):
        for _, row in df_north.iterrows():
            try:
                value = float(row[column])
            except (ValueError, TypeError):
                continue
            if math.isfinite(value) and isinstance(row["time"], str) and row["time"].strip():
                point = {"time": row["time"], "value_yi": value}
    north_points[column] = point
    if point is None:
        print(f"{label}：无可用时刻/数值，不能当零")
    else:
        print(f"{label}最后有效点 {point['time']}：{point['value_yi']} 亿元（非已核实收盘值）")
print("交易日须另行核实；沪股通仅作情绪参考，深股通可靠性有限；不合成同步总额")

# 涨幅排名与资金字段独立呈现，前者不证明后者。
comp = industry_comparison(10)
print("行业涨幅返回样本:", comp.get("top", [])[:5])
flows = board_fund_flow("industry", "today", 10)
print("行业主力净额返回样本（main_net 单位元）:", flows.get("rows", [])[:5])
print("空结果不证明无数据；核对交易日、覆盖范围和字段口径后再比较")
```
