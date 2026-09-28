<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 可转债条款、上市状态与报价

查询§15.1时读取本文，CLI及Python导入见 [脚本入口](#bonds)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

东财数据中心可转债全表：基本条款（评级、规模、转股起始日、到期日）+ 最新转股价 / 债价 / 正股价 / 转股价值 / 溢价率。
行情字段直接采用东财返回值；本函数不核验报价时间或停牌状态，可能缺失或陈旧，不能保证每条均为当前可成交报价。
`status`：`upcoming` 已发行未上市 / `listed` 按日期/市场字段判断已上市（不证明当前正在交易） / `delisted` 已摘牌（`include_delisted=True` 才返回）/ `unknown` 判断不了（不猜）。
东财在赎回 / 到期公告后会提前填上摘牌日，摘牌日之前仍算 `listed`；上市日也可能提前填上，上市日之前算 `upcoming`（按北京时间判断）。
退市板块的转债（404001–404005，如 404005 普利退债）东财不填上市日和摘牌日，按交易市场 `STAS00` 判为 `delisted`。

<a id="bonds"></a>

### 15.1 脚本入口

复用 [scripts/events_data.py](../scripts/events_data.py) 的东财请求与完整输出入口：

```bash
python3 "<skill目录>/scripts/events_data.py" bonds --output bonds.json
python3 "<skill目录>/scripts/events_data.py" bonds --include-delisted --output all-bonds.json
```

每页500条、最多20000条，保持旧版按申购日/代码排序。先取得完整源再按北京时间判断状态、过滤已摘牌；未知状态保留。源空报错，过滤后空仍可返回有列结构的空表，重复代码检查针对过滤后的结果。quoteColumns/quoteType原样请求，价格/转股价值/溢价率直接采用源字段，不重新计算或交叉核验上述公式。

CLI完整保存全部行、列/dtype/索引/attrs/来源，终端仅预览三行；已有输出不覆盖，异常非零退出且不保存。Python调用先执行「Python 脚本路径初始化」。

<!-- v39-cb:start -->
```python
from events_data import convertible_bonds
```
<!-- v39-cb:end -->

```python
import math
import pandas as pd

cb = convertible_bonds()
# 仅演示源字段筛选，不证明低估或当前可成交；需另核验行情时点、停牌及转股条件。
values = cb[["bond_price", "convert_value", "premium_pct"]].apply(pd.to_numeric, errors="coerce")
valid = values.apply(lambda col: col.map(lambda x: pd.notna(x) and math.isfinite(x))).all(axis=1)
mask = valid & (cb.status == "listed") & (values.bond_price > 0) & (values.convert_value > 0) & (values.premium_pct < 10)
low_premium = cb.loc[mask].copy()
low_premium["premium_pct"] = values.loc[mask, "premium_pct"]
low_premium = low_premium.sort_values("premium_pct")
print("低溢价样本（源百分数<10，不代表低估或可交易）:", len(low_premium))
print(low_premium[["code", "name", "bond_price", "convert_value", "premium_pct"]].head())
```

---
