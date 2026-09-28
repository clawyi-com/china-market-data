<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 资金面、筹码模型与 ETF 份额

按任务读取：[§4.1 两融](#margin)、[§4.2 大宗](#block)、[§4.3 股东户数](#holders)、[§4.4 分红](#dividends)、[§4.5 日资金流](#stock-flow)、[§4.6 筹码推演](#chips)、[§4.7 ETF份额](#etf)。`<skill目录>` 指技能根目录；Python 组合使用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

**§4.1–§4.4 共用规则：** 代码原样传入，使用纯 6 位；--page-size 透传单页大小，不新增分页、排序或去重。date 是原日期字符串前十位；缺失与显式 None 维持原行为。CLI 保存完整列表，stdout 只给路径/实际条数/前三条预览，省略输出时自动新建文件，已有路径不覆盖；非有限浮点用 $float 标记。--min-interval 至少 1 秒，本次调用后恢复；异常非零退出、不创建结果文件。数据中心 helper 未新增业务状态验证，空列表不能证明没有记录。

<a id="margin"></a>

### 4.1 融资融券明细

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，共享东财数据中心查询与限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" margin 600519 --output margin.json
```

融资融券按 DATE 倒序单页查询，默认 30 条。字段 rzye/rzmre/rzche/rqye/rqmcl/rqchl/rzrqye 原样映射；融资和融券余额为元，不在脚本中换算亿元。缺失字段用 0，显式 None 保留，数量字段不误当金额。

CLI 输出、限流与错误规则见本层 §4.1–§4.4 共用规则。Python 组合调用先初始化脚本路径：

```python
from eastmoney_signals import margin_trading

# 用法
data = margin_trading("600519")
for d in data[:5]:
    print(f"{d['date']}: 融资余额={d['rzye']/1e8:.2f}亿 融券余额={d['rqye']/1e8:.2f}亿")
```

<a id="block"></a>

### 4.2 大宗交易

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，共享东财数据中心查询与限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" block 600519 --output block.json
```

大宗交易默认 20 条，按 TRADE_DATE 倒序。close/price 采用原值或 0；溢价率用 (price/close-1)×100、保留两位，close 为 0 时溢价仍按旧规则为 0，不代表真实平价。vol/amount/buyer/seller 原样映射，不新增单位换算或字符串数值解析。

CLI 输出、限流与错误规则见本层 §4.1–§4.4 共用规则。Python 组合调用先初始化脚本路径：

```python
from eastmoney_signals import block_trade

# 用法
data = block_trade("600519")
for d in data[:5]:
    print(f"{d['date']}: 价格={d['price']} 溢价={d['premium_pct']}% 买方={d['buyer']}")
```

<a id="holders"></a>

### 4.3 股东户数变化

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，共享东财数据中心查询与限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" holders 600519 --output holders.json
```

股东户数默认 10 条，按 END_DATE 倒序。HOLDER_NUM、HOLDER_NUM_CHANGE、HOLDER_NUM_RATIO、AVG_FREE_SHARES 分别映射 holder_num/change_num/change_ratio/avg_shares；变化比例原口径为百分数，不乘除 100。原接口 RPT_HOLDERNUMLATEST 不额外补抓历史，返回内容以数据源为准。

CLI 输出、限流与错误规则见本层 §4.1–§4.4 共用规则。Python 组合调用先初始化脚本路径：

```python
from eastmoney_signals import holder_num_change

# 用法
data = holder_num_change("600519")
for d in data[:5]:
    print(f"{d['date']}: 股东数={d['holder_num']} 变化={d['change_ratio']}% 户均={d['avg_shares']}")
# 股东户数减少仅说明持有人数量变化，不能单独证明主力吸筹。
```

<a id="dividends"></a>

### 4.4 分红送转历史

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，共享东财数据中心查询与限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" dividends 600519 --output dividends.json
```

分红送转默认 20 条，按 EX_DIVIDEND_DATE 倒序。PRETAX_BONUS_RMB、TRANSFER_RATIO、BONUS_RATIO、ASSIGN_PROGRESS 原样映射 bonus_rmb/transfer_ratio/bonus_ratio/plan；原注释口径为税前每股派息、每 10 股转增/送股，迁移不改变数值或新增单位换算。日期缺失可能为空，未新增除权日/进度过滤。

CLI 输出、限流与错误规则见本层 §4.1–§4.4 共用规则。Python 组合调用先初始化脚本路径：

```python
from eastmoney_signals import dividend_history

# 用法
data = dividend_history("600519")
for d in data[:5]:
    print(f"{d['date']}: 每股派息={d['bonus_rmb']}元 转增={d['transfer_ratio']} 送={d['bonus_ratio']}")
```

<a id="stock-flow"></a>

### 4.5 个股资金流（120日，日级）

实现位于 [scripts/eastmoney_signals.py](../scripts/eastmoney_signals.py)，仅需 requests，沿用共享东财会话、重试和限流：

```bash
python3 "<skill目录>/scripts/eastmoney_signals.py" stock-flow 600519 --output stock-flow.json
```

请求 lmt=120，不额外裁剪服务端返回行数。用 em_market_code 判沪/深北市场，但代码部分原样拼接，**使用纯 6 位代码**，不把它误认为 minute 的 em_secid 归一化。返回 date/main_net/small_net/mid_net/large_net/super_net，金额单位元，保持源顺序与重复日期。

原解析要求每行至少 7 段，虽然仅取前 6 段；更短行跳过，额外段忽略。数值 "-" 按旧行为变整数 0，其余转 float；空串/非法字符串报错，NaN/Infinity 不新增业务过滤。日期原样保留，不新增日期排序、校验或过滤。原函数捕获请求/JSON 异常后 WARN + [] 的行为不变；CLI 遇 WARN 将其写 stderr、退出 1，不创建空结果文件。正常空响应仍保存，不能仅凭空列表判断无资金流。

CLI 保存完整列表，stdout 只给路径、总行数与前三条预览；省略输出时自动创建文件、已有路径不覆盖，非有限值用 $float 标记。--min-interval 至少 1 秒，本次结束恢复。下面示例校验日期、重复和数值后，统计返回数据中日期最新的 20 条；不保证它们连续覆盖最近 20 个交易日。使用完整文件或 Python 返回值，不能用三条预览计算。源缺失标记已转成 0，无法从返回值恢复，累计值仍需核对源数据完整性。Python 组合调用先初始化脚本路径：

```python
from datetime import datetime
import math
from eastmoney_signals import stock_fund_flow_120d


def summarize_latest20(data):
    by_date = {}
    for row in data:
        try:
            date = row["date"]
            parsed = datetime.strptime(date, "%Y-%m-%d")
            value = row["main_net"]
            if parsed.strftime("%Y-%m-%d") != date or date in by_date:
                raise ValueError("日期无效或重复")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("金额无效")
            by_date[date] = value
        except (KeyError, TypeError, ValueError):
            print("日期、重复记录或金额异常，不能统计；请核对完整数据。")
            return
    if len(by_date) < 20:
        print(f"仅有 {len(by_date)} 条有效记录，不能计算最新20条累计。")
        return
    dates = sorted(by_date)[-20:]
    total_main = sum(by_date[date] for date in dates)
    print(f"返回数据最新20条（{dates[0]} 至 {dates[-1]}）主力累计净流入: {total_main/1e8:.2f}亿")
    print("未核验交易日连续性及数据新鲜度；源缺失标记可能已转为0，不代表完整的近20交易日资金流。")


data = stock_fund_flow_120d("600519")
summarize_latest20(data)
```

> **⚠️ 大陆住宅 IP 间歇封锁（#18）：** push2/push2his 系列对**部分大陆住宅宽带 IP** 有连接级风控，表现为偶发 `HTTP 000`（连接被拒/超时）或返回空——**这不是代码问题**（同一代码在其他网络/时段实测正常）。遇到时：① 隔几分钟重试；② 换网络环境（如手机热点）；③ 降低请求频率（调大 `EM_MIN_INTERVAL`）。日级资金流务实替代：用 §1.2 腾讯 K 线或 §1.3 通达信盘后包的量价数据（mootdx 行情命令已失效，#52），或换时段重试。

---

<a id="chips"></a>

### 4.6 筹码分布 CYQ — 获利比例 / 平均成本 / 成本区间（V3.7.0 新增）

**核心价值：** 本层叫「资金面 / **筹码**层」，但 §4.1~§4.5 全是融资融券、大宗、股东户数这类
**资金面**数据，一直缺真正的**筹码分布**。本端点补齐。

🔴 **东财没有公开 CYQ 接口**（2026-08-19 实测 `push2/api/qt/stock/cyq/get` 与 `push2his` 两种写法**均 404**）。
业界通行做法是**本地推演**：历史筹码按换手率衰减，当日成交量按三角分布撒进 `[low, high]` 区间。
**零新增数据源** —— OHLC 与换手率都从 §6.5 baostock 一次取齐（见下方用法）。

计算实现位于 [scripts/chip_distribution.py](../scripts/chip_distribution.py)，依赖 numpy、pandas；CLI 只读取本地文件，不自动联网取数：

```bash
python3 "<skill目录>/scripts/chip_distribution.py" prices.csv --grid-size 300 --decay 1.0 --output chips.json
```

支持 UTF-8 CSV（含表头）或 JSON 对象数组（--format csv|json 可覆盖文件后缀推断）。必须包含 date/high/low/close/turn；数值列须是数值，turn 为百分数（0.31 表示 0.31%），日期用 YYYY-MM-DD。CSV 按 pandas 默认类型推断，JSON 用 DataFrame 构建，不另做 to_numeric 清洗；复杂类型数据可直接调用原 Python API。

保留原模型：先丢弃 high/low/close/turn 缺失行，保留 high>0，再按 date 升序；首个有效价格区间播种为全部期初筹码，之后按 turn/100×decay（夹在 0–1）衰减叠加。三角权重峰值为 (high+low+close)/3；一字板映射最近网格，窄振幅无网格点时也映射最近均价网格。首日换手不缩小期初总仓位。均价/分位数在完整归一化网格上计算；histogram 只返回权重大于 1e-6 的点，不能把截断后的直方图当成未损失的完整网格。

CLI 完整保存所有指标与原返回 histogram，stdout 仅展示标量/区间及直方图前三点；Python 区间与点对的 tuple 在 JSON 中表示为数组，非有限值以 $float 标记。未指定输出时当前目录自动新建 JSON，指定路径不覆盖；优先硬链接发布、不支持则独占创建并复制，须等成功退出后再读。输入/计算/保存失败非零退出。CLI 不替代前复权、停牌过滤和取数准备，仍按下方原例子构造数据；模型推演与启发式限制保留。

Python 组合调用先初始化脚本路径，再导入：

```python
import pandas as pd
from chip_distribution import chip_distribution, _triangular_weights
from baostock_data import bs_session, _rs_to_df, _bs_code

# 用法 — 输入用 §6.5 baostock（一次拿齐 OHLC + 换手率）
import baostock as bs

bs_code = _bs_code("600519")
with bs_session():
    rs = bs.query_history_k_data_plus(
        bs_code, "date,open,high,low,close,turn,tradestatus",
        start_date="2026-02-01", end_date="2026-08-18", frequency="d", adjustflag="2",
    )                                            # 2=前复权，筹码成本必须用复权价
    k = _rs_to_df(rs)
for c in ("open", "high", "low", "close", "turn"):
    k[c] = pd.to_numeric(k[c], errors="coerce")
k = k[k["tradestatus"] == "1"]                   # 停牌日不参与换手衰减

r = chip_distribution(k)
print(f"现价 {r['price']:.2f} | 获利比例 {r['profit_ratio']*100:.2f}% | 平均成本 {r['avg_cost']:.2f}")
print(f"90%成本区间 {r['cost_90'][0]:.2f}~{r['cost_90'][1]:.2f} 集中度 {r['concentration_90']*100:.2f}%")
print(f"筹码峰 {r['peak_price']:.2f}")
# 实测 2026-08-19（131 个交易日，窗口累计换手 46.5%）：
#   现价 1297.99 | 获利比例 15.44% | 平均成本 1371.31
#   90%成本区间 1207.89~1425.16 集中度 8.25% | 筹码峰 1398.99
#   ← 窗口累计换手不足 100%，多数筹码仍是期初高位持仓，故均成本高于现价、获利盘偏低
```

**读法与自检**

| 指标 | 含义 | 性质 |
|------|------|------|
| `profit_ratio` | 成本**不高于现价**的模型筹码占比（包含保本筹码，不代表真实账户获利比例） | **硬约束**：必在 [0,1] |
| `avg_cost` | 加权平均持仓成本 | **硬约束**：必落在网格最低~最高之间 |
| `cost_90` / `cost_70` | 5%~95% / 15%~85% 分位价格区间 | **硬约束**：`cost_90` 必包含 `cost_70` |
| `concentration_*` | `(高-低)/(高+低)`，越小越集中 | 在分位价格为正且指标有限时，90% 集中度大于或等于 70%（浮点比较留容差） |
| `peak_price` | 筹码最密集的价位（套牢/支撑区） | **启发式**：通常落在 `cost_90` 内 |

> ⚠️ **下面两条是启发式，不是不变量，不要拿它们当断言去拒绝结果：**
> - 「`price < avg_cost` ⇔ `profit_ratio < 50%`」在**对称**分布下成立，但**右偏**分布里
>   均值被右尾拉高，现价可能同时低于均值、又高于中位数 —— 此时两者方向相反是正常的。
> - 「`peak_price` 落在 `cost_90` 内」绝大多数时候成立，但一个**窄而高的尖峰**若恰好位于
>   5% 分位之外，峰值就会落在区间外，这仍是合法结果。

> ⚠️ **这是推演不是实测持仓**。券商软件各家衰减系数与分布模型不同，数值不会完全一致，
> 看的是**形态与相对变化**（获利盘是在增加还是减少、筹码峰在上方还是下方），不是绝对值对齐。
> 输入必须用**前复权**价（`adjustflag="2"`），用不复权价跨除权日会把成本算错。

<a id="etf"></a>

### 4.7 ETF 份额 — 上交所按日归档 + 深交所当前快照（V3.9.0 新增）

ETF 份额变化是看资金申购赎回的直接口径。两所都是官方数据，单位**万份**。
**上交所**可按历史日期查询（实测 2023-01-03 仍有 446 只）；**深交所只提供最新一天**，`date` 与快照日期不符直接抛错，
历史份额需要自己按日留存（深交所注明 T 日晚为预估值、T+1 早为确认值）。两所的类别字段口径不同，没有硬并成一列。

实现位于 [scripts/etf_shares.py](../scripts/etf_shares.py)，依赖 requests、pandas：

```bash
python3 "<skill目录>/scripts/etf_shares.py" 2026-09-18 --exchange SH --output etf-sh.json
```

沪市保留单页完整性核验：实际条数必须等于来源 total，日期逐行一致；深市按 pagecount 完整翻页，每页日期/总页数/总条数必须稳定、预期页不得为空，最终数量必须一致，每页后 sleep(0.3)。两所份额必须是有限数值，缺字段、重复代码、快照变化均报错；空沪市日期和不匹配的深市日期仍为 ValueError，不把未发布/历史不可查询变成成功空表。

Python 返回完整 DataFrame，source/source_url/fetched_at 列保留；沪类别 etf_type 与深类别 fund_category 不合并，深市另保留 manager/listing_date。CLI 保存 columns、columns_index、dtypes、index、attrs 与矩阵 data，非有限/缺失/日期值显式标记；stdout 只给绝对路径、总行数和前三行。省略输出路径时当前目录生成新 JSON，已有路径不覆盖；输出发布沿用先临时文件、硬链接优先/独占复制兼容规则，等待成功退出再读取。查询/结构/保存异常非零退出，不输出部分快照。

Python 组合调用先初始化脚本路径：

<!-- v39-etf-shares:start -->
```python
from etf_shares import etf_shares, _etf_shares_sse, _etf_shares_szse
```
<!-- v39-etf-shares:end -->

```python
sh = etf_shares("2026-09-18", "SH")
sz = etf_shares("2026-09-18", "SZ")     # 若深交所最新快照不是这一天，会抛 ValueError 并告诉快照日期
```

---
