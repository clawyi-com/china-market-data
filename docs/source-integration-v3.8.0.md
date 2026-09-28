<!-- Modified by china-market-data contributors: removed nontechnical promotion; integration record retained. -->

# A 股数据源整合记录 · v3.8.0

调研：2026-09-04 至 2026-09-05；实现验收：2026-09-05。
基线：v3.7.2，GitHub `main` 提交 `2794807`。本衍生版本已移除非技术展示内容。

## 纳入本版

| 能力 | 数据提供方 | 与原版关系 | 数据边界 |
|---|---|---|---|
| 指数成分 | 中证、国证 | 两个新官方源 | 最近公布快照；国证为月末，不能用于历史时点回填 |
| 指数权重 | 中证、国证 | 复用上述新源 | 百分数；权重文件和成分文件可能不同日 |
| 指数估值 | 中证 | 复用新源 | 近期 PE、股息率，两种股本口径；无 PB |
| 交易日历 | 深交所 | 已有源的新端点 | 必须整月完整，未发布不推断为休市 |
| 两融备胎 | 上交所、深交所 | 已有源的新备胎 | 逐所查询；金额元、余量股/份；缺失官方字段保留为空 |
| 北交所行情备胎 | 北交所 | 新官方源 | 当前行情和五档快照；无历史回填，盘中延迟未标定 |

沿用仓库的**能力入口计数**，增加6个公共函数，源侧多路由不重复计数：54→60。
主入口51→55，备胎3→5，层数11→12，来源19→22。
这些数值不是原始 HTTP URL 的数量，也不包含候选项目、辅助函数和本地测试。

## 可复查的端点发现线索

- [AKShare：中证成分/权重](https://github.com/akfamily/akshare/blob/main/akshare/index/index_cons.py)
- [AKShare：中证估值](https://github.com/akfamily/akshare/blob/main/akshare/index/index_stock_zh_csindex.py)
- [AKShare：国证指数](https://github.com/akfamily/akshare/blob/main/akshare/index/index_cni.py)
- [Qlib：深交所交易日历](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/utils.py)
- [CNEquity：沪深官方两融](https://github.com/rootSunc/CNEquity/blob/main/src/cnequity/adapters/exchange/margin_trading.py)
- [CNEquity：北交所行情](https://github.com/rootSunc/CNEquity/blob/main/src/cnequity/adapters/bse/daily_quotes.py)

实现直接访问官方域名，未增加这些聚合库作为依赖。GitHub 代码帮助发现端点，数据本身由官方源返回。
这些链接指向会更新的上游主分支；本次实际返回及验证时间以下表为准。

## 本机真实数据验证

验证日期不等于数据日期。例如 2026-09-05 为周六，北交所当前快照日期为 9月4日；月末权重日期为8月31日。

| 请求 | 返回行数 | 源日期 | 检查 |
|---|---:|---|---|
| CSI 000300 成分 | 300 | 2026-09-04 | 代码前导零、交易所、唯一成分 |
| CSI 000300 权重 | 300 | 2026-08-31 | 百分数合计、真实月末日期 |
| CNI 399006 成分 | 100 | 2026-08-31 | 原始六位股票代码，不补成其他市场 |
| CNI 399006 权重 | 100 | 2026-08-31 | 权重合计、日期、零鉴权 |
| CSI 000300 估值 | 20 | 2026-08-10—09-04 | PE两列、股息率两列，不混用口径 |
| SZSE 2026-09 日历 | 30 | 2026-09-01—09-30 | 所有自然日齐全，采用官方交易标志 |
| SSE 两融 | 2000 | 2026-09-03 | 分页总数相符、上交所融券金额为空 |
| SZSE 两融 | 2103 | 2026-09-03 | XLSX原始元/股，无亿/万换算错误 |
| BSE 全板行情 | 341 | 2026-09-04 | 完整分页、代码唯一、每行日期一致 |
| BSE 920021 行情 | 1 | 2026-09-04 | 开8.55、高9.99、低8.55、收9.19，成交量63000262股 |

额外边界：

- 国证987008（港股科技指数）返回的腾讯代码为 `00700`；旧原型补零会错标成深市 `000700`。修复后要求国证原始股票代码六位，拒绝五位港股；对深证成指399001的500条记录核对，均已保留六位文本。
- 深交所两融在2026-09-05（周六）和2026-09-30（当时未发布）返回0行8列的表头文件。实现抛错，不将它解释为“全部标的两融为零”。
- 北交所分页期间总数变化、返回旧交易日、缺少盘口字段、重复标的均拒绝；匿名会话302仅重建一次，不循环跟随。
- 两融返回代码也校验交易所，避免把北交所或另一个市场的证券贴成请求市场；上交所两融和北交所行情的分页总数拒绝小数、布尔值等异常类型，不截断成“完整快照”。

## 验证方法

运行环境：macOS，Python 3.9.6。没有新增运行时依赖；测试直接执行 SKILL.md 中两个带标记的代码块，避免测试副本与用户实际代码脱节。

```bash
python3 -m unittest discover -s tests -v
```

26 个离线测试以合成的官方结构响应验证错误传播、股票代码、字段、日期、单位和分页；不会访问网络。
线上套件含10条真实取数路径，需要显式启用。下面是**本次**验证日期，不是以后固定应使用的日期：

```bash
ASTOCK_LIVE_TRADE_DATE=2026-09-04 ASTOCK_LIVE_MARGIN_DATE=2026-09-03 \
  python3 -m unittest discover -s tests -v
```

重跑时将日期设为源当前实际提供的交易日；北交所是当前快照，不能用旧日期重复取历史数据。
本次没有重跑旧版全部54个入口的真实网络请求，其历史验证日期保留在原章节。

## 候选池（未接入，不算已支持）

| 候选 | 已核实价值 | 决定及剩余条件 |
|---|---|---|
| [easy_tdx](https://github.com/handsomejustin/easy_tdx) | 通达信竞价过程；2026-09-04平安银行实测63点；MIT | 同一通达信数据来源的实现备选。要求Python≥3.10，先验证可选依赖与竞价契约，不改变主包Python3.9兼容 |
| [eltdx](https://github.com/electkismet/eltdx) | 当日竞价82点及历史09:25快照可用；历史完整过程未复现 | 当前 LICENSE 为 Research-Only，限制商业/生产用途；不纳入本Apache-2.0项目，不复制实现 |
| [同花顺官方 Financial-API](https://github.com/HiThink-Tech/Financial-API) | 文档含竞价、基金、批量数据等增强能力 | 需用户Key，未做带Key数据验收；不增加强制鉴权，不计入主源数量 |
| [TickFlow](https://github.com/tickflow-org/tickflow) | 免费日K实测沪市和北交所成功 | 观察型独立服务备选；本次未确认数据来源、再分发条件和长期服务保障 |
| [CNEquity](https://github.com/rootSunc/CNEquity) | 官方端点和日期/分页防错参考，含国证历史调样适配 | 继续作为实现参考；历史调样另需时点验证，不把当前月末文件称为历史成分 |
| [AKShare](https://github.com/akfamily/akshare)、[adata](https://github.com/1nchaos/adata)、[efinance](https://github.com/Micro-sheep/efinance)、[Ashare](https://github.com/mpquant/Ashare) | 可检索上游端点与解析经验 | 多数为已有来源的包装；不作为新独立来源，不恢复运行时依赖 |
| [free-stockdb](https://github.com/hello245m/free-stockdb) | 本地存储和同步设计 | 上游数据出处不够清楚，暂不接入 |

已支持与候选边界：本版不包含集合竞价、历史指数成员区间、公募基金完整层、同花顺Key接入或新的交易客户端。
