<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 估值公式、输出边界与原框架

计算前向PE、PE消化时间或PEG时读取本文；分项见 [前向PE](#forward-pe)、[消化时间](#digestion)、[PEG](#peg)、[原框架](#framework)。`<skill目录>` 为技能根目录；Python调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。full组合入口的数据来源及例外见 [完整调研流程](../SKILL.md#完整调研流程)。

公式与单票组合入口集中在 [scripts/valuation.py](../scripts/valuation.py)，依赖 requests、pandas，以及随附 `ths_eps_forecast.py` / `_ticker.py`；完整估值解析 HTML 还需 lxml。Python 调用先执行「Python 脚本路径初始化」，无需读取实现。

```bash
python3 "<skill目录>/scripts/valuation.py" forward-pe 100 2 --output pe.json
python3 "<skill目录>/scripts/valuation.py" digestion 50 0.5 --target-pe 30 --output years.json
python3 "<skill目录>/scripts/valuation.py" peg 50 0.5 --output peg.json
python3 "<skill目录>/scripts/valuation.py" full 688017 --output valuation.json
```

CLI 保存完整原生计算结果，终端给出文件路径和结果。非有限数用 `{"$float":"Infinity"}` / `-Infinity` / `NaN` 显式编码；已有路径不覆盖。原函数输出的解析警告转到 stderr，并放入终端 JSON 的 `warnings` 列表；仍保留原版可返回的部分结果，调用方不能忽略警告。未捕获的异常非零退出且不保存结果。

<a id="forward-pe"></a>

### 前向PE

当前价 / 预测 EPS；EPS ≤ 0 返回无穷大。

```python
from valuation import forward_pe
```

<a id="digestion"></a>

### PE消化时间

当前 PE ≤ 目标 PE 时返回 0，否则 CAGR ≤ 0 返回无穷大，其余为 `log(当前PE/目标PE) / log(1+CAGR)`。目标默认 30，可传 `target_pe`；CAGR 使用小数（0.5 = 50%）。

```python
from valuation import pe_digestion
```

<a id="peg"></a>

### PEG

`PE / (CAGR * 100)`；CAGR ≤ 0 返回无穷大。原框架的区间解释见下方。

```python
from valuation import calc_peg
```

<a id="framework"></a>

### 投资框架速查

以下原框架按原文保留，仅是特定筛选假设，不是公式的输入约束或所有行业通用的估值结论。30x是消化时间的默认参数，可调整；CAGR门槛、PEG区间及“期权”类比都需要另行论证，不能作为数据接口已经验证的事实，也不构成期权定价模型。

```
壁垒 → 增速 → PE消化 → PEG校验

1. 有壁垒吗？(tech_moat / capacity_moat) → 没有则排除
2. 增速多少？(CAGR > 30% 才有意义)
3. PE多久消化到30x？(< 2年合理, > 4年太贵)
4. PEG多少？(< 1 便宜, 1-1.5 合理, > 1.5 贵)

30x PE 锚点: A股成长股的合理估值重力线，所有行业统一用30x。
期权定价例外: PEG > 3 但壁垒极深时，本质是看涨期权，不适用PEG框架。
```

---
