<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 宏观数据、利率与事件日历

按任务读取：[社融](#financing)、[PMI](#pmi)、[收益率曲线](#yield)、[FR/FDR](#repo)、[LPR](#lpr)、[宏观日历](#calendar)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

> 本层混合多种频率：社融/PMI为月度指标，收益率曲线/回购利率为日频记录，LPR需区分历史机制，宏观日历为事件时间。各入口无需 Key。
> 统计期、记录日期和实际发布日期不是同一概念；发布日期及变更以来源公告为准，不用固定日期推断数据已发布。
> 社融会丢弃总量为空的月份，PMI取最新发布页；不据月份标签推断当时已知信息或固定领先关系。
>
> **社融支持范围：2021 年起**（原2026-08-19实测记录覆盖2021~2026六年；返回已发布月份且不跨年，当年不足12行，见下方7行示例）。
> 2020 及更早是旧版式——表头与项目名合并在一个单元格、且附表带「2017 年以来」的历史区，
> 传入这些年份会**抛错而不是返回可疑数据**。

<a id="financing"></a>

### 11.1 人民银行 — 社会融资规模增量

**核心价值：** 获取官方社会融资规模增量及分项，中英双语 12 列；不将其直接等同于央行流动性投放或市场涨跌原因。

**链路是三级跳**（索引 → 年份页 → 专题页 → xls 附件），任何一级结构变更都会 fail-fast 抛错，不静默返回空。

实现位于 [scripts/macro_data.py](../scripts/macro_data.py)，依赖 requests、pandas 和 Excel 引擎（xls 用 xlrd，xlsx 用 openpyxl）：

```bash
python3 "<skill目录>/scripts/macro_data.py" social-financing --output social-financing.json
python3 "<skill目录>/scripts/macro_data.py" social-financing --year 2024 --output social-financing-2024.json
```

沿原链路索引→年份页→专题→第一个xls/xlsx附件；未指定年份取索引最大年份。缺链接、缺月份表头或无有效数据均报错，未知年份ValueError。附件原请求只取content，不新增HTTP状态检查；Excel错误仍传播。

表头“月份”行后跳过3行，取前12列，数值转失败为NaN。月份按单元格解析：2026.01为1月、2026.1为10月；不按行序编月份。保留目标年、丢社融总量为空的未发布行，重置索引，不去重或排序；所有金额为亿元。支持2021年起的版式，旧年份不静默套用。CLI完整保存DataFrame列/dtype/index/attrs/data，日期/缺失值显式编码，仅预览前三行，已有路径不覆盖，异常非零退出不保存。

Python组合调用先初始化脚本路径：

```python
from macro_data import pboc_social_financing

# 用法
df = pboc_social_financing()          # 最新年（只含已发布月份）
print(df[["month", "afre_total", "rmb_loans", "government_bonds"]].to_string(index=False))
# 实测 2026-08-19：返回 7 行（2026-01 ~ 2026-07），2026-01 社融增量 72,185 亿
# 全部 12 列：month / afre_total(社融增量) / rmb_loans(人民币贷款) / fx_loans(外币贷款) /
#   entrusted_loans(委托贷款) / trust_loans(信托贷款) /
#   undiscounted_bankers_acceptance(未贴现银行承兑汇票) / corporate_bonds(企业债券) /
#   government_bonds(政府债券) / equity_financing(非金融企业境内股票融资) /
#   abs_by_depository(存款类金融机构ABS) / loans_written_off(贷款核销)

hist = pboc_social_financing(2024)    # 指定年份
import math
# 必须恰好包含目标年12个不同月份，且总量均为有限数值，才标为全年合计。
expected = {f"2024-{month:02d}" for month in range(1, 13)}
months = hist["month"].astype(str).tolist()
values = hist["afre_total"].tolist()
valid = all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)
if len(months) == 12 and set(months) == expected and valid:
    print("12个月, 全年社融增量", f"{sum(values):,.0f}", "亿元（按返回数据口径）")
else:
    print("未取得完整且有效的2024年12个月数据，不能计算全年合计。")
# 实测：12 个月, 322,588 亿元
```

---

<a id="pmi"></a>

### 11.2 国家统计局 — 采购经理指数 PMI

**核心价值：** 获取制造业、非制造业及综合PMI最新发布值；指标按源指数值保留，不推断固定领先季度。

实现复用 [scripts/macro_data.py](../scripts/macro_data.py)：

```bash
python3 "<skill目录>/scripts/macro_data.py" pmi --output pmi.json
```

从最新发布索引取第一个标题包含“采购经理指数”的链接，保留原相对URL拼接规则，不额外按日期排序。剔除script/style与HTML标签后删除全部空白，兼容全角括号内空格。大中小企业支持全合并、半拆和全拆三种原措辞；分档缺失为None，制造业/非制造业/综合三个主指标任何一个缺失均报错。标题没有年月时period仍为None；指标保留49.2等指数值，不除100。CLI完整字典保存与预览，已有路径不覆盖，异常非零退出且不保存。共用宏观模块需要requests、pandas，PMI本身不读Excel、不需要Excel引擎。

Python组合调用先初始化脚本路径：

```python
from macro_data import nbs_pmi

# 用法
p = nbs_pmi()
print(p["period"], "制造业", p["manufacturing_pmi"], "非制造业", p["non_manufacturing_pmi"])
# 实测 2026-08-19：2026-07 制造业 49.2 / 非制造业 49.0 / 综合 49.3
#                  大型 49.5 / 中型 49.7 / 小型 47.4（均在荣枯线下）
```

> **解读边界：** 本入口只取最新发布页，不自行构建连续月份序列；判断趋势或企业规模差异需另核对多期同口径数据，不能从单次返回推断连续趋势。

<a id="yield"></a>

### 11.3 中债收益率曲线 — 国债 / 商业银行 AAA / 中短票 AAA（V3.9.0 新增）

中央结算公司官方数据，3 月到 30 年共 8 档期限，单位 %。`curve='all'` 一次返回三条曲线（按 `curve` 列区分）。
官网单次查询超过 1 年会静默返回 0 行，本函数按 360 天切片；一周以上的切片 0 行视为接口口径变化并抛错。
中短期票据曲线没有 30 年，该列为 None。三条曲线的起点不同（国债 2006-03-01、中短票 2006-12-25、商业银行 2009-12-24，2026-09-20 实测），
start 更早时从起点开始取；每段返回的日期必须落在该段内，`all` 模式按起点核对**返回的每一天**该有的曲线是否齐全，不齐抛 `RuntimeError`。
中债不公布债券市场交易日历、页面也没有总条数，整天缺失无法判定（只有整段 7 天以上 0 行才报错）。

实现复用 [scripts/macro_data.py](../scripts/macro_data.py)，依赖 requests、pandas：

```bash
python3 "<skill目录>/scripts/macro_data.py" yield-curve 2026-09-01 --end 2026-09-25 --curve all --output yields.json
```

end省略仍用本机date.today，start/end经原日期helper转换；最早起点、360天切片、每段日期/曲线完整性和重复检查保持不变。表头必须逐列相同；HTML注释去除，取最后表格；数值沿原helper解析，空值保留缺失，不除100。结果按日期和曲线排序，source_url为最后响应URL。CLI保存完整DataFrame列/dtype/index/attrs/data，只预览前三行，已有输出不覆盖，异常非零退出不保存。整天缺失仍需另备交易日历核对，不能把本接口检查称为交易日历完整性认证。

Python组合调用先初始化脚本路径：

<!-- v39-chinabond:start -->
```python
from macro_data import chinabond_yield_curve
```
<!-- v39-chinabond:end -->

<a id="repo"></a>

### 11.4 银行间回购定盘利率 FR / FDR（V3.9.0 新增）

中国货币网（外汇交易中心）官方 CSV：`kind='FR'` 全市场回购定盘利率 FR001 / FR007 / FR014（约近 3 年），
`kind='FDR'` 银银间 FDR001 / FDR007 / FDR014（约近 1 年）。单位 %。看资金面松紧的日频指标。

实现复用 [scripts/macro_data.py](../scripts/macro_data.py)，依赖requests、pandas：

```bash
python3 "<skill目录>/scripts/macro_data.py" repo-fixing --kind FR --output fr.json
python3 "<skill目录>/scripts/macro_data.py" repo-fixing --kind FDR --output fdr.json
```

kind按原str().upper()处理。CSV按UTF-8 BOM解码，跳过空行，每行必须9列且中间5列为空，三档利率均必需；缺失/非有限/无法解析的数值报错，不置零。按日期升序、重置索引，重复日期与全空报错。利率为百分数原值，不除100。CLI完整保存DataFrame及来源元信息，只预览前三行，已有路径不覆盖，异常不保存。可取历史范围由源CSV决定，不新增日期筛选或历史完整性认证。

<!-- v39-repo-fixing:start -->
```python
from macro_data import repo_fixing_rates
```
<!-- v39-repo-fixing:end -->

<a id="lpr"></a>

### 11.5 LPR 贷款市场报价利率全历史（V3.9.0 新增）

东财数据中心。2013-10 至 2019-08 为旧机制的逐日 1 年期 LPR（`lpr_5y` 为 None，5 年期 2019-08-20 才设立）；
改革后的报价日以源记录及公告为准，不写死每月某日。同一报表混有旧贷款基准利率行；具体过滤按下文LPR1Y字段规则执行，不是按年份删除。

实现复用 [scripts/macro_data.py](../scripts/macro_data.py)，严格分页函数位于现有东财模块 [_eastmoney.py](../scripts/_eastmoney.py)：

```bash
python3 "<skill目录>/scripts/macro_data.py" lpr --output lpr-history.json
```

按TRADE_DATE升序查询RPTA_WEB_RATE，默认每页500条、最多5000条；仅来源count超过上限时截断，否则核对总条数。不是无限历史接口，需超过5000条时通过Python调整公共查询上限另行处理。仅过滤LPR1Y为None/缺失的基准利率行，不按年份删行；LPR1Y空串/横线/非有限或坏值报错。LPR5Y可缺失，2019年前保留一档。日期原值str后截前10位再解析，收益率保留百分数，结果不新增排序或去重。

CLI完整保存DataFrame与来源，前三行预览，已有路径不覆盖、异常不保存。分页途中9201、空页、非末页不满、pages/count变化及条数不符均报错；只有首屏9201或合法空结果可由公共函数返回[]，LPR最终无有效行仍报错。

<!-- v39-lpr:start -->
```python
from macro_data import lpr_history
```
<!-- v39-lpr:end -->

<a id="calendar"></a>

### 11.6 全球宏观日历（华尔街见闻）（V3.9.0 新增）

经济数据的公布值 / 预期 / 前值 + 重要事件（央行议息等）。区间含两端最多 92 天，接口单次只允许一周，本函数按 7 天切片。
`importance` 1–4，数字越大越重要（实测 4 = 工业增加值、社零这类头条数据）；`kind`：`data` 经济数据 / `event` 事件。
已开始的整周返回 0 条说明接口异常，抛 `RuntimeError`；单日、周末或三周以后的日期可能确实没有条目，整个区间为空时抛 `ValueError`。

实现复用 [scripts/macro_data.py](../scripts/macro_data.py)：

```bash
python3 "<skill目录>/scripts/macro_data.py" calendar 2026-09-21 --end 2026-09-25 --country 中国 --min-importance 3 --output calendar.json
```

不是游标分页：按北京时间每天00:00:00至末日23:59:59切成7天窗口，end默认start后6天。保持最多92天、窗口内时间/重要度/id检查、重复id拒绝；过滤前先验证所有原始条目，不用country掩盖坏记录。FD/FE映射data/event，未知类型原样保留；actual/forecast/previous/revised仅空串和None转缺失，数值0、字符串0保留，unit/period仍按原假值转None。按分钟时间字符串排序，country精确匹配、importance阈值过滤；筛完为空ValueError。source_url仍是最后响应URL。

CLI保存完整DataFrame含来源与元信息，前三行预览，已有输出不覆盖；源错误/区间错误/空结果均非零退出且不保存。保留下面组合用法：

<!-- v39-macro-calendar:start -->
```python
from macro_data import macro_calendar
```
<!-- v39-macro-calendar:end -->

```python
curve = chinabond_yield_curve("2026-01-01", curve="treasury")
fr = repo_fixing_rates("FR")
lpr = lpr_history()
cal = macro_calendar("2026-09-21", country="中国", min_importance=3)
```

---
