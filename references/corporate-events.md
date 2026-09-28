<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 公司事件与申购日历

查询§14.1–§14.6时读取本文；六个CLI及Python导入见 [脚本入口](#commands)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

公司层面的事件型数据，全部来自东财数据中心（经 `em_get()` 限流，股权质押数据的原始来源是中国结算每周统计）。
各入口按各自排序字段取最多 `limit` 条（上限5000），不能统一理解为公告日顺序：回购按更新字段UPD，IPO按申购日，质押按统计日或指定统计日的质押比例排序。无代码时通常查询全市场，质押另有最近统计日规则。部分收窄条件允许空表，仅表示此次查询未返回匹配记录；不证明现实中不存在事件。具体空结果规则见下文。
`code` 只收个股：`sh000001` / `000001.XSHG` 这类显式沪市指数写法直接抛 `ValueError`（归一化成 000001 会查到平安银行）。
翻页排序字段都能唯一确定一行，并逐页检查重复（实测只按质押比例排序时 2212 行里重复 1 行、漏 1 行）。

| 函数 | 数据 | 单位 / 口径 |
|---|---|---|
| `earnings_forecast(code=None, report_date=None, limit=500)` | 业绩预告 | 一次预告按指标拆多行（归母净利 / 扣非 / 营收…）；金额元，变动为同比 % |
| `institution_survey(code=None, start=None, end=None, detail=False, limit=500)` | 机构调研 | `detail=False` 一次调研一行 + 机构家数；`True` 一家机构一行 |
| `holder_trades(code=None, direction=None, start=None, end=None, limit=500)` | 股东增减持 | 万股；变动股数带符号（减持为负）；占总股本 / 流通股 % |
| `share_buyback(code=None, progress=None, limit=500)` | 股票回购 | 方案上下限与已实施部分；股、元、占总股本 % |
| `equity_pledge(code=None, date=None, limit=5000)` | 股权质押比例 | 中国结算每周统计（通常周五）；万股、万元；**只覆盖沪深**，北交所代码抛错 |
| `ipo_calendar(limit=100)` | 新股申购日历 | 含尚未申购的排期；中签率 %、首日涨幅 % |

<a id="commands"></a>

### 14.1–14.6 脚本入口

实现集中在 [scripts/events_data.py](../scripts/events_data.py)，依赖 requests、pandas 及随附公共模块，无需读取实现：

```bash
python3 "<skill目录>/scripts/events_data.py" forecast --report-date 2026-09-30 --limit 30 --output forecast.json
python3 "<skill目录>/scripts/events_data.py" survey --code 688062 --detail --output survey.json
python3 "<skill目录>/scripts/events_data.py" holder-trades --direction 减持 --start 2026-09-01 --output trades.json
python3 "<skill目录>/scripts/events_data.py" buyback --progress 实施中 --output buyback.json
python3 "<skill目录>/scripts/events_data.py" pledge --output pledge.json
python3 "<skill目录>/scripts/events_data.py" ipo --limit 30 --output ipo.json
```

CLI 保存完整 DataFrame（列/dtype/索引/attrs/来源及全部行），终端仅预览前三行；已有输出不覆盖，异常非零退出且不保存。limit 默认值保持上表；不自动扩大上限。按旧版串行调用并共享东财限流，不能并发启动多个 CLI 来规避间隔。Python 组合调用先执行「Python 脚本路径初始化」，再导入下面函数。

空结果细节：holder-trades 仅给 direction 仍按全市场空结果报错；buyback 给 progress 已算收窄条件，可返回空表；pledge 指定统计日无行仍抛 ValueError。机构调研按公告日筛选，不按接待日；所有条件都在返回后继续核对。

<!-- v39-events:start -->
```python
from events_data import (
    earnings_forecast, institution_survey, holder_trades,
    share_buyback, equity_pledge, ipo_calendar,
)
```
<!-- v39-events:end -->

```python
fc = earnings_forecast(report_date="2026-09-30")
sv = institution_survey("688062", detail=True)
cut = holder_trades(direction="减持", start="2026-09-01")
bb = share_buyback(progress="实施中")
pl = equity_pledge()                                 # 最近一个统计日全市场
ipo = ipo_calendar(limit=30)
```

---
