<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 组合估值与调研流程

按任务选择：[A 单票估值](#single)、[B 批量比较](#batch)、[C 主题研报](#reports)、[D 快速调研](#research)。`<skill目录>` 为技能根目录；Python例子先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)，各流程可分别导入运行。

<a id="single"></a>

### 流程 A: 单票组合估值

先在当前 Python 进程执行「Python 脚本路径初始化」，再导入组合入口；同花顺依赖由脚本加载。CLI 为 `scripts/valuation.py full <六位代码> --output <新文件.json>`；公式及输出规则见 [估值公式](valuation-formulas.md)。

保留原行为：先取腾讯报价，再取同花顺预测；按列名匹配「均值」「预测机构数」，首两行作为当年/次年，不自动按年份排序。代码须按原示例传纯六位；92/8 路由北交所、6/9 沪市、其余深市，未接入统一 ticker 路由。总市值取腾讯字段45（亿元），不新增僵尸报价检测。

组合函数与上方独立公式的边界不同：负 EPS 仍参与计算；EPS 缺失/零时前向 PE 为 None；增长为零时 cagr_pct 为 None；不满足 PE>30 且增长>0 时 digest_years 为0。EPS 解析错误只打印警告并保留已解析字段；未把部分结果改成统一失败。这些均为旧版行为，不能把0年当作数据完整的证明。

```python
from valuation import full_valuation

# 用法
result = full_valuation("688017")
print(result)
```

<a id="batch"></a>

### 流程 B: 批量估值对比

先执行「Python 脚本路径初始化」，再执行下列循环；每票异常仍独立打印并继续。

```python
from valuation import full_valuation

stocks = ["688017", "300308", "300476", "002463"]
for code in stocks:
    try:
        r = full_valuation(code)
        print(f"{r['name']}({code}): PE_fwd={r['pe_fwd']}x PEG={r['peg']} 消化={r['digest_years']}年 覆盖={r['analyst_count']}家")
    except Exception as e:
        print(f"{code}: 失败 - {e}")
```

<a id="reports"></a>

### 流程 C: 主题研报批量检索

先执行「Python 脚本路径初始化」，并按 §2.3 配置 iwencai API Key。

```python
from iwencai import iwencai_search
from eastmoney_reports import eastmoney_reports

# Step 1: iwencai 多 query 语义搜索
queries = [
    "人形机器人产业链深度 2026",
    "人形机器人减速器 丝杠",
    "特斯拉Optimus 国产供应链",
]
seen_uids = set()
all_articles = []
for q in queries:
    arts = iwencai_search(q, channel="report", size=50)
    for a in arts:
        uid = a.get("uid")
        # 没有稳定UID时保留记录，不能把所有缺UID的文章合并为一篇。
        if uid is not None and str(uid).strip():
            key = str(uid).strip()
            if key in seen_uids:
                continue
            seen_uids.add(key)
        all_articles.append(a)
print(f"保留 {len(all_articles)} 条研报记录（仅去重非空UID；缺UID记录可能仍重复）")

# Step 2: 东财补充同标的研报列表；本例不自动下载PDF，下载入口见§2.1。
for a in all_articles[:10]:
    stocks = a.get("stock_infos") or []
    for s in stocks:
        stock_code = s.get("code", "")
        if stock_code:
            em = eastmoney_reports(stock_code, max_pages=1)
            print(f"  {stock_code}: 东财 {len(em)} 篇")
```

<a id="research"></a>

### 流程 D: 新标的快速调研（V3.0 增强版）

先在同一个 Python 进程执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，然后执行下列完整示例；函数直接导入，无需逐章执行取数示例。示例中的日期固定为原示例日期，实际调研时须按任务日期替换。

```python
import io
from contextlib import redirect_stdout
from ths_eps_forecast import ths_eps_forecast
from tencent_quote import tencent_quote
from eastmoney_signals import (eastmoney_concept_blocks, eastmoney_fund_flow_minute,
                               stock_fund_flow_120d, dragon_tiger_board, lockup_expiry,
                               margin_trading, holder_num_change)


def checked_call(fn, *args, **kwargs):
    diagnostics = io.StringIO()
    with redirect_stdout(diagnostics):
        result = fn(*args, **kwargs)
    if "[WARN]" in diagnostics.getvalue():
        raise RuntimeError("取数失败，不能用部分结果继续判断：" + diagnostics.getvalue())
    if diagnostics.getvalue():
        print(diagnostics.getvalue(), end="")
    return result


code = "688017"
research_date = "2026-05-17"  # 示例日期；按实际研究任务替换，不代表下方实时数据的日期。
forecast = checked_call(ths_eps_forecast, code)
print("一致预期返回表（空表不证明没有机构覆盖）:")
print(forecast.to_string(index=False))
q = checked_call(tencent_quote, [code]).get(code)
print("报价原始字段:", q if q else "未取得报价")
print("使用前核对报价日期与is_stale；默认零值不等于有效零。")
print("板块返回记录:", checked_call(eastmoney_concept_blocks, code))

# 分钟资金流为时点记录，不累加；日资金流先核验日期/重复/覆盖，不能直接取末尾20条求和。
print("分钟资金流原始记录:", checked_call(eastmoney_fund_flow_minute, code))
print("日资金流原始记录:", checked_call(stock_fund_flow_120d, code))
# 如需指标，分别按§3.4和§4.5的说明与校验示例计算。
print("龙虎榜返回记录（不可直接当作独立上榜次数）:", checked_call(dragon_tiger_board, code, research_date))
print("解禁返回记录（检查区间及分页覆盖）:", checked_call(lockup_expiry, code, research_date))
print("融资融券返回记录（原单位/缺失值）:", checked_call(margin_trading, code, page_size=5))
print("股东户数返回记录（核验日期，不据此证明吸筹）:", checked_call(holder_num_change, code))
# 需要PE消化或PEG时，按流程A单独调用full并检查其警告、预测期及部分结果。
```

---

<a id="shared-helpers"></a>

## Python 公共 helper

仅在直接调用公共 helper 或核查其返回与错误行为时读取本节；上面的业务组合示例不需要先执行这些导入块。CLI 无需 Python 路径初始化。

### 东财数据中心统一查询（共用 helper）

龙虎榜/解禁/融资融券/大宗交易/股东户数/分红 共用同一 base URL：

会话、重试配置及节流时间戳集中在 [scripts/_eastmoney.py](../scripts/_eastmoney.py)。先执行 [Python 脚本路径初始化](../SKILL.md#python-脚本路径初始化)，再导入；不必读取源码：

```python
import time
import random
import requests
from typing import Optional
import _eastmoney
from _eastmoney import UA, DATACENTER_URL, em_get, eastmoney_datacenter

# 批量任务如需进一步降速，修改模块配置（同进程所有东财调用共享）：
# _eastmoney.EM_MIN_INTERVAL = 1.5
```

默认请求间隔 1 秒；未到间隔时再加 0.1–0.5 秒抖动，时间戳在请求结束时更新（异常也更新）。Session 复用并设置 UA；连接/429/500/502/503/504 最多 3 次重试，backoff_factor=0.6，仅 GET，403 不重试；旧 urllib3 不支持配置时沿用无重试降级。

按旧版方式串行调用；这不是跨进程限流器，也没有线程锁，不能并发启动多个 CLI 来规避间隔。同进程通过 `import _eastmoney` 共享状态；不要 `from _eastmoney import EM_MIN_INTERVAL` 后仅修改本地变量，那不会改变模块配置。`eastmoney_datacenter()` 保留只查询第一页及失败载荷可能返回 [] 的旧行为；需要严格分页/错误识别的端点仍用下方 `_em_datacenter_strict()`。


### V3.9.0 共用 helper（§1.2 腾讯 K 线起的所有 V3.9.0 / V3.10.0 新端点都依赖它）

业务脚本自动导入所需 helper；仅在直接组合公共函数时执行本导入块，无需按顺序执行其他章节。V3.9.0 新端点统一返回 DataFrame，
末尾附 `source` / `source_url` / `fetched_at` 三列。**「确实没有数据」与「接口坏了」分开处理**：前者返回空表或抛
`ValueError`（非交易日、日期太早），后者抛 `RuntimeError`（结构改变、重复行、全市场 0 行），不把错误页当空结果。
本组共用 helper 的东财请求经 `em_get()` 限流；`_em_datacenter_strict()` 与旧 `eastmoney_datacenter()` 的区别是会翻页、并把错误码抛出来。

<!-- v39-helpers:start -->
```python
import functools
import math
import re
from datetime import date as _date_cls, datetime, timezone

import pandas as pd
import requests
from _market_common import (
    V39_UA, _v39_http, _v39_json, _v39_date, _v39_src_date,
    _v39_num, _v39_req_num, _v39_contract, _v39_frame,
)


from _market_common import _v39_rows


from _market_common import _v39_labels


from _market_common import _v39_count


from _eastmoney import _em_datacenter_strict


from _market_common import _em_day
```
<!-- v39-helpers:end -->

---
