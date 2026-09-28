<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 指数成分、权重、估值与交易日历

需要§12.1–§12.4数据时读取本文，四个CLI和Python导入见 [脚本入口](#commands)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

补齐指数成分、权重、指数估值与官方交易日历。实现集中在 [scripts/official_data.py](../scripts/official_data.py)，仅使用已有的
`requests pandas xlrd openpyxl`；不依赖前面章节的股票代码推断规则。指数代码必须是 **6 位纯数字**，
`provider="csi"` 表示中证，`provider="cni"` 表示国证，不能把股票代码直接当指数查询。

| 函数 | 契约 |
|---|---|
| `index_constituents(index_code, provider="csi")` | 官方最近发布的成分快照；中证日度文件、国证月末文件，真实日期在 `date` 列 |
| `index_weights(index_code, provider="csi")` | 最近公布的权重；`weight_percent=0.433` 表示 **0.433%**，不是 43.3% |
| `index_valuation(index_code)` | 仅中证公开估值文件：两种股本口径 PE、两种股息率；**不提供 PB、不承诺全历史** |
| `trading_calendar(year, month)` | 深交所整月日历；逐日返回 `is_open`，不靠工作日推断，也不把未发布月份当休市 |

**日期边界：** 当前成分与权重可能不同日，不能按行号拼接或将月末权重标成今天。
这些快照不提供历史时点成分；国证的 `download-history` 名字虽带 history，本次接口实际返回
单个月末快照。历史调样另有接口，暂不纳入本版。调用方应先检查 `date`，做历史回测时不能拿
当前成分代替当时成分。网络失败、结构变化、重复记录或不完整日历均抛异常，不伪装为空结果。

<a id="commands"></a>

### 12.1–12.4 脚本入口

直接运行，无需读取实现代码：

```bash
python3 "<skill目录>/scripts/official_data.py" constituents 000300 --output members.json
python3 "<skill目录>/scripts/official_data.py" weights 399006 --provider cni --output weights.json
python3 "<skill目录>/scripts/official_data.py" valuation 000300 --output valuation.json
python3 "<skill目录>/scripts/official_data.py" calendar 2026 9 --output calendar.json
```

CLI 保存完整 DataFrame（列、dtype、索引、attrs、全部行及来源字段），终端仅预览前三行；已有路径不覆盖，失败非零退出且不生成结果文件。Python 组合调用先执行「Python 脚本路径初始化」，再导入下面四个函数。指数模块独立运行，不需要加载其他业务章节。

<!-- official-data-core:start -->
```python
from official_data import index_constituents, index_weights, index_valuation, trading_calendar
```
<!-- official-data-core:end -->

```python
members = index_constituents("000300")
weights = index_weights("399006", provider="cni")
valuation = index_valuation("000300")
days = trading_calendar(2026, 9)
print(members[["date", "code", "name"]].head())
print(weights[["date", "code", "weight_percent"]].head())
print(valuation.tail(1))
print(days.loc[days.is_open, "date"].tolist())
```

原始端点的发现与交叉核对参考：
[AKShare 中证成分](https://github.com/akfamily/akshare/blob/main/akshare/index/index_cons.py)、
[AKShare 中证估值](https://github.com/akfamily/akshare/blob/main/akshare/index/index_stock_zh_csindex.py)、
[AKShare 国证](https://github.com/akfamily/akshare/blob/main/akshare/index/index_cni.py)、
[Qlib 交易日历](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/utils.py)。
本实现直接读取官方文件/API，不调用上述项目的包装库。
