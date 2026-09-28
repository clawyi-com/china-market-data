<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 基础资料与历史状态

按任务读取：[财务快照](#finance)、[F10](#f10)、[当前基本面](#info)、[财报三表](#statements)、[历史估值](#valuation)、[上市退市信息](#basic)、[历史行业](#industry)、[当前 ST 名单](#st)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

<a id="finance"></a>

### 6.1 mootdx 财务快照（37字段季报数据）

使用 [tdx_client.py](../scripts/tdx_client.py)；先执行路径初始化后可用下方 Python 示例，或直接运行（[输出契约](market-data-details.md#mootdx)）：

```bash
python3 "<skill目录>/scripts/tdx_client.py" finance --params '{"symbol":"688017"}' --output finance.json
```

```python
from tdx_client import tdx_client

client = tdx_client(check='finance')  # 见 Prerequisites 的 tdx_client()；财务/F10 按 finance 验活（#52：K 线命令失效不影响这里）

# market: 0=深圳, 1=上海
fin = client.finance(symbol='688017')
# 返回 37 个字段的季报快照:
#   liutongguben(流通股本), zongguben(总股本)
#   eps(每股收益), bvps(每股净资产), roe(净资产收益率%)
#   profit(净利润), income(主营收入)
#   meigujingzichan(每股净资产), meigugongjijin(每股公积金)
#   meiguweifeipeili(每股未分配利润)
#   等37个季报财务字段
```

<a id="f10"></a>

### 6.2 mootdx F10（公司文本资料）

使用 [tdx_client.py](../scripts/tdx_client.py)；先执行路径初始化后可用下方 Python 示例，或直接运行（[输出契约](market-data-details.md#mootdx)）：

```bash
python3 "<skill目录>/scripts/tdx_client.py" F10C --params '{"symbol":"688017"}' --output f10-categories.json
```

```python
from tdx_client import tdx_client

client = tdx_client(check='finance')  # 见 Prerequisites 的 tdx_client()；财务/F10 按 finance 验活（#52：K 线命令失效不影响这里）

# 先用 F10C 列出服务器实际提供的类别，不要写死类别名：
# 请求不存在的类别时 mootdx 不报错，而是返回 {类别: 文本} 的 dict，按字符串切片会抛 TypeError。
for cat in client.F10C(symbol='688017'):
    text = client.F10(symbol='688017', name=cat['name'])
    print(f"=== {cat['name']} ===")
    print(text[:200] if text else "(空)")
```

> **⚠️ 2026-09 起 F10 只剩「最新提示」一类（#52 同一次服务端变化）：** 内置 10 台服务器 2026-09-20 逐台实测，
> `F10C` 只返回「最新提示」（内含 最新提示 / 互动问答 / 最新公告 / 最新报道 / 最新异动 / 大宗交易 / 融资融券 / 风险提示 8 个小节，
> 约 1.2 万字）；原来的公司概况、财务分析、股东研究、股本结构、资本运作、业内点评、行业分析、公司大事 8 类不再返回。
> 替代：行业 / 股本 / 市值 → §6.3；财务 → §6.1、§6.4；股东户数 → §4.3；增减持 → §14.3；回购 → §14.4；质押 → §14.5；
> 公司公告与大事 → §7.1 巨潮。

<a id="info"></a>

### 6.3 东财个股基本面（直连 push2 API）

实现位于 [scripts/company_data.py](../scripts/company_data.py)，仅需 requests：

```bash
python3 "<skill目录>/scripts/company_data.py" info 688017 --output company.json
```

用 em_market_code 判市场后拼接原始代码，使用纯 6 位，不自动剥离前后缀。字段原样保留：total_shares/float_shares 为股，mcap/float_mcap 为元，price 原值；list_date 使用 str 转换，缺失为空串、显式 None 会成为字符串 "None"。缺失 data 默认空对象，**data:null 仍报错**，不在迁移中改成空成功。--min-interval 至少 1 秒、本次结束恢复，共享东财 Session 与限流。

CLI 完整保存字典，stdout 返回路径与字段预览，不截断文件；省略输出时自动新建 JSON，已有路径不覆盖。错误非零退出，无成功文件；原接口未验证业务状态，默认值字典不代表数据有效。Python 组合调用先初始化脚本路径：

```python
from company_data import eastmoney_stock_info

# 用法
info = eastmoney_stock_info("688017")
print(info)  # 展示原始字段；计算前核验身份、缺失值、数值类型及单位，不把默认0当有效市值。
```

<a id="statements"></a>

### 6.4 新浪财报三表（资产负债表/利润表/现金流量表）

实现同样位于 [scripts/company_data.py](../scripts/company_data.py)：

```bash
python3 "<skill目录>/scripts/company_data.py" finance 600519 --report-type lrb --num 8 --output finance.json
```

report-type 原样传给 source，常用 fzb/lrb/llb；num 默认 8，既作为字符串请求参数，也在本地对倒序报告期键切片，0/负数保留原切片语义。证券代码先 get_prefix 后拼原输入，使用纯 6 位；不新增股票/ETF过滤或前后缀剥离。请求独立走新浪 requests.get，不使用东财限流参数。

返回报告期字符串及原始科目值，不将财报数字字符串转浮点。跳过空科目或 item_value=None；item_value=""/0 保留；同比只有 None/空串不附键，0/False 均保留。同名科目按后项覆盖前项，原样保留键冲突行为，不做科目合并。result/data/report_list 任层空按旧规则返回空列表，坏结构仍报错。

CLI 完整保存列表，stdout 只给总期数和前三期预览；文件保护与错误规则同上。原函数未验证 HTTP/业务成功，不能将空结果当成无财报的证明。Python 组合调用：

```python
from company_data import sina_financial_report

# 用法: 利润表
lrb = sina_financial_report("600519", "lrb")
for item in lrb[:3]:
    print(f"报告期: {item.get('报告期', '')} 净利润: {item.get('净利润', '')}")

# 用法: 资产负债表
fzb = sina_financial_report("600519", "fzb")

# 用法: 现金流量表
llb = sina_financial_report("600519", "llb")
```

---

<a id="valuation"></a>

### 6.5 baostock 估值历史 — PE/PB/PS/PCF + 换手率 + 停牌 + ST（V3.7.0 新增）

**核心价值：** §1.1 腾讯只给**当日**估值快照，本端点给**日频历史序列**（可回溯至 2016），
一次调用同时拿到四个我们此前完全没有的字段：**换手率**（筹码分布的必需输入）、
**停牌状态**、**ST 标记**、**历史估值**。

🔴 **北交所不支持**：baostock 服务端直接拒绝 4/8/92/920 号段，报
`10004011 股票代码未标识sh或sz`（2026-08-19 实测）。本实现在**登录前**就拦掉并抛 `ValueError`，
不浪费一次会话，也不会静默返回空表。

实现位于 [scripts/baostock_data.py](../scripts/baostock_data.py)，依赖 baostock、pandas：

```bash
python3 "<skill目录>/scripts/baostock_data.py" valuation 600519 2016-01-04 2026-08-18 --output valuation.json
```

保留先校验代码、再登录：str(code).zfill(6)，60/68/90→sh，00/30/20→sz，其余前两位拒绝（包括北交所、ETF和SH前缀）；这不是完整格式校验，600519.SH或短字符串bad仍可能通过原前两位判断，必须传正确纯6位代码。会话登录成功后无论查询成功/异常均logout；登录失败直接RuntimeError。_rs_to_df在迭代前检查错误码，按fields和行原样建表，不新增迭代中错误码检查。

估值请求fields固定、日频、不复权adjustflag=3；仅close/peTTM/pbMRQ/psTTM/pcfNcfTTM/turn做to_numeric(errors='coerce')，无效数字变缺失，不过滤停牌/ST，不改变日期/代码/status字符串，也不重新排序。CLI保存完整表格及dtype/index/attrs，stdout仅前三行；省略输出自动新建JSON、已有文件不覆盖。SDK登录/退出的stdout转发stderr，保持stdout JSON可解析；异常非零退出、无结果文件。

Python组合调用先初始化脚本路径，再导入（会话helper也供筹码取数与ST备用源使用）：

```python
from baostock_data import bs_session, _rs_to_df, _bs_code, baostock_valuation_history

# 用法
df = baostock_valuation_history("600519", "2016-01-04", "2026-08-18")
if df.empty:
    print("未取得历史估值记录，不能据此断言没有历史数据。")
else:
    print(len(df), "行", df.iloc[0]["date"], "→", df.iloc[-1]["date"])
print(df.tail(2)[["date", "close", "peTTM", "pbMRQ", "psTTM", "turn", "isST"]].to_string(index=False))
# 实测 2026-08-19：2581 行；2026-08-18 peTTM=19.93 pbMRQ=6.46 psTTM=9.37 turn=0.3098

# ST 标记实测有效：000004 在 2024-01 至今的 610 个交易日里有 276 天 isST=1
st = baostock_valuation_history("000004", "2024-01-01", "2026-08-18")
print("isST 分布:", st["isST"].value_counts().to_dict())     # {'0': 334, '1': 276}

# 停牌：tradestatus == "0"
print("停牌天数:", (df["tradestatus"] == "0").sum())
```

**字段说明**

| 字段 | 含义 | 备注 |
|------|------|------|
| `peTTM` `pbMRQ` `psTTM` `pcfNcfTTM` | 市盈率TTM / 市净率MRQ / 市销率TTM / 市现率TTM | 负值需按对应指标分母解释（盈利、净资产、收入或现金流），不能一概视为亏损或直接作低估排序 |
| `turn` | 换手率（**百分数**，0.31 = 0.31%） | §4.6 筹码分布的必需输入 |
| `tradestatus` | `1`=正常交易 `0`=停牌 | 算指标前应过滤掉停牌日 |
| `isST` | `1`=ST/*ST `0`=正常 | 历史逐日标记，可还原「当时是不是 ST」 |

---

<a id="basic"></a>

### 6.6 baostock 标的基本信息 — 上市日 / 退市日 / 状态（V3.7.0 新增）

**核心价值：** 提供**退市日期**的零鉴权入口。配合 §1.1 的 `is_stale` 僵尸报价标志，
可用于当前筛选核验上市状态；历史回测按当时的上市/退市日期确定标的范围，不能因今天已退市就剔除全部历史记录，以免引入幸存者偏差。

同一脚本提供基本信息命令：

```bash
python3 "<skill目录>/scripts/baostock_data.py" basic 600519 --output basic.json
```

使用相同代码校验与登录/退出。保留只取首行to_dict、空表返回{}；上市/退市日期、type/status不转型、不把空outDate改成None。CLI保存完整字典，终端返回完整字段预览。文件保护与错误规则同上。

```python
from baostock_data import baostock_stock_basic

# 用法
print(baostock_stock_basic("600519"))
# 实测：{'code': 'sh.600519', 'code_name': '贵州茅台', 'ipoDate': '2001-08-27',
#        'outDate': '', 'type': '1', 'status': '1'}   ← outDate 为空 = 仍在市
```

> 🔴 **原实测退市样本的除权除息缺失**（2026-08 交叉验证记录，非全部退市标的的覆盖证明）：通达信 `xdxr()` 即使传对
> `market=2` 也返回 0 条、东财历史快照同样没有、baostock 直接拒绝北交所代码。
> 对这些缺少除权除息记录的样本，不能保证复权一致；需按具体标的和日期核验因子覆盖，不能据此断言所有退市标的都无法复权。

---

<a id="industry"></a>

### 6.7 申万行业分类历史 — 消除行业前视偏差（V3.7.0 新增）

**核心价值：** §3.7 `industry_comparison()` 用东财，**只有当前归属**。做历史研究时用今天的
行业分类去套过去，是典型的**前视偏差**。本端点给出每只股票的**行业变迁史**。

⚠️ 申万官方只发布**代码**不发布中文名（名称表是另一份未公开发布）。
东财/通达信的行业名**不能**直接套——分类体系不同，代码不通用。

实现位于 [scripts/sw_industry.py](../scripts/sw_industry.py)，依赖 requests、pandas 及 Excel 读取引擎（旧式 .xls 用 xlrd，实际为 .xlsx 时用 openpyxl）：

```bash
python3 "<skill目录>/scripts/sw_industry.py" history --output sw-history.json
python3 "<skill目录>/scripts/sw_industry.py" as-of 000001 2016-01-01 --output sw-asof.json
```

两条 CLI 每次各下载一次原行业表；批量回测按下方 Python 例子先取一次，再复用 DataFrame 调用 as_of，避免每个日期重新下载。history 保留额外列，将四个已知中文列重命名；仅 code/start_date/industry_code 必须存在。代码和行业码 astype(str).zfill(6)，l1/l2 为前2位+0000、前4位+00；不补中文行业名。start_date 转日期，坏值变 NaT，再按代码/起始日排序、重置索引，不去重。

as_of 对代码补零，筛选 start_date≤查询日后取最后一行；等于调整日即使用新归属，无记录返回 None。**它不会自行排序传入的 DataFrame**，要复用 history 返回的升序表；重复调整日仍按原顺序选择，NaT 不匹配。不用当前行业归属替代历史，也不引入其他分类体系。

CLI history 全量保存 DataFrame 列/dtype/index/attrs/data；日期和缺失值显式编码，终端只预览前三行。as-of 保存完整字典或 JSON null（表示无归属），不将 None 误当请求失败。已有输出不覆盖，未指定输出自动新建；请求/读取/计算/保存异常非零退出、无结果文件。SSL 错误仍给原提示，不关闭证书验证；其他HTTP/网络异常原样传播。

Python 组合调用先初始化脚本路径：

```python
from sw_industry import sw_industry_history, sw_industry_as_of

# 用法
sw = sw_industry_history()
print(len(sw), "行 |", sw["code"].nunique(), "只标的 |",
      sw["l1_code"].nunique(), "个一级行业")
# 实测 2026-08-19：12893 行 | 5905 只 | 38 个一级 / 194 个二级 / 553 个三级

# 前视偏差验证：平安银行在不同时点属于不同行业
for d in ("2013-01-01", "2016-01-01", "2026-08-18"):
    print(d, sw_industry_as_of(sw, "000001", d))
# 2013-01-01 → 440101（一级 440000，自 1991-04-03）
# 2016-01-01 → 480101（一级 480000，自 2014-02-21）
# 2026-08-18 → 480301（一级 480000 / 二级 480300，自 2021-07-30）
```

> **典型用法：** 做行业轮动回测时，每个调仓日调用 `sw_industry_as_of()` 取**当时**的归属，
> 而不是用一张当前分类表贯穿全程。实测有标的历史上变更过 **10 次**行业。

<a id="st"></a>

### 6.8 ST / *ST 名单 — 全市场风险警示快照（V3.9.0 新增）

沪深走东财「风险警示板」过滤（含 B 股）；北交所不在这个过滤里，改为拉北交所全表按名称筛。
东财 push2 与 push2delay 都连不上时，退到 §6.5 baostock 证券列表按名称筛——**只有沪深、没有价格**，
`attrs['coverage']` 与 `attrs['fallback_reason']` 会写明。走 push2delay 时价格约有 15 分钟延迟（`source_url` 可看出走的哪个域）。
需要回测用的**历史** ST 状态，用 §6.5 `baostock_valuation_history()` 的 `isST` 列。

实现位于 [scripts/st_list.py](../scripts/st_list.py)，主源依赖 requests、pandas，实际退到备用源时另需 baostock。

```bash
python3 "<skill目录>/scripts/st_list.py" --output st-list.json
```

主域请求失败才尝试延迟域；两域的 requests 网络/HTTP 异常均失败才降级。非 JSON、业务错误、分页总数变化或不完整、空的沪深/北交所原集合、身份字段异常、重复代码均报错，不用部分名单冒充完整结果。北交所按名称包含 ST 筛选，沪深沿用风险警示板全集；名称以 * 开头标为 *ST，否则 ST。数值空值保留缺失。

备用源按 code_name="ST" 查询，只保留 type/status 均为字符串 "1" 且名称含 ST 的行；没有价格，coverage/fallback_reason 明确标出仅沪深。CLI 完整保存列/dtype/index/attrs/data（含来源和抓取时间），终端仅前三行预览；SDK 诊断转 stderr。异常非零退出，已有文件或符号链接不覆盖。历史状态仍使用 §6.5 isST，不将本快照用于历史回测。

<!-- v39-st-list:start -->
```python
from st_list import st_stock_list
```
<!-- v39-st-list:end -->

```python
st = st_stock_list()
print(st.attrs["coverage"], len(st), st.st_type.value_counts().to_dict())
```

---
