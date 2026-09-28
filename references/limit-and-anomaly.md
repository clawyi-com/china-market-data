<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 涨跌停、情绪与监控异动

按任务读取：[四池](#pools)、[涨停原因](#reasons)、[情绪指标](#sentiment)、[重点监控](#monitor)、[日内异动](#anomaly)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

> 连板梯队、炸板率、晋级率、涨停原因题材——打板与题材跟踪的高频需求（#23 / #15）。东财四池走 `push2ex.eastmoney.com`（与现有 push2 同源，已纳入 `em_get()` 限流）；涨停原因题材增强用同花顺。**全部免登录、零鉴权。**

<a id="pools"></a>

### 8.1 东财涨停板池 — 涨停 / 炸板 / 跌停 / 昨日涨停

实现位于 [scripts/limit_pools.py](../scripts/limit_pools.py)，依赖 requests；四池使用同一个脚本入口和共享东财限流：

```bash
python3 "<skill目录>/scripts/limit_pools.py" zt 20260925 --output zt.json
python3 "<skill目录>/scripts/limit_pools.py" zb 20260925 --output zb.json
python3 "<skill目录>/scripts/limit_pools.py" dt 20260925 --output dt.json
python3 "<skill目录>/scripts/limit_pools.py" yzt 20260925 --output yzt.json
```

保留原服务端排序与单次 pagesize=10000，不自动翻页、不再本地排序。价格÷1000；涨幅/换手等按原字段 round(...,2)，金额和市值为元；HHMMSS 补零后格式化，不新增有效时间检查；N天M板缺值使用 ?。原函数请求/JSON 异常打印 WARN 并返回 []，data/pool 为空也返回 []，坏行转换仍抛异常。CLI 若捕获 WARN 则非零退出且不落盘，避免将请求失败当正常空池；无 WARN 的空池仍成功保存，不能据此证明上游业务有效。完整 JSON 文件保留全部记录，终端仅预览前三条，已有路径不覆盖。

Python 组合调用先初始化脚本路径：

```python
from limit_pools import em_zt_pool, em_zb_pool, em_dt_pool, em_yzt_pool

# 用法
zt = em_zt_pool("20260626")
print(f"查询日 20260626 返回涨停样本 {len(zt)} 只（空样本不证明当日无涨停）")
for s in zt[:3]:
    print(f"  {s['name']} {s['zt_stat']} 封板{s['seal_fund']/1e8:.2f}亿 {s['industry']}")
```

> **坑：** ① 价格字段 `price`/`limit_price` 已 ÷1000（原始值是 ×1000 整数）。② 四池使用不同端点（getTopicZTPool / getTopicZBPool / getTopicDTPool / getYesterdayZTPool）和字段映射；排序分别为涨停/炸板=`fbt:asc`、跌停=`fund:asc`、昨涨停=`zs:desc`，`dpt` 都是 `wz.ztzt`。③ `date` 必须传交易日，非交易日 `data` 返回 null。④ 金额单位均为**元**。

<a id="reasons"></a>

### 8.2 同花顺涨停揭秘 — 涨停原因题材 + 封板成功率 + 板型

复用 [scripts/limit_pools.py](../scripts/limit_pools.py)：

```bash
python3 "<skill目录>/scripts/limit_pools.py" ths 20260925 --output ths-limit.json
```

原参数 page=1、limit=200、板块过滤与内部 field ID 不变，不自动翻页。价格/百分比/封板率/金额原值不强制转换；open_num 假值变 0，first_time 按本机时区解析 Unix 秒。请求失败原生函数 WARN+[]，CLI 对 WARN 报错且不保存；行字段/时间转换错误仍抛出。

```python
from limit_pools import ths_limit_up_pool

# 用法: 涨停原因题材归因
for s in ths_limit_up_pool("20260626")[:5]:
    print(f"  {s['name']} {s['high_days']} | {s['reason']} | 封板率{s['seal_rate']}")
```

> **坑：** `first_limit_up_time` 是 **Unix 秒时间戳**（要 `datetime.fromtimestamp`），不是 HHMMSS。`field` 那串是同花顺内部字段 ID，照抄即可。`filter=HS,GEM2STAR` 控制板块范围（沪深主板 + 创业板 + 科创板）。

<a id="sentiment"></a>

### 8.3 打板情绪速算 — 炸板率 / 连板高度 / 连板梯队

复用 [scripts/limit_pools.py](../scripts/limit_pools.py)：

```bash
python3 "<skill目录>/scripts/limit_pools.py" sentiment 20260925 --output sentiment.json
```

依次取涨停、炸板、跌停；炸板率=炸板数/(涨停数+炸板数)×100，四舍五入一位，分母零时为 0。最高连板空时为 0，梯队按板数升序计数。原生 ladder 保持整数键字典；CLI 为保留键类型与顺序，将 ladder 编码为 `{"$map": [[板数, 家数], ...]}`，不是字符串键。任何一池产生 WARN，CLI 失败不保存部分情绪指标；原 Python 函数仍保持 WARN 后按空池计算的行为。情绪结果完整预览和保存。

```python
import io
from contextlib import redirect_stdout
from limit_pools import limit_up_sentiment

# 原函数会把请求失败当空池继续计算；组合调用必须检查诊断。
diagnostics = io.StringIO()
with redirect_stdout(diagnostics):
    s = limit_up_sentiment("20260626")
if "[WARN]" in diagnostics.getvalue():
    raise RuntimeError("行情池请求失败，不能使用部分情绪指标：" + diagnostics.getvalue())
print(f"查询日 {s['date']} 返回样本：涨停{s['zt_count']} 炸板{s['zb_count']} 跌停{s['dt_count']}")
if s['zt_count'] + s['zb_count']:
    print(f"返回样本炸板率 {s['break_rate']}%（需另核验三池的日期、完整性与时点一致性）")
else:
    print("炸板率不可判定：分母为0；不能把脚本默认0解读为有效0%。")
if s['zt_count']:
    print(f"样本最高{s['max_height']}连板，梯队: {s['ladder']}")
else:
    print("未取得涨停样本，不能确认连板高度与梯队。")
```

> 晋级率须先确认“昨涨停集合”和“今日仍涨停集合”的日期、覆盖及观察时点，再按证券代码匹配计数。不能统一用 `pct >= 9.8` 代替涨停身份；分母为空或覆盖无法核实时不输出晋级率。盘中观察不称为收盘晋级率。

<a id="monitor"></a>

### 8.4 东财重点监控池（V3.6.0 新增 · #15）

东财 App「重点监控」名单：被交易所风险警示 / 重点监控的标的及其**生效时间窗**。零鉴权静态 JSON，全量返回不分页。

实现复用 [scripts/limit_pools.py](../scripts/limit_pools.py)，依赖 requests：

```bash
python3 "<skill目录>/scripts/limit_pools.py" monitor --output active-monitor.json
python3 "<skill目录>/scripts/limit_pools.py" monitor --all --output all-monitor.json
```

默认筛选北京时间今天处于 start≤today≤end 的记录，首末日均包含；--all 保留过期/未生效记录。日期仍按源字符串比较，不新增格式清洗。市场字段转大写后 1/0/B 对应 SH/SZ/BJ，未知保留 ?原值，不猜成深市。返回全量列表，CLI 保存全部、预览前三条；源返回 null/空仍按原行为得到 []，请求/解析异常报错，不关闭证书校验。

Python 组合调用先初始化脚本路径：

```python
from limit_pools import cn_today, em_stock_monitor

# 用法
pool = em_stock_monitor()
print(f"返回当前重点监控样本 {len(pool)} 只（空列表不证明完整名单为空）")
for s in pool[:5]:
    print(f"  {s['code']} {s['name']}({s['market']}) 监控期 {s['start']}~{s['end']}")
```

| 字段 | 含义 |
|------|------|
| STKCODE / STKNAME | 代码 / 名称 |
| MARKET | `"1"`=沪市，`"0"`=深市，**`"B"`=北交所**（三值且含字母，别当 0/1 二值处理） |
| VALIDATESTARTDATE / VALIDATEENDDATE | 监控生效起 / 止日（通常 14 天窗口） |
| LINK_URL | 东财 App 内详情页（可空） |

<a id="anomaly"></a>

### 8.5 东财日内异动池 — 严重异常波动（V3.6.0 新增 · #15）

交易所「严重异常波动」口径的异动标的：连续 N 日同向异动、累计偏离值触发阈值等。两个端点同源，**零鉴权，但必须带 `team=h5` 等固定参数**，否则返回 `{"result":1001,"msg":"unknow team"}`。

实现复用 [scripts/limit_pools.py](../scripts/limit_pools.py)：

```bash
python3 "<skill目录>/scripts/limit_pools.py" anomaly --page-size 200 --page-no 1 --output anomaly.json
python3 "<skill目录>/scripts/limit_pools.py" anomaly-count --page-size 50 --page-no 1 --sort-key "" --sort-dir "" --output anomaly-count.json
```

固定 H5 参数保持原值；pageSize/pageNo 转字符串，只取指定页，不自动翻页。返回 date/pages/items，全量当前页保存，终端只预览前三项但保留 date/pages。result!=0（含缺失）报错；data 缺失或假值仍按原行为给空 items，不把请求错误当正常空数据。

代码 4/8/92 开头或 board==8 优先识别 BJ，否则仅整数市场号 1 为 SH，其余 SZ。明细 s==6 且规则 e 为4/5/6/7时用40/50/60/70加严说明；未知规则保留原码与提示。is_today 仅 o==2 为 False。统计端点的 t 是次数，价格/涨幅/偏离值保持原值；不把它当明细端点的涨幅目标。非交易时段可能是上一交易日，不能强制覆盖为今天。

两类命令复用全量JSON保存和不覆盖策略；异常非零退出、不保存。原有监控池交叉示例保留如下。

```python
from limit_pools import em_price_anomaly, em_price_anomaly_count, em_stock_monitor

# 用法
a = em_price_anomaly(page_size=200)
print(f"{a['date']} 日内异动 {len(a['items'])} 条")
for s in a["items"][:5]:
    print(f"  {s['code']} {s['name']} {s['change_pct']}% 偏离{s['deviation']}%/{s['days']}日 | {s['rule']}")

c = em_price_anomaly_count(page_size=50)
for s in c["items"][:5]:
    print(f"  {s['code']} {s['name']} {s['price']}元 {s['change_pct']}% 异动{s['times']}次")

# 与重点监控池交叉：只表示两类记录重合，不是已验证的风险等级；先核对双方日期。
monitor_codes = {x["code"] for x in em_stock_monitor()}
hot = [s for s in a["items"] if s["code"] in monitor_codes]
print(f"异动且在监控池: {[(s['code'], s['name']) for s in hot]}")
```

> **字段来源说明：** `p`/`a`（最新价、涨跌幅）已与腾讯行情逐条核对（3/3 完全一致）；`m`/`c`/`n`/`e`/`x`/`d`/`o` 的语义取自东财前端 `formatNewData` 的字段映射（`x`→DEVUATION_VALUE、`d`→MAX_DAYS、`a`→CHANGE_RATE、`o`→IS_HAPPEN）。
>
> **两端点同名字母含义不同：** `list` 的 `t` 是涨跌幅目标值（浮点），`count` 的 `t` 是异动次数（整数）——不要跨端点复用解析逻辑。
>
> **`open` 字段**为盘口开闭标志；`date` 为交易日（`YYYYMMDD`）。非交易时段返回上一交易日数据，属正常。

---
