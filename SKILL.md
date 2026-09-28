---
name: china-market-data
description: 当任务需要实际获取A股及相关市场数据，或进行证券代码归一化与聚宽格式转换时使用——行情/K线/逐笔(腾讯日周月前后复权+分钟线+当日逐笔、通达信官网全市场盘后包、百度)、研报(东财+新浪+同花顺+iwencai)、信号(热点/北向/龙虎榜/解禁/行业/板块资金流)、资金面(融资融券/大宗/股东户数/分红/资金流/ETF份额)、新闻(财联社/东财/华尔街见闻/新闻联播)、财务三表/F10/估值历史/ST名单、公告(巨潮)、打板(涨停池/连板/炸板率/监控池/异动)、ETF期权、舆情互动(互动易/上证e互动/热榜)、筹码分布、复权因子、申万行业变迁、宏观与利率(社融/PMI/中债收益率曲线/回购定盘利率/LPR/全球宏观日历)、指数成分/权重/估值/交易日历、期货与大宗商品(五家期货交易所日行情/商品与股指期权/持仓排名/期货日K含大商所/实时期货/A50/上海金)、事件驱动(业绩预告/机构调研/增减持/回购/股权质押/新股申购)、可转债等真实数据。十五层·87端点(含5备胎)·34个来源·附可运行代码，§1–§15 数据入口及五个备用入口使用随附 scripts；估值计算使用 valuation 脚本，组合流程示例见正文；优先用腾讯/交易所官方等数据源，东财接口已内置节流但不保证免风控，主源不可用可查「备用源速查」降级。在需要调用数据接口取数或执行上述本地代码转换时使用：A股概念解释、投资观点讨论、策略问答等无需取数或代码转换的话题不要加载本skill。
metadata:
  origin: custom
  version: "3.10.0"
---

<!-- Modified by china-market-data contributors: reorganized from a-stock-data; CLI extraction, references and validation changes. See UPSTREAM.md and NOTICE. -->

本技能覆盖行情、研报、信号、资金与筹码、新闻、财务与公司资料、公告、涨停与异动、ETF期权、互动与热度、宏观利率、指数日历、期货商品、公司事件和可转债，并提供估值、代码转换及备用取数入口。按下方端点路由选择 CLI，执行前读取对应说明；无需先阅读来源全表。

原能力树及版本标注保留于 [历史能力总览](references/sources-and-fallbacks.md#capability-history)，仅在核对历史说明时读取；当前能力边界以端点路由和详细章节为准。

## When to Activate

- 用户需要**指数成分、指数权重、指数 PE / 股息率、官方交易日历、沪深官方两融或北交所行情备份**（V3.8）。
- 用户要看**商品期货 / 期权 / 持仓排名 / A50 / 黄金现货**，或**业绩预告 / 机构调研 / 增减持 / 回购 / 股权质押 / 新股申购 / 可转债**，
  或**国债收益率曲线 / 回购利率 / LPR / 全球宏观日历**、**ETF 份额**、**ST 名单**、**新闻联播**、**沪市互动问答**、**全市场当日日线**（V3.9）。
- 用户要把代码转成**聚宽格式**（`600519.XSHG`）或获取**回测所需数据**（见「回测数据边界」）。

- 用户要查 A 股个股估值（一致预期 / PE / PEG / PE消化）
- 用户要拉实时行情（价格 / 五档盘口 / K线 / 涨跌停价）
- 用户要搜研报（按主题 / 按标的 / 按行业 / 下载PDF）
- 用户要看**当日强势股 / 题材归因 / 概念热点**
- 用户要看**北向资金动向**（沪股通/深股通分钟流向、本地已保存历史；见 [§3.2](#northbound-data)）
- 用户要看**概念板块归属**（行业/概念/地域）
- 用户要看**个股资金流向**（主力/散户/超大单/大单分钟级）
- 用户要看**龙虎榜席位**（营业部 + 机构买卖）
- 用户要看**全市场龙虎榜**（当日所有上榜股票 + 净买额排名）
- 用户要看**限售解禁日历**（历史解禁 + 未来待解禁）
- 用户要做**行业横向对比**（涨跌排名 / 资金流入 / 领涨股）
- 用户要看**融资融券 / 两融数据**（融资余额 + 融券余额）
- 用户要看**大宗交易**（成交价/量 + 买卖方营业部）
- 用户要看**股东户数变化**（筹码集中度）
- 用户要看**分红送转历史**（每股派息 + 送股 + 转增）
- 用户要看**指数/ETF行情**（上证指数 / 沪深300 / 创业板指 / ETF）
- 用户要看**涨停 / 打板情绪**（涨停池 / 连板梯队 / 炸板率 / 跌停 / 涨停原因题材）
- 用户要看**ETF 期权**（T型报价 / 希腊字母 Delta·Gamma·Theta·Vega / 隐含波动率 IV）
- 用户要看**投资者互动问答**（公司如何回应某传闻/利好 · 互动易）
- 用户要看**市场热度 / 人气榜**（同花顺热榜 / 东财人气榜 / 个股概念命中）
- 用户要看新闻资讯（个股新闻 / 财联社快讯 / 全球资讯）
- 用户要查公告（巨潮公告全文）
- 用户要做产业链调研 / 批量横向对比
- 关键词：估值、一致预期、机构预测、市盈率、PEG、市值、研报、产业链、行业研究、K线、盘口、公告、新闻、**强势股、题材、热点、概念归因、北向资金、沪股通、深股通、概念板块、资金流向、主力、龙虎榜、席位、营业部、全市场龙虎榜、净买入、解禁、限售、行业对比、行业轮动、融资融券、两融、大宗交易、股东户数、筹码集中、分红、派息、送股、指数、ETF、涨停、打板、连板、炸板、跌停、涨停原因、封板、晋级率、ETF期权、希腊字母、隐含波动率、互动易、投资者关系、热榜、人气榜、市场热度、期货、商品期权、股指期权、持仓排名、A50、黄金、上海金、业绩预告、机构调研、增减持、回购、股权质押、新股申购、打新、可转债、转股溢价率、国债收益率、收益率曲线、回购利率、FR007、LPR、宏观日历、ETF份额、ST、新闻联播、上证e互动、聚宽、回测**

当上述需求需要实际取数时，按下方路由选择 CLI；仅需证券代码格式转换时使用对应本地 helper。仅讨论概念或投资观点且无需取数时不使用。命中场景不代表每个来源都支持该市场和日期，执行前核对路由限制。

## 端点路由速查（按需定位，不必通读全文）

按「用户需求与关键限制」选择入口，再读取对应章节（§）。CLI 列是脚本及子命令索引，不是完整命令；使用 `python3 "<skill目录>/scripts/<脚本名>.py" [子命令] --help` 查看参数，并按章节示例执行。多个子命令以 `/` 分隔，按需求选一个，不将 `/` 输入命令。Python 函数列仅用于组合调用与能力映射，无需先执行导入。除 iwencai 需 API Key 外全部零 key。

| § | Python 函数（组合调用） | 用户需求与关键限制 | CLI 入口 | 源 |
|---|---|---|---|---|
| 前置 | `norm_ticker(code)` | 任意写法→纯6位（`SH600519`/`600519.SH`/`600519.XSHG` 皆可；解析失败抛错不返空） | 无独立 CLI；见下方 Python 转换说明 | 本地 |
| 前置 | `to_joinquant(code)` | 转聚宽代码 `600519.XSHG` / `000001.XSHE`（北交所不转换） | 无独立 CLI；见下方 Python 转换说明 | 本地 |
| 1.1 | `tencent_quote(codes)` | 实时价/PE/PB/市值/换手/涨跌停/指数/ETF（带 `is_stale` 僵尸报价标志）；股价/市盈率；上证指数用 sh000001，亦支持沪深300、创业板指；不返回五档盘口 | [tencent_quote.py](scripts/tencent_quote.py)；[使用说明](references/quotes-and-kline.md#quote) | 腾讯 |
| 1.2 | `tencent_kline(code, period, adjust, start, end, count)` | 日/周/月前后复权 + 1~60 分钟 K 线（沪深，不含北交所） | [tencent_kline.py](scripts/tencent_kline.py)；[使用说明](references/quotes-and-kline.md#kline) | 腾讯 |
| 1.3 | `tdx_daily_package(date)` | 某交易日沪深北全部证券日线（含成交额） | [tdx_daily_package.py](scripts/tdx_daily_package.py) ；[使用说明](references/market-data-details.md#daily-package) | 通达信官网 |
| 1.4 | `tencent_ticks(code)` | 最近一个交易日的分笔成交（价/手/元/主动买卖；沪深个股+ETF，不含北交所） | [tencent_ticks.py](scripts/tencent_ticks.py) ；[使用说明](references/market-data-details.md#ticks) | 腾讯 |
| 1.5 | `baidu_kline_with_ma(code)` | 日K线带 MA5/10/20 | [baidu_kline_with_ma.py](scripts/baidu_kline_with_ma.py) ；[使用说明](references/market-data-details.md#baidu) | 百度 |
| 1.6 | `sina_adjust_factor(code, kind)` / `apply_adjust(bars, factors)` | 复权因子 qfq/hfq + 套用到不复权K线 | [sina_adjust.py](scripts/sina_adjust.py)：`factors / apply` ；[使用说明](references/market-data-details.md#adjust) | 新浪 |
| 1.7 | `tdx_client()` → `.bars()` / `.quotes()` / `.transaction()` | K线(多周期,不复权) / 五档盘口 / 逐笔成交（⚠️ 2026-09 起返回空，#52，留档） | [tdx_client.py](scripts/tdx_client.py)：`bars / quotes / transaction`（失效留档） ；[使用说明](references/market-data-details.md#mootdx) | 通达信 |
| 2.1 | `eastmoney_reports(code)` / `download_pdf(rec)` | 按标的搜个股研报、机构评级、三年EPS、下载 PDF | [eastmoney_reports.py](scripts/eastmoney_reports.py)：`stock / pdf`；[使用说明](references/research-reports.md#eastmoney) | 东财 |
| 2.1 | `eastmoney_industry_reports(industry_code)` | 按行业搜研报、行业研究；下载 PDF 使用同脚本 pdf 子命令 | [eastmoney_reports.py](scripts/eastmoney_reports.py)：`industry`；[使用说明](references/research-reports.md#eastmoney) | 东财 |
| 2.2 | `ths_eps_forecast(code)` | 机构一致预期 EPS；机构预测、盈利预测 | [ths_eps_forecast.py](scripts/ths_eps_forecast.py)；[使用说明](references/research-reports.md#eps) | 同花顺 |
| 2.3 | `iwencai_search(query)` / `iwencai_query(query)` | NL 语义搜研报/选股（需 Key）；按主题、产业链搜研报 | [iwencai.py](scripts/iwencai.py)：`search / query`；[使用说明](references/research-reports.md#iwencai) | iwencai |
| 2.4 | `sina_research_reports(code=None, page=1)` | 研报列表：标题/类型/机构/研究员（无评级） | [sina_reports.py](scripts/sina_reports.py)；[使用说明](references/research-reports.md#sina) | 新浪 |
| 3.1 | `ths_hot_reason()` | 当日强势股+题材归因；热点、概念归因 | [ths_hot_reason.py](scripts/ths_hot_reason.py)；[使用说明](references/signals-realtime.md#hot) | 同花顺 |
| 3.2 | `hsgt_realtime()` | 北向资金、沪股通/深股通：当日分钟流向或本地已保存历史；sgt 仅参考，历史不补抓；见 [调用说明](#northbound-data) | [northbound.py](scripts/northbound.py)：实时用 `realtime`；本地历史用 `history`；显式保存见 §3.2；[使用说明](references/signals-realtime.md#northbound) | 同花顺 |
| 3.3 | `eastmoney_concept_blocks(code)` | 个股所属板块/概念归属；概念板块 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`boards`；[使用说明](references/signals-realtime.md#boards) | 东财 |
| 3.4 | `eastmoney_fund_flow_minute(code)` | 个股资金流（分钟级）；主力/散户、超大单/大单 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`minute`；[使用说明](references/signals-realtime.md#minute) | 东财 |
| 3.5 | `dragon_tiger_board(code, date)` | 个股龙虎榜+买卖席位 TOP5；龙虎榜席位、营业部、机构买卖 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`dragon`；[使用说明](references/signals-ranking.md#dragon) | 东财 |
| 3.6 | `lockup_expiry(code, date)` | 解禁历史+未来90天待解禁；限售解禁 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`lockup`；[使用说明](references/signals-ranking.md#lockup) | 东财 |
| 3.7 | `industry_comparison()` | 行业板块涨跌排名；行业对比、行业轮动、领涨股；行业/概念近期涨幅另用 `board-quotes` | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`industry`；[使用说明](references/signals-ranking.md#industry) | 东财 |
| 3.8 | `board_fund_flow(board_type, period)` | 板块资金流向（行业/概念/地域 × 今日/5日/10日，主力+四档）；资金流入 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`board-flow`；[使用说明](references/signals-ranking.md#board-flow) | 东财 |
| 3.9 | `daily_dragon_tiger(date)` | 全市场龙虎榜+净买额排名；净买入排名 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`daily-dragon`；[使用说明](references/signals-ranking.md#daily-dragon) | 东财 |
| 4.1 | `margin_trading(code)` | 融资融券明细；两融、融资余额、融券余额 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`margin`；[使用说明](references/capital-and-chips.md#margin) | 东财 |
| 4.2 | `block_trade(code)` | 大宗交易+营业部；成交价/量、买卖方营业部 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`block`；[使用说明](references/capital-and-chips.md#block) | 东财 |
| 4.3 | `holder_num_change(code)` | 股东户数变化；筹码集中度的参考指标，不等同筹码分布 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`holders`；[使用说明](references/capital-and-chips.md#holders) | 东财 |
| 4.4 | `dividend_history(code)` | 分红送转历史；分红、派息、送股、转增 | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`dividends`；[使用说明](references/capital-and-chips.md#dividends) | 东财 |
| 4.5 | `stock_fund_flow_120d(code)` | 个股资金流（120日，日级） | [eastmoney_signals.py](scripts/eastmoney_signals.py)：`stock-flow`；[使用说明](references/capital-and-chips.md#stock-flow) | 东财 |
| 4.6 | `chip_distribution(df)` | 筹码分布（获利比例/平均成本/90-70成本区间/筹码峰） | [chip_distribution.py](scripts/chip_distribution.py)；[使用说明](references/capital-and-chips.md#chips) | 本地计算 |
| 4.7 | `etf_shares(date, exchange)` | ETF 份额（万份）：上交所历史日期 / 深交所当前快照 | [etf_shares.py](scripts/etf_shares.py)；[使用说明](references/capital-and-chips.md#etf) | 上交所/深交所 |
| 5.1 | `eastmoney_stock_news(code)` | 个股新闻 | [market_news.py](scripts/market_news.py)：`stock`；[使用说明](references/news.md#stock) | 东财 |
| 5.2 | `cls_telegraph()` | 财联社电报（7×24，本地签名零key） | [market_news.py](scripts/market_news.py)：`cls`；[使用说明](references/news.md#cls) | 财联社 |
| 5.3 | `eastmoney_global_news()` | 全球资讯（7×24） | [market_news.py](scripts/market_news.py)：`global`；[使用说明](references/news.md#global) | 东财 |
| 5.4 | `wallstreetcn_lives(channel, limit, cursor)` | 7×24 快讯（按频道，可翻页） | [news_sources.py](scripts/news_sources.py)：`wscn`；[使用说明](references/news.md#wscn) | 华尔街见闻 |
| 5.5 | `cctv_news(date, with_content=True)` | 新闻联播条目 + 文字稿（政策信号研究用） | [news_sources.py](scripts/news_sources.py)：`cctv`；[使用说明](references/news.md#cctv) | 央视网 |
| 6.1 | `tdx_client(check='finance').finance(symbol)` | 季报快照 37 字段 | [tdx_client.py](scripts/tdx_client.py)：`finance`；[使用说明](references/company-and-history.md#finance) | 通达信 |
| 6.2 | `tdx_client(check='finance').F10(symbol, name)` | F10 文本（2026-09 起服务端只剩「最新提示」一类） | [tdx_client.py](scripts/tdx_client.py)：`F10C / F10`；[使用说明](references/company-and-history.md#f10) | 通达信 |
| 6.3 | `eastmoney_stock_info(code)` | 行业/股本/市值/上市日期 | [company_data.py](scripts/company_data.py)：`info`；[使用说明](references/company-and-history.md#info) | 东财 |
| 6.4 | `sina_financial_report(code, type)` | 财报三表；资产负债表/利润表/现金流量表 | [company_data.py](scripts/company_data.py)：`finance`；[使用说明](references/company-and-history.md#statements) | 新浪 |
| 6.5 | `baostock_valuation_history(code, s, e)` | 估值历史 PE/PB/PS/PCF + 换手率 + 停牌 + ST（**不支持北交所**） | [baostock_data.py](scripts/baostock_data.py)：`valuation`；[使用说明](references/company-and-history.md#valuation) | baostock |
| 6.6 | `baostock_stock_basic(code)` | 上市日 / **退市日** / 状态 | [baostock_data.py](scripts/baostock_data.py)：`basic`；[使用说明](references/company-and-history.md#basic) | baostock |
| 6.7 | `sw_industry_history()` / `sw_industry_as_of(df, code, d)` | 申万行业**变迁史**（消除前视偏差，仅代码无中文名） | [sw_industry.py](scripts/sw_industry.py)：`history / as-of`；[使用说明](references/company-and-history.md#industry) | 申万 |
| 6.8 | `st_stock_list()` | 沪深京 ST / *ST 当日名单 | [st_list.py](scripts/st_list.py)；[使用说明](references/company-and-history.md#st) | 东财（baostock 兜底） |
| 7.1 | `cninfo_announcements(code)` | 公告检索+PDF 下载 | [cninfo_announcements.py](scripts/cninfo_announcements.py)；[使用说明](references/announcements.md#cninfo) | 巨潮 |
| 7.2 | `tdx_client(check='finance').F10(symbol, name='最新提示')` | 最新公告摘要 | [tdx_client.py](scripts/tdx_client.py)：`F10`；[使用说明](references/announcements.md#f10) | 通达信 |
| 8.1 | `em_zt_pool` / `em_zb_pool` / `em_dt_pool` / `em_yzt_pool` | 涨停/炸板/跌停/昨涨停四池；涨停池/炸板池/跌停池/昨涨停池；结合昨涨停表现研究晋级率 | [limit_pools.py](scripts/limit_pools.py)：`zt / zb / dt / yzt`；[使用说明](references/limit-and-anomaly.md#pools) | 东财 |
| 8.2 | `ths_limit_up_pool(date)` | 涨停原因题材+封板成功率+板型；涨停原因、题材、封板 | [limit_pools.py](scripts/limit_pools.py)：`ths`；[使用说明](references/limit-and-anomaly.md#reasons) | 同花顺 |
| 8.3 | `limit_up_sentiment(date)` | 炸板率/连板高度/连板梯队；打板情绪、连板梯队 | [limit_pools.py](scripts/limit_pools.py)：`sentiment`；[使用说明](references/limit-and-anomaly.md#sentiment) | 东财(四池组合) |
| 8.4 | `em_stock_monitor()` | 重点监控池（风险警示名单+生效时间窗） | [limit_pools.py](scripts/limit_pools.py)：`monitor`；[使用说明](references/limit-and-anomaly.md#monitor) | 东财 |
| 8.5 | `em_price_anomaly()` / `em_price_anomaly_count()` | 日内异动明细 / 按标的聚合异动统计（严重异常波动） | [limit_pools.py](scripts/limit_pools.py)：`anomaly / anomaly-count`；[使用说明](references/limit-and-anomaly.md#anomaly) | 东财 |
| 9.1 | `sina_option_codes` / `sina_option_tquote` / `sina_option_greeks` | ETF期权合约清单 / T型报价 / 希腊字母+IV；Delta/Gamma/Theta/Vega、隐含波动率 | [sina_options.py](scripts/sina_options.py)：`codes / quote / greeks`；[使用说明](references/etf-options.md) | 新浪 |
| 10.1 | `cninfo_irm(code)` | 互动易问答（提问+公司回复，深市）；投资者关系、公司回应传闻/利好；沪市见 §10.3 | [investor_sentiment.py](scripts/investor_sentiment.py)：`irm`；[使用说明](references/interaction-and-popularity.md#irm) | 巨潮 |
| 10.2 | `ths_hot_list()` / `em_hot_rank()` / `em_hot_concept(code)` | 热榜/人气榜/概念命中；市场热度、人气排名 | [investor_sentiment.py](scripts/investor_sentiment.py)：`ths / rank / concepts`；[使用说明](references/interaction-and-popularity.md#ranking) | 同花顺+东财 |
| 10.3 | `sse_e_interaction(code=None, kind='answered')` | 上证e互动问答（沪市）；沪市互动问答、公司回复 | [sse_interaction.py](scripts/sse_interaction.py)；[使用说明](references/interaction-and-popularity.md#sse) | 上证e互动（上交所运营） |
| 11.1 | `pboc_social_financing(year)` | 社会融资规模增量（月度12列）；社融 | [macro_data.py](scripts/macro_data.py)：`social-financing`；[使用说明](references/macro-and-rates.md#financing) | 人民银行 |
| 11.2 | `nbs_pmi()` | 制造业/非制造业/综合 PMI + 大中小型企业 | [macro_data.py](scripts/macro_data.py)：`pmi`；[使用说明](references/macro-and-rates.md#pmi) | 国家统计局 |
| 11.3 | `chinabond_yield_curve(start, end, curve)` | 国债 / 银行 AAA / 中短票 AAA 收益率曲线 3月~30年 | [macro_data.py](scripts/macro_data.py)：`yield-curve`；[使用说明](references/macro-and-rates.md#yield) | 中债 |
| 11.4 | `repo_fixing_rates(kind)` | 回购定盘利率 FR / FDR 001·007·014；FR007 | [macro_data.py](scripts/macro_data.py)：`repo-fixing`；[使用说明](references/macro-and-rates.md#repo) | 中国货币网 |
| 11.5 | `lpr_history()` | LPR 1 年 / 5 年全历史 | [macro_data.py](scripts/macro_data.py)：`lpr`；[使用说明](references/macro-and-rates.md#lpr) | 东财 |
| 11.6 | `macro_calendar(start, end, country, min_importance)` | 全球宏观日历（公布值/预期/前值） | [macro_data.py](scripts/macro_data.py)：`calendar`；[使用说明](references/macro-and-rates.md#calendar) | 华尔街见闻 |
| 12.1 | `index_constituents(index_code, provider)` | 最近公布的沪深北指数成分；csi/cni 显式选源；当前快照，不能当作历史指数成分 | [official_data.py](scripts/official_data.py)：`constituents`；[使用说明](references/index-and-calendar.md) | 中证/国证 |
| 12.2 | `index_weights(index_code, provider)` | 最近公布的指数权重（百分数），保留真实日期 | [official_data.py](scripts/official_data.py)：`weights`；[使用说明](references/index-and-calendar.md) | 中证/国证 |
| 12.3 | `index_valuation(index_code)` | 两种口径 PE、股息率；不含 PB | [official_data.py](scripts/official_data.py)：`valuation`；[使用说明](references/index-and-calendar.md) | 中证 |
| 12.4 | `trading_calendar(year, month)` | 官方整月交易日历 | [official_data.py](scripts/official_data.py)：`calendar`；[使用说明](references/index-and-calendar.md) | 深交所 |
| 13.1 | `futures_daily(date, exchange)` | 期货日行情（SHFE/INE/CZCE/CFFEX/GFEX） | [futures_data.py](scripts/futures_data.py)：`daily`；[使用说明](references/futures-and-commodities.md) | 五家期货交易所 |
| 13.2 | `options_daily(date, exchange)` | 商品期权 / 股指期权日行情 + Delta / IV（中金所不公布这两项） | [futures_data.py](scripts/futures_data.py)：`options`；[使用说明](references/futures-and-commodities.md) | 五家期货交易所 |
| 13.3 | `futures_position_rank(date, exchange, symbol)` | 会员成交 / 持买 / 持卖前 20 名；持仓排名 | [futures_data.py](scripts/futures_data.py)：`rank`；[使用说明](references/futures-and-commodities.md) | 上期所/能源/郑商所/中金所 |
| 13.4 | `futures_realtime(symbols)` | 实时期货（含大商所品种） | [futures_data.py](scripts/futures_data.py)：`realtime`；[使用说明](references/futures-and-commodities.md) | 新浪 |
| 13.5 | `a50_futures()` | 富时中国 A50 期指 | [futures_data.py](scripts/futures_data.py)：`a50`；[使用说明](references/futures-and-commodities.md) | 新浪 |
| 13.6 | `sge_spot(instrument)` | 上海金交所现货日线（黄金/白银/铂金）；上海金、黄金现货 | [futures_data.py](scripts/futures_data.py)：`spot`；[使用说明](references/futures-and-commodities.md) | 上金所 |
| 13.7 | `futures_kline(symbol, start, end)` | 期货日 K：单个合约 / 主力连续的逐日序列（含大商所） | [futures_data.py](scripts/futures_data.py)：`kline`；[使用说明](references/futures-and-commodities.md) | 新浪 |
| 14.1 | `earnings_forecast(code, report_date, limit)` | 业绩预告 | [events_data.py](scripts/events_data.py)：`forecast`；[使用说明](references/corporate-events.md) | 东财 |
| 14.2 | `institution_survey(code, start, end, detail, limit)` | 机构调研（汇总 / 逐机构） | [events_data.py](scripts/events_data.py)：`survey`；[使用说明](references/corporate-events.md) | 东财 |
| 14.3 | `holder_trades(code, direction, start, end, limit)` | 股东增减持 | [events_data.py](scripts/events_data.py)：`holder-trades`；[使用说明](references/corporate-events.md) | 东财 |
| 14.4 | `share_buyback(code, progress, limit)` | 股票回购方案与进度 | [events_data.py](scripts/events_data.py)：`buyback`；[使用说明](references/corporate-events.md) | 东财 |
| 14.5 | `equity_pledge(code, date, limit)` | 股权质押比例（中国结算周度，仅沪深） | [events_data.py](scripts/events_data.py)：`pledge`；[使用说明](references/corporate-events.md) | 东财 |
| 14.6 | `ipo_calendar(limit)` | 新股申购日历；打新 | [events_data.py](scripts/events_data.py)：`ipo`；[使用说明](references/corporate-events.md) | 东财 |
| 15.1 | `convertible_bonds(include_delisted=False)` | 可转债条款 + 转股价值 / 溢价率；转股溢价率 | [events_data.py](scripts/events_data.py)：`bonds`；[使用说明](references/convertible-bonds.md) | 东财 |
| 官方备胎扩展 | `margin_trading_backup(date, exchange, code=None)` | 单所两融明细（由 official_data 自动加载依赖） | [official_data.py](scripts/official_data.py)：`margin` | 上交所/深交所 |
| 官方备胎扩展 | `bse_quote_backup(date, code=None)` | 北交所全板/单票当前快照（由 official_data 自动加载依赖） | [official_data.py](scripts/official_data.py)：`bse-quote` | 北交所 |
| 备用源速查 | `dragon_tiger_backup` / `fund_flow_backup` / `announcements_backup` | 龙虎榜/资金流/公告官方备胎（主源被封时降级） | [market_backups.py](scripts/market_backups.py)：`dragon-tiger / fund-flow / announcements` | 交易所官方+新浪+东财(沪市公告) |
| 估值公式 | `forward_pe` / `pe_digestion` / `calc_peg` / `full_valuation(code)` | 前向PE / PE消化时间 / PEG / 单票估值全景；个股估值、批量比较见「完整调研流程」 | [valuation.py](scripts/valuation.py)：`forward-pe / digestion / peg / full` | 本地计算 |

## 数据源优先级 & 东财防封（重要，先读）

### 优先级原则：按任务路由选源，核对覆盖与请求限制

| 优先级 | 数据源 | 协议 | 封 IP 风险 | 覆盖 |
|--------|--------|------|-----------|------|
| **1（首选）** | **腾讯财经** | HTTP | 历史记录存在限流（§1.2 三入口轮换），不保证免封禁 | 实时价、PE/PB/市值/换手率/涨跌停、指数、ETF、日周月/分钟 K 线、当日逐笔 |
| **2** | **交易所 / 官方机构** | HTTP | 极低（避免高频） | 通达信盘后包、沪深北交易所、五家期货交易所、上金所、中债、货币网、中证/国证 |
| **3** | 新浪 / 巨潮 / 同花顺 / 华尔街见闻 | HTTP | 低 | 财报三表、复权因子、公告、一致预期/热点、研报列表、快讯 |
| **4** | **mootdx（通达信）** | TCP 7709 二进制 | 不保证免封禁或可达 | 财务快照、F10 正常；**K 线 / 盘口 / 逐笔 2026-09 起返回空（#52）** |
| **5（按具体任务路由）** | **东财 eastmoney** | HTTP | **有风控，会封 IP** | 见下 |

行情、K线、实时价、市值与财务三表优先考虑腾讯、官方或新浪的对应入口；最终按端点路由核对市场、日期、字段和复权口径。可取到相似数据不代表可等价替换；任何来源都不保证免限流或封禁。

### 默认使用东财的能力

下列能力默认走东财（须限流）；已有交易所备胎的龙虎榜、两融可按文末速查表切换，不应视为东财独占：

> 龙虎榜席位 · 全市场龙虎榜 · 限售解禁日历 · 融资融券 · 大宗交易 · 股东户数 · 分红送转 · 个股资金流向（分钟/日级）· 行业板块排名 · 研报列表/PDF · 个股新闻 · 全球资讯 · ST 名单 · LPR · 事件驱动（业绩预告/机构调研/增减持/回购/质押/新股）· 可转债

历史阈值与封禁案例见 [东财历史风控记录](references/sources-and-fallbacks.md#eastmoney-history)。这些记录不是安全请求配额或恢复时间保证；不同子域可能受不同影响，腾讯也可能限流。实际调用仍遵守下方请求规则和逐端点降级限制。

**被封后的降级路径**（各层备胎详见「备用源速查」章节）：

| 被封端点 | 替代方案 | 差异 |
|---|---|---|
| `push2/clist/get`（股票列表） | `datacenter-web` + 腾讯行情批量 | 行业字段来自 datacenter 的 `BOARD_NAME` |
| `push2his/kline/get`（K线） | 腾讯 `fqkline/get`（前复权）→ 新浪 `getKLineData`（不复权） | 腾讯有前复权，新浪没有 |
| `push2/stock/get`（个股） | 腾讯 `qt.gtimg.cn` | 腾讯无行业/概念字段 |

### 防封铁律（调用东财时必须遵守）

1. **串行，不并发**——绝不对东财开多线程/协程并发请求
2. **每次间隔 ≥ 1 秒 + 随机抖动**（QPS ≤ 2），批量筛选时调大到 1.5~2 秒
3. **复用 HTTP 会话**（Keep-Alive），不要每次新建连接
4. **带正常 UA + Referer**（按脚本现有请求头与接口要求核对，不假设每个端点均已配置）
5. **批量场景每只股票之间 sleep**——AI 跑批量循环（如筛选 100 只股逐个拉龙虎榜/资金流）是被封的头号元凶

### 东财限流入口与调用方式

本 SKILL 提供节流入口 `em_get()`（定义见下方「东财数据中心统一查询（共用 helper）」），在同进程串行调用下提供最小间隔 `EM_MIN_INTERVAL=1.0s` 与随机抖动、复用 `EM_SESSION`（Keep-Alive）及默认 UA。业务脚本自行导入所需 helper；CLI 调用和导入业务函数均无需先执行公共导入块。例外：`market_backups.py` 保留 urllib 请求，沪市公告备用仍访问东财，但未接入 `em_get()`，不能假定已有自动限流。`investor_sentiment.py` 的三个入口也未接入 `em_get()`（见 §10.2），需由调用方控制请求频率。限流不能保证不触发风控。

> 仅在 Python 中直接调用公共 helper 时，才按「共用 helper」执行导入；调节共享间隔需 `import _eastmoney` 后修改 `_eastmoney.EM_MIN_INTERVAL`。CLI 仅在支持时使用 `--min-interval`（见对应命令帮助）。状态只在同一进程内共享，不是跨进程限流器，不要并发启动多个 CLI 绕过间隔。

---

## Prerequisites

```bash
python3 -m venv "<skill目录>/.venv"
PIP_USER=0 "<skill目录>/.venv/bin/python" -m pip install -r "<skill目录>/requirements.txt"
python3 "<skill目录>/scripts/run.py" --check
```

Windows PowerShell（通常没有 `python3` 命令，改用 `py -3`；未安装 py 启动器时用 `python`）：

```powershell
py -3 -m venv "<skill目录>\.venv"
$env:PIP_USER = "0"
& "<skill目录>\.venv\Scripts\python.exe" -m pip install -r "<skill目录>\requirements.txt"
py -3 "<skill目录>\scripts\run.py" --check
```

技能目录只读（无法创建 `.venv`）时，把虚拟环境建在可写位置，之后一律用该解释器运行脚本；技能目录内没有 `.venv` 时脚本不切换解释器，直接使用调用它的 Python：

```bash
python3 -m venv ~/.venvs/china-market-data
PIP_USER=0 ~/.venvs/china-market-data/bin/python -m pip install -r "<skill目录>/requirements.txt"
~/.venvs/china-market-data/bin/python "<skill目录>/scripts/run.py" --check
```

首次使用第三方库功能时先检查依赖；失败时按输出修复当前技能的虚拟环境，不要轮流猜测系统 Python。需要 Python 3.9+。`PIP_USER=0` 用于覆盖全局 pip 的 user 模式配置（否则 venv 内安装会报 `Can not perform a '--user' install`）。下文示例统一写 `python3`：Windows 换成 `py -3` 或 `python`，目录只读时换成上面外部虚拟环境的解释器路径。输出流编码无法表示中文时（如英文 Windows 管道默认的 cp1252），脚本自动改用 UTF-8 输出，读取方按 UTF-8 解码。文中 CLI 示例可直接运行业务脚本，也可用 `python3 "<skill目录>/scripts/run.py" 业务.py`（后接原参数）；两种方式在技能内 `.venv` 存在时都会自动切换到它，不自动安装依赖，也不依赖宿主 agent 配置（`tencent_quote.py` 仅用标准库，不切换）。可只安装任务需要的依赖；`--check` 检查的是全部能力，未装可选依赖不阻止腾讯报价等仅需标准库的 CLI；不必为这类任务安装全部依赖。

| 依赖 | 版本要求 | 用途 |
|------|---------|------|
| mootdx | >= 0.10 | TCP 财务快照+F10（非 HTTP 依赖之一；K 线/盘口/逐笔 2026-09 起返回空，#52）；0.11.x 用 `tdx_client()` 规避 BESTIP bug，见下节 |
| requests | any | 所有HTTP API直连 |
| pandas | any | 数据处理+HTML表格解析 |
| stockstats | any | 随附脚本未使用；仅供组合分析时自行计算 RSI/MACD/BOLL 等指标 |
| numpy | any | §4.6 筹码分布的网格计算 |
| baostock | >= 0.8 | §6.5/§6.6 估值历史·换手率·停牌·ST·退市日，§6.8 ST 名单兜底（TCP，免注册免 key；**不支持北交所**） |
| xlrd | >= 2.0 | 读 `.xls`（§6.7 申万行业分类、§12 中证） |
| openpyxl | any | 读 `.xlsx`（§11.1 社融、§12 国证、深交所两融） |
| lxml | any | pandas HTML 表格解析（同花顺 EPS、估值组合等） |

> **架构：** 除 mootdx 与 baostock（均为 TCP 客户端库）外，所有数据源均为直连 HTTP API，不经第三方数据封装。每个 HTTP 端点的底层 URL/参数完全暴露，方便调试和定制。

### iwencai API Key（仅语义搜索需要）

```bash
# 环境变量方式
export IWENCAI_API_KEY="your_key_here"
export IWENCAI_BASE_URL="https://openapi.iwencai.com"

# 申请地址: https://www.iwencai.com/skillhub
# 注册后安装 SkillHub CLI，再安装 report-search 技能即可获得 Key
```

其他数据源（腾讯 / 东财 / 同花顺 / 百度股市通 / 新浪 / 巨潮 / 财联社 / mootdx / baostock / 申万 / 人民银行 / 国家统计局 / 沪深北交易所 / 中证 / 国证 / 通达信官网 / 华尔街见闻 / 央视网 / 中债 / 中国货币网 / 五家期货交易所 / 上金所）全部免费，无需 key。

### mootdx 调用说明

使用 [scripts/tdx_client.py](scripts/tdx_client.py)，依赖 mootdx 和 pandas。

- **CLI 调用：** 脚本自动创建客户端、选择服务器并真实取数验活，已规避 BESTIP 空串问题，无需执行 Python 路径初始化或手动导入。`finance`、`F10C`、`F10` 默认使用财务验活；`bars`、`quotes`、`transaction` 默认使用 K 线验活。命令示例见 §6.1、§6.2、§7.2。
- **Python 调用：** 需要复用客户端或直接处理原生返回对象时，先执行下方「Python 脚本路径初始化」，再按对应章节导入并创建 `tdx_client(check='finance')`。使用此 helper，避免裸调用 `Quotes.factory()` 触发 BESTIP 问题。
- **可用范围：** 2026-09-20 实测财务快照和 F10「最新提示」可用，K 线 / 盘口 / 逐笔命令返回空；行情替代入口见 §1.7，F10 类别限制见 §6.2。mootdx 使用 TCP 7709，海外网络可能超时。

### Python 脚本路径初始化

直接运行 CLI 时不需要这一步。组合使用 Python 函数或执行下文含脚本导入的代码块前，在同一个 Python 进程先运行：将 `<skill目录>` 替换为本文件所在目录的绝对路径（也支持 `~/...`）。不改变当前工作目录。

```python
import sys
from pathlib import Path

skill_dir = Path("<skill目录>").expanduser().resolve()
sys.path.insert(0, str(skill_dir / "scripts"))
```

公共代码规则位于 `scripts/_ticker.py`（标准库）；非东财 HTTP 与表格 helper 位于 `scripts/_market_common.py`（requests、pandas）。下文直接导入，不需要读取源码。业务函数均从对应脚本导入；东财 `em_get` 及会话/限流状态在 `_eastmoney.py` 共用，保留原请求行为。

### 市场前缀规则（全局通用）

```python
from _ticker import SH_INDEX, get_prefix
```

> **歧义说明：** `000001` 默认按个股→`sz000001`（平安银行）；要上证指数请显式传 `sh000001`。`000016` 默认按沪指数→上证50；要深康佳A 请传 `sz000016`。

> ### ⚠️ 北交所老号段（43/83/87）已基本作废 — 会拿到僵尸数据且不报错
>
> **2026-07-31 实测：** 东财北交所在市 342 只中 **336 只已是 `920xxx` 号段**，仅剩 3 只老码且全部停牌。存量公司代码已整体迁移（如 锦波生物 `832982`→`920982`、贝特瑞 `835185`→`920185`）。
>
> **危险在于老码不会报错，而是返回看似正常的脏数据：**
>
> | 接口 | 传老码 `832982` | 传新码 `920982` |
> |------|----------------|----------------|
> | 腾讯行情 | 返回 **112.60、成交量 0**（定格在迁移日） | 131.74，正常成交 ✅ |
> | 腾讯行情（贝特瑞） | `835185` → 45.91、成交量 0 | `920185` → 21.05 ✅ |
> | 东财研报 | **0 篇**（静默空） | 79 篇 ✅ |
>
> 老码行情价与真实价可差 17%~100%+，直接拿去算估值会得出完全错误的结论。
>
> **判定僵尸报价：** `成交量 == 0 且 最新价 == 昨收` → 极可能是已迁移的废码（真停牌股同样满足，两者都不该用于估值）。`tencent_quote()` 已内置该检测并置 `is_stale` 标志，见 §1.1。
>
> **拿新码：** 用 `push2` 北交所全量清单 `fs=m:0+t:81+s:2048` 按名称反查现行代码。

### Ticker 格式归一化

`norm_ticker()` 把下列写法统一成纯 6 位数字：

> ⚠️ **不是所有端点都自动归一化**（V3.6.0 前这里写的是「所有接口统一支持」，与实现不符，已改正）。
> - **已内置归一化**：§2.1 `eastmoney_reports()`、§2.2 `ths_eps_forecast()`。
> - **只认纯 6 位或显式 `sh`/`sz`/`bj` 前缀**（其余端点）：`tencent_quote()` 等走 `get_prefix()` 路由的函数
>   支持 `600519` 和 `sh600519`，但**不认后缀式** `600519.SH`——实测会拼成 `sh600519.SH` 并返回空载荷（静默失败）。
> - **结论**：拿到用户输入的代码，**先过一遍 `norm_ticker()` 再传给任何端点**，最省事也最安全。
>   例外：输入本身带市场信息且落在 000 歧义段（`000001.SH` / `000001.XSHG` = 上证指数）时，`norm_ticker()` 会丢掉市场，
>   应改用 `get_prefix(c) + norm_ticker(c)` 得到 `sh000001` 再传。聚宽代码互转见下方 `to_joinquant()`（#55）。

| 输入 | 归一化结果 |
|------|-----------|
| `688017` | `688017` |
| `SH688017` / `sh688017` | `688017` |
| `688017.SH` / `688017.sh` | `688017` |
| `SZ000001` | `000001` |
| `BJ920982` | `920982` |
| `600519.XSHG` / `000001.XSHE`（聚宽写法，#55） | `600519` / `000001` |

三个代码转换 helper 现位于 [scripts/_ticker.py](scripts/_ticker.py)，仅用标准库。`em_market_code` 为沪=1、深/北=0；`em_secid` 保留显式市场并规范化代码；`to_joinquant` 不猜北交所后缀，仍报 ValueError。Python 路径初始化后导入：

```python
from _ticker import get_prefix, norm_ticker, em_market_code, em_secid, to_joinquant

# 用法
norm_ticker("SH600519")      # '600519'
norm_ticker("600519.SH")     # '600519'
norm_ticker("bj920982")      # '920982'
norm_ticker("sz000016")                      # '000016'（深康佳A，000 段的显式消歧，合法）
norm_ticker("600519.XSHG")                   # '600519'（聚宽写法，#55）
```

以下输入预期抛出 `ValueError`，用于说明校验边界，不属于上面的初始化代码：

| 调用 | 拒绝原因 |
|------|----------|
| `norm_ticker("6005190")` | 7 位代码，不截断 |
| `norm_ticker("茅台")` | 不是证券代码 |
| `norm_ticker("SH000001.SZ")` | 前后缀矛盾，不猜市场 |
| `norm_ticker("SH000001", stock_only=True)` | 上证指数，不是平安银行 |
| `norm_ticker("000001.SH", stock_only=True)` | 后缀写法同样拦下指数 |
| `norm_ticker("SZ600519")` | 600519 是沪市，与深市前缀矛盾 |
| `norm_ticker("600519.XSHE")` | 600519 是沪市，与聚宽深市后缀矛盾 |

### 东财数据中心统一查询（共用 helper）

业务 CLI 和业务函数会自动导入所需 helper；仅在 Python 中直接组合公共函数时，先执行上方路径初始化，再读 [公共 helper 导入与返回规则](references/research-workflows.md#shared-helpers)。其中保留完整导入块、重试配置、DataFrame 来源字段与错误处理说明。

- 东财已接入的请求使用 `em_get()`；默认最小间隔1秒并带抖动。调节时用 `import _eastmoney` 后修改 `_eastmoney.EM_MIN_INTERVAL`，不要仅修改导入到本地的同名变量。
- 状态只在同进程共享，没有线程锁或跨进程协调；保持串行。未接入限流的脚本例外见前面的「东财限流入口与调用方式」，降低频率也不保证免封禁。
- `eastmoney_datacenter()` 只取第一页，某些失败载荷可能返回空列表；严格分页与业务错误识别用 `_em_datacenter_strict()`。空结果不等于现实中没有数据，各业务入口的错误语义仍按对应章节核对。

---

## Layer 1: 行情层（实时与历史行情）

> **V3.10.0 起本层重排：能用的在前，2026-09 起失效的 mootdx 行情命令移到最后（§1.7，留档）。**
> 旧编号 → 新编号：1.2→1.1 腾讯实时、1.5→1.2 腾讯 K 线、1.6→1.3 通达信盘后包、1.3→1.5 百度、1.4→1.6 新浪复权因子、1.1→1.7 mootdx；
> §1.4 腾讯逐笔为新增。CHANGELOG 的历史版本说明里写的仍是旧编号。

### 1.1 腾讯财经 API — PE/PB/市值/换手率/涨跌停/指数/ETF

默认运行 `scripts/tencent_quote.py <代码...> --output <新文件.json>`。执行前按需读取 [CLI 参数、输出字段与 Python 调用](references/quotes-and-kline.md#quote)。

- 裸 `000001` 是平安银行；上证指数用 `sh000001`，二者可在同一次查询中返回。不要直接传后缀式代码。
- 核对返回代码是否齐全及 `is_stale`；空结果不是零价，陈旧报价须核查。成交额为万元，市值为亿元。
- 本 CLI 不返回五档盘口；需要五档时查「备用源速查」。批量代码合并查询，不逐只并发启动 CLI。
- `--output` 保存完整结果且不覆盖已有文件；终端仅前三条预览，分析须读文件。父目录须存在，等 CLI 成功退出后读取。

### 1.2 腾讯 K 线 — 日/周/月前后复权 + 1~60 分钟

默认运行 `scripts/tencent_kline.py <代码> [参数] --output <新文件.json>`。执行前读取 [周期、复权、日期范围与 CLI 示例](references/quotes-and-kline.md#kline)。

- 仅支持沪深；北交所日线用 §1.3。日/周/月默认前复权；不复权用 `--adjust none`。分钟线仅不复权、最近最多 320 根，不支持日期区间。
- 成交量单位为手；没有成交额，分钟字段 `turnover_rate_pct` 是换手率，不是成交额。需要成交额用 §1.3。
- 腾讯前复权可能产生非正价格并报错；长区间回测取不复权数据后按 §1.6 比例因子处理，不把原始价冒充复权价。
- 指定输出保存完整结果且不覆盖已有文件；终端仅前三条预览，须读完整文件。父目录须存在，等 CLI 成功退出后读取。
- 三入口轮换与冷却由脚本处理；同后端并非独立数据源。批量串行 Python 调用以共享冷却状态，重启 CLI 不继承状态。结构或数值校验失败须报告。

### 1.3 通达信官网盘后包 — 全市场某交易日日线

默认 CLI：`scripts/tdx_daily_package.py <交易日> --output <新文件.json>`。执行前读取 [参数、字段及完整性校验](references/market-data-details.md#daily-package)。

- HTTP 盘后包与失效的 mootdx TCP 行情是不同来源；返回不复权日线，个股量为股、金额为元，指数等特殊代码的量保留源值。
- 非交易日、尚未发布或历史 404 会失败，不能当作零成交；不保证所有历史日期覆盖。2022-05-06 前可能仅沪深，此后缺北交所文件会报错。
- 腾讯只能逐只补取沪深，不支持北交所，且无成交额，不能冒充完整沪深北全市场结果；降级须报告缺失市场、字段及日期覆盖。
- CLI 始终落盘；读完整文件，不把前三条预览当全市场。父目录须存在，不覆盖旧文件，等待成功退出再读取。

### 1.4 腾讯逐笔成交 — 最近交易日分笔明细

默认 CLI：`scripts/tencent_ticks.py <代码> --output <新文件.json>`。执行前读取 [分页、金额核对与缺笔标记](references/market-data-details.md#ticks)。

- 仅最近交易日的沪深个股和 ETF，不支持历史日期、指数或北交所；约三秒合并分笔，不是交易所 Level-2 逐笔。
- 量为手、金额为元；保留集合竞价及盘后定价。盘后金额不计入腾讯行情快照当日金额，不能直接拿全表金额与快照比较。
- 必须检查完整文件的 `attrs.missing_seq`：盘后缺笔仍可能返回，不能称全天完整；连续竞价段缺号或金额核对失败会报错。开盘前也可能取不到上一交易日数据。
- CLI 始终落盘；读取全部行和 attrs，不能只看前三条预览。父目录须存在，不覆盖旧文件，等成功退出再读；失败不得解释成无成交。

### 1.5 百度股市通 K 线 — 日线及 MA5/MA10/MA20

默认 CLI：`scripts/baidu_kline_with_ma.py <代码> --output <新文件.json>`。执行前读取 [字段解析、start-time 与失败处理](references/market-data-details.md#baidu)。

- 固定日线，不承诺分钟、指数/ETF 或分页；代码原样传递，`--start-time` 不做日期转换。
- 返回 keys 和未解析的 rows 字符串；保留空行，`row_count` 不等于有效 K 线根数。按 keys 解析、核对日期后使用。
- `hit risk`、验证码、业务错误或空白数据是失败，不能当正常零条行情；按备用源处理并保留缺失说明。
- CLI 始终落盘，读完整文件；父目录须存在，不覆盖已有文件，等待成功退出再读。

### 1.6 新浪复权因子 — qfq / hfq

默认 CLI：`scripts/sina_adjust.py factors <代码> --kind qfq` 取因子，`scripts/sina_adjust.py apply --bars <原始价列表.json> --factors <因子列表.json> --kind qfq` 计算。执行前读取 [输入格式、计算方向及示例](references/market-data-details.md#adjust)。

- 输入必须是不复权价格；其他行情 CLI 的封装文件须先提取 `data` 对象列表，不能直接传整个 columns/attrs/data 文件。
- qfq 做除法，hfq 做乘法；因子文件不携带种类，两步 `--kind` 必须一致，不自动推断。默认仅改价格，不改量额。
- 新浪 hfq 与其他源可能有不同基准，不能直接比价格绝对值。北交所无可用因子，不把不复权日线说成已复权。
- 空因子、日期早于最早因子、零因子会失败，不继续使用未复权值充当成功结果。CLI 始终保存完整新文件；父目录须存在，等成功退出再读。

### 1.7 mootdx — 行情命令失效留档

文档记录 2026-09 起 `bars / quotes / transaction` 普遍返回空，测速可能约一分钟后失败；不要作为默认行情源。实时价用 §1.1、沪深 K 线用 §1.2、全市场日线用 §1.3、最近交易日分笔用 §1.4；五档查「备用源速查」。

财务与 F10 仍走 §6.1 / §6.2 / §7.2，对应 CLI `scripts/tdx_client.py finance / F10C / F10` 自动使用 finance 验活。仅维护旧调用或核查历史参数时读 [mootdx CLI、频率表与 Python 留档](references/market-data-details.md#mootdx)，不要顺序执行留档行情示例。

---

## Layer 2: 研报层

### 2.1 东财研报 API — 个股/行业列表与 PDF

默认 CLI：`scripts/eastmoney_reports.py stock <代码>`；行业用 `industry <行业码或 '*'>`；PDF 用 `pdf <单条记录.json> --target-dir <目录>`。执行前读 [分页、字段与 PDF 保存规则](references/research-reports.md#eastmoney)。

- 免费无 Key；行业码从 `industry '*'` 结果的 industryName/industryCode 查找，不猜通用行业码。
- 列表某些错误载荷也可能返回空，不能直接断言无研报；页数上限也不代表已取全。北交所废旧码需核查现行代码。
- PDF 输入为接口的一条完整原记录，不是列表或任意 JSON。原函数复用同名文件，不验证 PDF 文件头/已有内容；异常 publishDate 路径字符还可能使文件逸出目标目录，须核查，退出成功不证明 PDF 有效。
- stock/industry 完整列表落盘，stdout 仅前三条预览；`--output` 不覆盖旧文件且父目录须存在。PDF 没有列表文件的独占发布/失败清理保证。
- 东财共享限流仅限同进程；串行调用，`--min-interval` 可调大、不能小于 1 秒；不要并发启动 CLI 绕过间隔。
- 个股或全市场研报列表失败时可尝试 §2.4，并说明字段缺失；新浪入口不提供东财行业码筛选或 PDF 下载，不能等价替代这两类任务。

### 2.2 同花顺一致预期 EPS

默认 CLI：`scripts/ths_eps_forecast.py <代码> --output <新文件.json>`。执行前读 [表格识别、输出结构及 Python 用法](references/research-reports.md#eps)。

- 需要 requests、pandas、HTML 解析器（推荐 lxml）。首张表回退不保证是 EPS，空结果/反爬页面不证明无机构预测；核查表头与内容，机构数少于 3 时谨慎使用。
- 完整表落盘，data 是按 columns 排列的行数组；保留重复列、多层表头/索引和缺失值标记，不能当普通 record 列表解析。
- 父目录须存在、不覆盖已有文件，成功退出后读完整文件；不能只用终端前三行预览。

### 2.3 iwencai — 自然语言主题搜索与本地去重

默认 CLI：`scripts/iwencai.py search <主题> --channel report --size 50`；本地去重用 `dedup <列表.json>`。执行前读 [鉴权、query、去重规则与 extra 解析](references/research-reports.md#iwencai)。

- 按标的优先 §2.1；跨主题语义搜索用本节。远程 search/query 需要 API Key 和 X-Claw Headers，由脚本处理；环境配置在导入时读取，修改后重启进程。本地 dedup 无需 Key 或网络。
- 默认搜索不去重；`--dedup` 或 dedup 命令才去重。同 uid 留最高 score，空 uid 按 title+publish_date 分组，同分留先出现者，结果按日期倒序；extra 可能是字符串或对象。
- 空 data/datas 不证明数据覆盖；失败不当作正常无结果。完整结果落盘，父目录须存在、不覆盖旧文件，成功退出后读完整文件。

### 2.4 新浪研报列表 — 东财之外的备用源

默认 CLI：`scripts/sina_reports.py [代码] --page <页码> --output <新文件.json>`。执行前读 [分页、限流与返回字段](references/research-reports.md#sina)。

- 不传代码取全市场，传代码取该证券；支持北交所代码。仅指定单页，不自动翻页。
- 返回标题、类型、日期、机构、研究员和详情链接，**没有评级和目标价**；不能把备用源说成字段完整替代。
- 同进程请求间隔 6 秒，空页重试一次后仍可能是限流；不能据空页断言无研报。批量分页在同一进程串行调用，不并发启动 CLI。
- 完整 DataFrame JSON 落盘，保留空表列定义；父目录须存在、不覆盖旧文件，成功退出后读文件和全部数据，stdout 仅前三行预览。

---

## Layer 3: 信号层

### 3.1 同花顺热点 — 当日强势股与题材归因

默认 CLI：`scripts/ths_hot_reason.py --date <日期> --output <新文件.json>`。执行前读 [日期、字段与输出格式](references/signals-realtime.md#hot)。

- 省略日期用本机今天；单次取指定日期，不分页。题材归因是来源人工标签，不等于已证实的涨价原因。
- 价格/涨幅字符串及题材标签保持原样；量为股、金额为元。完整 JSON 的 data 为按 columns 排列的行数组，保留额外字段。
- 空载荷可能是接口异常，不能断言当天无热点；无列空表不能直接按列索引。完整结果落盘、不覆盖旧文件，父目录须存在，成功退出后读全文件，不能仅看前三行预览。

<a id="northbound-data"></a>

### 3.2 同花顺北向资金 — 当日分钟流向与本地已保存历史

默认 CLI：`scripts/northbound.py realtime --output <新文件.json>` 查分钟流向，`history --count <条数> --output <新文件.json>` 查本地历史。执行前读 [字段、日期与缓存规则](references/signals-realtime.md#northbound)。

- 查询不会自动积累历史，history 不补抓；检查实际日期覆盖，少量记录不能代表一年。hgt 用于情绪参考，sgt 可能稀疏或不可靠；不同时间的末值不拼成同步合计，空值不当零，权威数据见备用源 HKEX 日统计。
- 金额单位亿元；接口仅有时刻，不能可靠推断交易日期。最后完整分钟点不保证收盘值，sgt 缺失时可能早于最新 hgt。
- 只有需要积累历史时才用 `realtime --save-date <核实日期>` 或 `save <日期> --hgt <值> --sgt <值>`；后者不联网。详见 reference 的独立保存示例，不把 JSON 导出当作日历史保存。
- 默认 CSV 位于 `~/.tradingagents/cache/northbound_daily.csv`，同日替换；访问路径会创建父目录，CSV 直接覆写、无并发锁/原子发布/回滚，须串行。CSV 更新与 JSON 导出不是同一事务，导出失败不撤销缓存更新。
- realtime/history 完整表落盘，data 为行数组；父目录须存在，不覆盖 JSON，成功退出后读全部数据，stdout 仅前三行预览。成功不证明源数据有效。

### 3.3 东财 slist — 个股板块/概念归属

默认 CLI：`scripts/eastmoney_signals.py boards <纯六位代码> --output <新文件.json>`。执行前读 [代码格式、板块字段及失败语义](references/signals-realtime.md#boards)。

- 行业、概念、地域混在同一个列表，concept_tags 包含全部板块名，不是精确分类。不要直接传带市场前后缀的代码。
- 单页最多请求 200 条、不分页；total 是实际返回数，不保证全量覆盖。保留源顺序和字段类型。
- 请求/JSON 解析 WARN 会使 CLI 非零退出且不落盘；正常空响应仍可能成功，缺少 HTTP/业务状态验证，不能仅据退出码断言数据有效。
- 共用东财限流，仅同进程串行生效；`--min-interval` 至少 1 秒。完整 JSON 落盘、不覆盖，父目录须存在，成功退出后读全文件而非三条预览。

### 3.4 东财 push2 — 个股分钟资金流

默认 CLI：`scripts/eastmoney_signals.py minute <代码> --output <新文件.json>`。执行前读 [市场代码、字段、单位及原始示例](references/signals-realtime.md#minute)。

- 支持前后缀/聚宽代码并保留市场；正确路由不保证 ETF 有个股资金流覆盖。日级数据见 §4.5。
- time/main_net/small_net/mid_net/large_net/super_net 的金额单位为元；保留源顺序，不新增日期过滤、分页或汇总。跨时间合计前须核实字段是期间量还是累计值，不能仅凭“分钟”名称直接求和。
- 请求/JSON 解析 WARN 使 CLI 非零退出且不落盘；正常空载荷仍可能成功，空结果不是零流入。坏数值会报错，非有限值以 $float 标记，不当普通有效金额。
- 共用东财限流，仅同进程串行生效；完整文件不覆盖、父目录须存在，成功退出后读全部数据，stdout 仅前三条预览。

### 3.5 龙虎榜席位 — 个股记录与买卖席位

CLI：`scripts/eastmoney_signals.py dragon <截止日> <纯六位代码> --look-back 30`。执行前读 [记录、席位和机构统计口径](references/signals-ranking.md#dragon)。回看按日历天，单页最多 50 条；席位仅对应首条记录日期，展示前 5 条不等于机构统计范围。金额为万元；空记录不证明未上榜，不承诺完整历史或全部席位。

### 3.6 限售解禁日历

CLI：`scripts/eastmoney_signals.py lockup <起点日期> <纯六位代码> --forward-days 90`。执行前读 [日期范围、份额及比例单位](references/signals-ranking.md#lockup)。history 未限制日期，可能含未来记录（单页 15 条）；upcoming 含起止日、单页 20 条，两组可重叠。量为万股，ratio 为小数比例，百分比须 ×100；空结果不证明无解禁。

### 3.7 行业板块涨幅排名

CLI：`scripts/eastmoney_signals.py industry --top-n 20`。执行前读 [排序、切片和覆盖范围](references/signals-ranking.md#industry)。完整分页后排名；total 是服务端总数，fetched_count 为取得数，缺失涨幅单列 missing，不参与排名。bottom 保留涨幅倒序，最后一条最弱；不完整或重复分页直接失败。涨幅排名不证明资金流入，资金字段用 §3.8。

“最近哪些行业/概念涨得好”用 `scripts/eastmoney_signals.py board-quotes --board-type concept --period 5d --top-n 20`（today/5d），按涨幅排名。默认 push2 失败后可串行尝试一次 `--source dataapi`；仍失败就报告缺口，不轮询多个域名。备用接口同属东财，仅提供代码/名称/涨幅，其他字段为空。两源均输出来源、抓取时间和覆盖数；quote_time=null 表示未提供行情时间，不能把抓取时间当交易日。

### 3.8 板块资金流向

CLI：`scripts/eastmoney_signals.py board-flow --board-type concept --period 5d --top-n 250`。执行前读 [周期、分页与字段差异](references/signals-ranking.md#board-flow)。类型 industry/concept/region，周期 today/5d/10d，无 3d；金额为元、main_pct 为百分数。只有 today 含四档金额，10d 无领涨股字段；total 不等于实际 rows 数。与行业涨幅同源，不是独立备用源。

### 3.9 全市场龙虎榜

CLI：`scripts/eastmoney_signals.py daily-dragon --date <交易日> --min-net-buy 5000`。执行前读 [筛选边界、日期和重复记录](references/signals-ranking.md#daily-dragon)。默认本机当天，不自动找交易日；单页最多 500 条，不分页或按股票去重。同股不同原因保留，记录数不等于股票数；门槛单位万元、按未舍入值 ≥ 筛选。空数据和 note 都不能证明未上榜。

**§3.5–§3.9 执行规则：** 用 `--output <新文件.json>` 保存完整结果，父目录须存在，不覆盖旧文件；成功退出后读全文件，不能只看前三条预览。东财请求串行执行，`--min-interval` 至少 1 秒、仅同进程共享；失败非零退出，不把空载荷当有效覆盖。

### 3.10 信号层组合用法：题材、北向与行业资金分别观察

需要组合观察时读 [可独立导入的 Python 示例](references/signals-ranking.md#workflow)。分别呈现题材标签频次、北向各通道带时刻的有效点、行业涨幅和行业资金字段；先核对日期与覆盖，不把北向末值叫收盘值，不把缺失当零，不用涨幅替代资金流，不宣称题材因果关系。示例不写北向日历史。

---

## Layer 4: 资金面 / 筹码层（V3.0 新增）

**§4.1–§4.5 共用执行边界：** 东财入口使用纯六位代码；串行调用，`--min-interval` 至少 1 秒，仅同进程共享。完整结果用 `--output <新文件.json>` 落盘，不覆盖，父目录须存在；等成功退出后读取全文件，不把三条预览当全部数据。空载荷不证明无记录，缺失/非有限值不当有效零；详细字段与原有异常处理见各 reference。

### 4.1 融资融券明细

CLI：`scripts/eastmoney_signals.py margin <代码>`。执行前读 [字段与单位](references/capital-and-chips.md#margin)。默认按日期倒序单页 30 条，`--page-size` 不代表自动分页；融资/融券余额为元，数量字段不是金额。缺失字段默认 0、显式 None 保留，不混同真实零余额。

### 4.2 大宗交易

CLI：`scripts/eastmoney_signals.py block <代码>`。执行前读 [价格、溢价及原始量额字段](references/capital-and-chips.md#block)。默认倒序单页 20 条；close 为 0 时脚本溢价默认 0，不代表真实平价。vol/amount 不做单位换算或字符串解析，使用前核对源口径。

### 4.3 股东户数变化

CLI：`scripts/eastmoney_signals.py holders <代码>`。执行前读 [日期、变化比例与覆盖限制](references/capital-and-chips.md#holders)。默认倒序单页 10 条，不额外补抓历史；change_ratio 已是百分数，不再 ×100。户数减少仅描述持有人数量变化，不能单独证明主力吸筹。

### 4.4 分红送转历史

CLI：`scripts/eastmoney_signals.py dividends <代码>`。执行前读 [派息、转增、送股及方案进度](references/capital-and-chips.md#dividends)。默认按除权日倒序单页 20 条；日期可为空，未按除权日或方案进度过滤，不把全部记录视为已实施。原数值直接映射，计算前核对每股/每十股口径。

### 4.5 个股日级资金流

CLI：`scripts/eastmoney_signals.py stock-flow <代码>`。执行前读 [120条请求、缺失转换和日期顺序](references/capital-and-chips.md#stock-flow)。金额为元，请求 lmt=120 不保证120个有效交易日；保留源顺序及重复日期。原始 '-' 会转成0，不能证明真实零流入；其余非法数值报错。近20日计算前核实日期、排序、重复及覆盖，不能仅凭列表尾部位置认定最近20日。腾讯K线或盘后包只补量价，不等价补齐主力资金流字段。

### 4.6 筹码分布 CYQ — 本地模型推演

CLI：`scripts/chip_distribution.py <本地CSV或JSON> --grid-size 300 --decay 1.0 --output <新文件.json>`。执行前读 [输入准备、模型与指标边界](references/capital-and-chips.md#chips)。

- 本地计算，不自动联网取数；输入含 date/high/low/close/turn，日期 YYYY-MM-DD，数值列为数值，turn 为百分数（0.31 即0.31%）。须先准备前复权价格并过滤停牌，CLI 不代做。
- 模型按日期排序，缺失行可能丢弃，初始筹码与历史窗口会影响结果；不是实测持仓，不能把模型获利比例当成真实账户获利人数比例。
- profit_ratio 为0–1比例，展示百分比 ×100；完整网格用于均值/分位数，histogram 仅保留权重>1e-6的点，不当无损完整网格。均值/中位数关系及筹码峰是否落在成本区间是启发式，不能据此否定合法结果。
- 完整指标和histogram保存新文件，stdout仅直方图前三点；父目录须存在，不覆盖，成功退出后读完整文件。

### 4.7 ETF 份额 — 沪市日归档与深市当前快照

CLI：`scripts/etf_shares.py <日期> --exchange SH --output <新文件.json>`（深市用 SZ）。执行前读 [两所日期能力、分页校验与字段](references/capital-and-chips.md#etf)。

- 单位万份；沪市可按历史日期查，深市只有最新快照，日期不匹配会报错，历史须自行留存；深市T日晚预估、T+1早确认。
- 两所类别字段不同，不强行合并。沪市单页校验total，深市完整分页并检查快照一致；缺字段、重复代码、数量或日期不符会失败，不输出部分快照或将失败当空表。
- 完整DataFrame JSON落盘，data为按columns排列的行数组，保留来源/抓取时间；文件不覆盖，父目录须存在，成功退出后读全量数据。

---

## Layer 5: 新闻层

**执行边界：** 成功退出后读取完整输出文件，stdout 仅前三条预览；已有文件不覆盖。§5.1–§5.3 保存列表，§5.4–§5.5 保存 DataFrame JSON（按 columns 解释 data，保留 attrs）。异常非零退出；前三节未校验全部 HTTP/业务成功状态，空列表不能证明没有新闻。东财两个入口串行调用，`--min-interval` 至少1秒、仅同进程共享；财联社为独立请求。

### 5.1 东财个股新闻

CLI：`scripts/market_news.py stock <代码> --output <新文件.json>`。执行前读 [查询与摘要边界](references/news.md#stock)。默认20条、第一页、相关性排序，不保证最新或全量；代码原样作为关键词。正文去标签后截200字符，不是新闻全文；time/source/url 保留源值。

### 5.2 财联社快讯

CLI：`scripts/market_news.py cls --output <新文件.json>`。执行前读 [签名、时间与字段](references/news.md#cls)。默认50条，签名本地计算、无需 Key；正文不截断，title/content 为空时回退 brief。时间按运行机器的本地时区转换，不能直接当北京时间。与东财是独立请求源，不能保证备用源始终可用或新闻逐条对应。

### 5.3 东财全球资讯（7×24）

CLI：`scripts/market_news.py global --output <新文件.json>`。执行前读 [摘要与输出规则](references/news.md#global)。默认50条，summary 截200字符，时间保留源值；不自动翻页、去重或合并。全市场快讯失败时可尝试财联社或见闻，需说明来源、时间及覆盖变化；不能替代个股检索或保证补全原新闻。

### 5.4 华尔街见闻快讯

CLI：`scripts/news_sources.py wscn --channel a-stock-channel --limit 50 --output <新文件.json>`。执行前读 [频道、翻页和字段校验](references/news.md#wscn)。常用 global-channel / a-stock-channel，limit 1–100，时间为 UTC+8。下一页用完整输出 attrs.next_cursor 显式传 `--cursor`，不自动翻页或去重；importance 为源 score，空条目或格式错误失败。依赖 requests、pandas，前三节只需 requests。

### 5.5 央视《新闻联播》文字稿

CLI：`scripts/news_sources.py cctv <YYYY-MM-DD> --titles-only --output <新文件.json>`。执行前读 [日期、正文和缺失边界](references/news.md#cctv)。默认抓逐条正文；仅需标题时用 --titles-only，此时没有 content 列。旧视频正文可能为 None，未发布或页面结构异常会报错；不保存部分抓取为成功。政策研究用途；保留原使用约束：不用于短视频文案引用。

---

## Layer 6: 基础数据层

**执行边界：** CLI 成功退出后读取完整输出，终端预览不代表全部；已有文件不覆盖。表格 JSON 按 columns 解释 data，保留 dtype/index/attrs；空值或默认值不代表有效数据。快照与历史序列分开使用，报告期也不等于信息当时已公开；回测另核对披露时间和历史样本范围。

### 6.1 mootdx 财务快照

CLI：`scripts/tdx_client.py finance --params '{"symbol":"688017"}' --output <新文件.json>`。执行前读 [财务字段与验活](references/company-and-history.md#finance)。CLI 默认按 finance 验活；Python 用 `tdx_client(check='finance')`，不要用失效的 K 线验活判断财务不可用。这是季报财务快照，不是历史财报序列；三表取数见 §6.4。

### 6.2 mootdx F10 公司文本

CLI：`scripts/tdx_client.py F10C --params '{"symbol":"688017"}' --output <新文件.json>` 列出类别，再用 `F10 --params '{"symbol":"688017","name":"实际类别名"}'` 取正文。执行前读 [类别限制及替代入口](references/company-and-history.md#f10)。不要写死旧类别；原实测仅剩“最新提示”，缺少的公司/财务/股东信息按 reference 路由另取。

### 6.3 东财当前基本面

CLI：`scripts/company_data.py info <六位代码> --output <新文件.json>`。执行前读 [股本、市值与缺失值](references/company-and-history.md#info)。股本为股、市值为元，原值不强制转数值；上市日期可能为空串或字符串 "None"。不自动剥离代码前后缀；东财 `--min-interval` 至少1秒，同进程共享。默认值字典不证明成功取得有效基本面。

### 6.4 新浪财报三表

CLI：`scripts/company_data.py finance <六位代码> --report-type lrb --num 8 --output <新文件.json>`。执行前读 [报告期、科目值与覆盖](references/company-and-history.md#statements)。fzb/lrb/llb 对应资产负债表/利润表/现金流量表，默认最近8期，不自动翻页。数值字符串与同比原值保留，分析前核对单位和期间口径；空结果不证明无财报。新浪独立请求，不使用东财限流参数。

### 6.5 baostock 历史估值与交易状态

CLI：`scripts/baostock_data.py valuation <六位代码> <开始日期> <结束日期> --output <新文件.json>`。执行前读 [历史估值、换手率及状态](references/company-and-history.md#valuation)。依赖 baostock、pandas；不支持北交所，传正确纯六位代码。日频价格不复权，turn 为百分数（0.31 即0.31%），tradestatus/isST 为字符串。部分数值无效会转缺失，不自动过滤停牌/ST；筹码计算须另准备前复权价格。历史状态不能用当前快照替代。

### 6.6 baostock 上市/退市信息

CLI：`scripts/baostock_data.py basic <六位代码> --output <新文件.json>`。执行前读 [状态、日期及源覆盖限制](references/company-and-history.md#basic)。只返回首行字典，空表为 {}；日期/type/status 保留字符串，空 outDate 不转 None。历史样本按当时状态确定，不能用今天的退市名单删除历史样本。

### 6.7 申万历史行业归属

CLI：`scripts/sw_industry.py history --output <新文件.json>`；单次查询用 `scripts/sw_industry.py as-of <六位代码> <YYYY-MM-DD> --output <新文件.json>`。执行前读 [分类体系、排序与日期匹配](references/company-and-history.md#industry)。返回行业代码，不补中文名，不套用东财或通达信名称。调整日当天采用新归属，无匹配返回 null；Python as_of 不自行排序，应复用 history 返回的升序表。批量按日研究先下载一次再复用，避免重复下载；依赖 requests、pandas 和 Excel 引擎。

### 6.8 当前 ST / *ST 名单

CLI：`scripts/st_list.py --output <新文件.json>`。执行前读 [主源、延迟域与降级损失](references/company-and-history.md#st)。主源含沪深风险警示板及北交所名称筛选；延迟域价格约滞后15分钟。仅两域网络/HTTP异常均失败才降到 baostock，此时仅沪深且没有价格，必须读取 attrs.coverage/fallback_reason；业务错误或不完整分页不能当成功名单。历史 ST 状态用 §6.5 的 isST，本接口是当前快照。

---

## Layer 7: 公告层

### 7.1 巨潮公告列表

CLI：`scripts/cninfo_announcements.py <六位代码> --page-size 30 --output <新文件.json>`。执行前读 [orgId、日期与输出限制](references/announcements.md#cninfo)。默认仅第一页30条，不自动翻页；代码不自动去除前后缀。返回标题/类型/日期/详情页链接，不返回公告正文，url 不是 PDF 下载地址；需要全文时须继续读取实际公告。

- orgId 优先取官方映射，同一进程复用非空缓存；映射失败警告后仍按旧规则查询，空结果不能证明无公告或查询完整。毫秒时间戳按运行机器本地时区转换，不能直接假设北京时间。
- 成功后读取完整 JSON，stdout 只预览前三条；已有输出不覆盖，异常非零退出。原接口不校验全部 HTTP/业务状态，成功保存空列表也不证明上游请求有效。

### 7.2 mootdx F10 公告摘要

CLI：`scripts/tdx_client.py F10 --params '{"symbol":"688017","name":"最新提示"}' --output <新文件.json>`。执行前读 [摘要调用与输出](references/announcements.md#f10)，类别不确定时先按 §6.2 用 F10C 查询。CLI 默认 finance 验活；Python 用 `tdx_client(check='finance')`。本入口是近期摘要，不是公告全文或完整历史，不能等价补齐巨潮缺失记录。

---

## Layer 8: 打板层（涨停 / 炸板 / 跌停 / 题材情绪，V3.3.0 新增）

**执行边界：** 本层统一用 `scripts/limit_pools.py`，依赖 requests。成功退出后读完整 JSON，stdout 多为前三条预览；已有文件不覆盖。四池共用东财同进程限流，本 CLI 没有 --min-interval 参数，不要并发多进程绕过限流。CLI 捕获 WARN 后失败且不保存；无 WARN 的空载荷也不证明上游数据完整有效。

### 8.1 涨停 / 炸板 / 跌停 / 昨日涨停四池

CLI：`scripts/limit_pools.py <zt|zb|dt|yzt> <YYYYMMDD> --output <新文件.json>`。执行前读 [字段、单位与空池边界](references/limit-and-anomaly.md#pools)。交易日参数原样传入，单次请求最多 pagesize=10000，不自动翻页；保留源顺序。价格已÷1000，金额/市值为元，涨幅/换手按源字段处理；空结果不能证明当天无涨跌停。

### 8.2 同花顺涨停原因与板型

CLI：`scripts/limit_pools.py ths <YYYYMMDD> --output <新文件.json>`。执行前读 [题材、封板率与时间字段](references/limit-and-anomaly.md#reasons)。仅第一页、limit=200，不自动翻页；价格/封板率等保留源值，first_time 由 Unix 秒按机器本地时区转换。同花顺可补充题材，不保证与东财池覆盖一致。

### 8.3 炸板率 / 连板高度 / 梯队

CLI：`scripts/limit_pools.py sentiment <YYYYMMDD> --output <新文件.json>`。执行前读 [公式、失败处理和晋级率限制](references/limit-and-anomaly.md#sentiment)。依次取涨停、炸板、跌停；炸板率为炸板数/(涨停数+炸板数)×100，默认分母0时返回0，不能据此判断有效0%。任一池 WARN 则 CLI 失败；Python 原函数会继续算，组合调用须检查诊断。三池非原子快照，核对日期/覆盖/观察时点后再解读；ladder 的 JSON 为 `{"$map": [[板数, 家数], ...]}`。晋级率另按昨涨停与今日涨停集合匹配，不能统一用涨幅阈值代替涨停身份。

### 8.4 重点监控名单

CLI：`scripts/limit_pools.py monitor --output <新文件.json>`；需包含未生效/过期记录加 --all。执行前读 [生效窗口与市场字段](references/limit-and-anomaly.md#monitor)。默认按北京时间今天筛选 start≤today≤end，两端包含；源日期字符串直接比较。市场1/0/B映射SH/SZ/BJ，未知保留标记；空返回不等于确认无人被监控。

### 8.5 日内异动明细与次数

CLI：`scripts/limit_pools.py anomaly --page-size 200 --page-no 1 --output <新文件.json>`；次数统计用 `anomaly-count --page-size 50 --page-no 1 --sort-key "" --sort-dir ""`。执行前读 [分页、规则与跨端点字段](references/limit-and-anomaly.md#anomaly)。仅指定页，保存date/pages/items，按pages判断是否需继续取页。非交易时段日期可能是上一交易日；两个端点的t分别是涨跌幅目标和异动次数，不能混用。与当前监控名单交叉须核对日期，重合不等于“最高风险”。

---

## Layer 9: ETF 期权层（T型报价 + 希腊字母 + IV，V3.3.0 新增）

### 9.1 合约清单、单合约报价与希腊字母

统一入口 `scripts/sina_options.py`，依赖 requests。执行前读 [ETF期权详细说明](references/etf-options.md)，其中包含合约月份、认购认沽参数、报价/希腊字母字段和单合约查询示例：

- 合约清单：`codes --underlying 510050 --output <新文件.json>`，默认认购，加 --put 取认沽。已映射标的为510050/510300/588000/510500；未知标的的回退行为不代表支持。保留源月份和合约顺序，不据首月或中间合约推断近月、平值。
- 单合约：`quote <合约代码> --output <新文件.json>`；希腊字母：`greeks <合约代码> --output <新文件.json>`。完整 T 型链需自行按月份、行权价及合约规格配对认购/认沽，本 CLI 不自动配对。
- IV 为源返回小数（0.1735即17.35%），展示时才转百分比；不本地计算BSM。部分数值转换失败会保留字符串；短报价可返回 {}，缺失/非有限值不作0，格式化前核验。
- 成功后读完整文件；codes 终端仅前三个月、每月前三个合约预览，quote/greeks 完整预览。月份请求 WARN 导致 CLI 非零退出且不保存，但无 WARN 的空对象也不能证明数据有效。已有输出不覆盖；请求独立于东财，GBK/Referer由脚本处理。

---

## Layer 10: 舆情互动层（互动易问答 + 热榜 + 人气榜，V3.3.0 新增）

**解读边界：** 分清投资者提问与公司回复，未回复不补写；引用回复前读取完整字段，不用终端预览作全文。平台热度、概念命中不能直接证明资金流向或涨跌原因，也不跨平台直接比较热度数值。

### 10.1 深市互动易问答

CLI：`scripts/investor_sentiment.py irm <六位代码> --page-size 30 --page-num 1 --output <新文件.json>`。执行前读 [查询、未回复和时区](references/interaction-and-popularity.md#irm)。依赖 requests，默认一页30条，不自动翻页；首次查询取首条secid，使用前核对返回公司/代码。answer=None保留，时间按机器本地时区转换。沪市走§10.3，北交所不在这两个入口的支持范围。

### 10.2 同花顺热榜 / 东财人气榜 / 概念命中

CLI：`scripts/investor_sentiment.py ths --period hour --output <新文件.json>`（可用day）；`rank --top 50 --output <新文件.json>`；`concepts <六位代码> --output <新文件.json>`。执行前读 [排名、补价和概念字段](references/interaction-and-popularity.md#ranking)。保留源顺序、重复项与字段类型，不默认首条rank=1；top只传源，不本地截断。补价记录缺失时保留空名称及None价格/涨幅，概念不作本地热度排序；旧市场映射不能保证北交所/未知前缀正确。三个请求未走em_get，无本CLI限流参数。

§10.1–§10.2完整列表保存，stdout前三条预览；请求WARN导致CLI失败、不保存，但无WARN空列表仍不能证明没有数据。Python原函数会WARN后返回[]，组合调用须检查诊断；已有文件不覆盖。

### 10.3 沪市上证e互动

CLI：`scripts/sse_interaction.py --code <沪市代码> --kind questions --page 1 --page-size 10 --output <新文件.json>`；省略--code看平台全市场，--kind answered取已回复。执行前读 [近期覆盖、uid缓存和正文解析](references/interaction-and-popularity.md#sse)。依赖 requests、pandas；页码≥1、每页1–50，不自动翻页。公司维度原实测约近一个月，不保证完整历史；首次定位uid请求较多，同进程缓存可复用，独立CLI不共享。

返回表格JSON，按columns解释data，保留attrs来源/抓取时间；未回复answer/answer_time为None。明确“暂无”才允许空表；结构变化、公司记录错配或回复关键字段缺失报错，不保存部分结果。成功后读完整文件，终端仅前三行，已有输出不覆盖。

---

## Layer 11: 宏观与利率层（社融 / PMI / 收益率曲线 / 回购利率 / LPR / 宏观日历）

**执行边界：** 统一入口 `scripts/macro_data.py`，依赖 requests、pandas；社融另需 Excel 引擎。各节频率不同，统计期不等于发布日期；回测需核验当时已公开的信息和修订情况。成功后读完整JSON，表格按columns解释data，保留attrs；终端一般仅前三行，PMI为完整字典。已有文件不覆盖，异常非零退出不保存。

### 11.1 社会融资规模增量

CLI：`scripts/macro_data.py social-financing --year 2024 --output <新文件.json>`，省略--year取索引最大年份。执行前读 [月份解析、覆盖和年度合计](references/macro-and-rates.md#financing)。2021年起版式，金额亿元；丢弃总量为空的月份，其他数值可能缺失，不自动排序/去重。全年合计先核实目标年12个不同月份及数值完整性，未发布或缺失不能当0。

### 11.2 最新 PMI

CLI：`scripts/macro_data.py pmi --output <新文件.json>`。执行前读 [最新页面及指标口径](references/macro-and-rates.md#pmi)。取索引首个匹配发布页，不是历史序列；指数49.2原样保留，不除100。制造业/非制造业/综合主指标缺失报错，规模分档可为None，period也可能缺失；不能据单期数据判断连续趋势。

### 11.3 中债收益率曲线

CLI：`scripts/macro_data.py yield-curve <开始日期> --end <结束日期> --curve all --output <新文件.json>`。执行前读 [曲线起点、切片与完整性边界](references/macro-and-rates.md#yield)。单位%，按360天切片；三条曲线起点不同，中短票无30年档。all校验返回日期内应有曲线，不保证所有交易日均已返回；整天缺失须另用适用日历核对。省略end取机器本地当天。

### 11.4 回购定盘利率 FR / FDR

CLI：`scripts/macro_data.py repo-fixing --kind FR --output <新文件.json>`，银银间用FDR。执行前读 [期限、CSV和历史覆盖](references/macro-and-rates.md#repo)。日频、单位%，各含001/007/014三档；原源历史窗口不同，覆盖以返回日期为准。三档均必需，缺失/非有限/重复日期报错；不自动补历史或证明交易日完整。

### 11.5 LPR 历史

CLI：`scripts/macro_data.py lpr --output <新文件.json>`。执行前读 [历史机制、字段过滤与分页上限](references/macro-and-rates.md#lpr)。利率单位%，旧机制1年期与改革后记录区分使用，早期5年期可缺失。按LPR1Y字段排除基准利率行，不按年份删除；默认最多5000条，并非无限历史。实际报价日期看源记录，不写死每月某日。

### 11.6 全球宏观日历

CLI：`scripts/macro_data.py calendar <开始日期> --end <结束日期> --country 中国 --min-importance 3 --output <新文件.json>`。执行前读 [窗口、过滤和公布值](references/macro-and-rates.md#calendar)。北京时间，含两端最多92天、按7天切片，end默认start后6天。country精确匹配、importance 1–4；过滤前校验原始记录，结果空报错。actual/forecast/previous/revised可缺失，0保留；区分data/event及未知类型，公布值缺失不等于0或事件未发生。

---

## Layer 12: 指数与交易日历（V3.8.0）

统一入口 `scripts/official_data.py`，依赖 requests、pandas 及 Excel 引擎。执行前读 [指数与交易日历详细说明](references/index-and-calendar.md)，其中包含成分、权重、估值和日历的来源契约、日期边界及完整示例。指数代码必须为六位纯数字，不能按股票代码解释；csi为中证、cni为国证。

### 12.1 指数成分

CLI：`scripts/official_data.py constituents <指数代码> --provider csi --output <新文件.json>`。最近发布的沪深北成分快照，日期看date，不看抓取时间；不支持的证券市场会报错。国证download-history同样只提供本入口取得的单个月末快照，不能用于还原任意历史时点。

### 12.2 指数权重

CLI：`scripts/official_data.py weights <指数代码> --provider cni --output <新文件.json>`（中证用csi）。weight_percent=0.433表示0.433%，不是43.3%；原实现校验每项0–100、合计99–101。成分和权重可能不同日，核对指数、来源、日期后按证券身份匹配，不按行号拼接或改标为今天。

### 12.3 中证指数估值

CLI：`scripts/official_data.py valuation <指数代码> --output <新文件.json>`。提供总股本/计算用股本两套PE与股息率，不混用；不含PB、不承诺全历史，缺失值保留缺失。结果按日期排序，不能把最新估值替代历史值。

### 12.4 深交所整月交易日历

CLI：`scripts/official_data.py calendar <年> <月> --output <新文件.json>`。逐日返回is_open，不按工作日推断；未发布、缺日、跨月或重复日期报错，不当作全月休市。来源为深交所，不自动扩展到债券、期货或境外市场日历。

四类CLI均保存完整DataFrame及来源信息，按columns解释data；终端仅前三行。成功后读取完整文件，已有路径不覆盖，异常非零退出且不生成结果文件。当前成分/权重不替代历史成分。

## Layer 13: 期货与大宗商品（V3.9.0 新增 · #49）

统一入口 `scripts/futures_data.py`，依赖 requests、pandas。执行前读 [期货与大宗商品详细说明](references/futures-and-commodities.md)，其中包含七类数据的交易所覆盖、历史起点、字段单位及完整示例。成功后读完整DataFrame JSON，按columns解释data并保留attrs；终端仅前三行，已有文件不覆盖，异常非零退出且不保存。CLI不自动降级、补交易日或增加重试。

### 13.1 官方期货日行情

CLI：`scripts/futures_data.py daily <日期> <交易所> --output <新文件.json>`。覆盖SHFE/INE/CZCE/CFFEX/GFEX，不含DCE；成交额turnover_10k单位万元，早期可能缺失。各所历史起点不同，非交易日/未发布等会报错。SHFE按同日INE文件剔除能源品种；CFFEX另对照index.xml核验日期与合约数据，不能跳过失败文件拼成完整结果。

### 13.2 官方期货期权日行情

CLI：`scripts/futures_data.py options <日期> <交易所> --output <新文件.json>`。覆盖同上五所，ETF期权走§9。Delta/IV以源实际字段为准，可能按系列提供，中金所不公布这两项；缺失不补0，也不当作本地计算结果。

### 13.3 会员持仓排名

CLI：`scripts/futures_data.py rank <日期> <交易所> --symbol <品种或合约> --output <新文件.json>`。仅SHFE/INE/CZCE/CFFEX，成交/持买/持卖前20名会员，不是全市场持仓或投资者账户分布。先验证完整源再筛symbol，筛选无匹配可成功保存空表；CFFEX已上市品种缺文件会报错。

### 13.4 新浪实时行情

CLI：`scripts/futures_data.py realtime RB0 IF0 M0 --output <新文件.json>`。可取大商所品种；RB0为主力连续，CU2610为具体合约。使用返回datetime核对时间，不因名为实时就认定正在交易；商品与中金所字段布局不同，缺字段保留缺失，不把日线当实时盘口替代。

### 13.5 A50 连续报价

CLI：`scripts/futures_data.py a50 --output <新文件.json>`。新浪hf_CHA50CFD连续报价，包含datetime及报价字段；不是外资净流入或持仓数据，不能从价格直接证明资金流向。

### 13.6 上金所现货日线

CLI：`scripts/futures_data.py spot --instrument 'Au(T+D)' --output <新文件.json>`。返回日线，不是即时现货报价；支持品种与历史范围见reference。黄金价格元/克，白银元/千克；无成交0值日剔除，少量原始OHLC异常日期在attrs.ohlc_anomaly_dates保留，不因保存JSON丢弃诊断。

### 13.7 新浪期货日 K

CLI：`scripts/futures_data.py kline M0 --start <开始日期> --end <结束日期> --output <新文件.json>`。具体合约或主力连续日线，可补DCE量价数据；主力连续换月可能跳空，未复权。结算价可能缺失（源0转None），精确成交量/持仓及结算优先官方日行情；DCE本技能没有对应官方回退。旧到期合约及日期区间覆盖有限，无数据报错，不承诺全历史。

---

## Layer 14: 事件驱动（V3.9.0 新增）

统一入口 `scripts/events_data.py`，依赖 requests、pandas。执行前读 [事件驱动详细说明：业绩预告、机构调研、增减持、回购、质押与新股申购](references/corporate-events.md)，其中包含六类事件的函数参数、单位、CLI/Python 示例、分页与空结果例外。共享东财同进程限流，串行调用；默认limit：前四类500、质押5000、IPO100，上限5000，不代表完整历史。个股代码归一化但拒绝显式指数写法；事件日期按各字段解释，不统一当公告日。

### 14.1 业绩预告

CLI：`scripts/events_data.py forecast --report-date <报告期日期> --limit 500 --output <新文件.json>`，可加--code。一次预告按指标拆多行，不能把行数当预告次数；金额元，同比为%。区分报告期与公告日，预告区间不是已实现业绩。

### 14.2 机构调研

CLI：`scripts/events_data.py survey --code <个股代码> --start <日期> --end <日期> --detail --output <新文件.json>`。日期按公告日筛选，不是接待日；默认一次调研一行，加--detail为一家机构一行，不把明细行数当独立调研次数。

### 14.3 股东增减持

CLI：`scripts/events_data.py holder-trades --direction 减持 --start <日期> --output <新文件.json>`，可加--code/--end。股数万股、减持为负，占比为%；仅direction不算可返回空表的收窄条件，全市场空结果仍报错。

### 14.4 股票回购

CLI：`scripts/events_data.py buyback --progress 实施中 --output <新文件.json>`，可加--code。按更新字段排序，区分方案上下限与已实施部分，单位股/元/%；不能把方案金额当已回购金额。progress也算收窄条件，可返回空表。

### 14.5 股权质押

CLI：`scripts/events_data.py pledge --output <新文件.json>` 默认最近统计日全市场。--code取该股历次统计，--date取指定统计日，两者不能同时给。仅沪深，北交所报错；股数万股、市值万元，占比%。指定统计日无记录抛ValueError，不按交易日自行补齐周度统计。

### 14.6 新股申购日历

CLI：`scripts/events_data.py ipo --limit 100 --output <新文件.json>`。按申购日倒序，含尚未申购排期；区分申购/中签/缴款/上市日期。发行量万股，网上发行量及申购上限为股，顶格配市值万元，中签率/首日涨幅为%；未定价或未上市字段可缺失，不补零。

六类均保存完整DataFrame及来源，按columns解释data，终端仅前三行；已有文件不覆盖，异常非零退出且不保存。逐页核对重复及返回筛选条件，允许的空表仅表示本次无匹配，不等于事件不存在；不要将limit内结果称为全部历史。

---

## Layer 15: 可转债（V3.9.0 新增）

### 15.1 可转债条款与最新源报价

CLI：`scripts/events_data.py bonds --output <新文件.json>`；需要已摘牌记录加 --include-delisted。执行前读 [可转债详细说明](references/convertible-bonds.md)，其中包含上市状态、日期边界、报价字段、分页上限及筛选示例。依赖 requests、pandas，共享东财请求。

- 每页500条、最多20000条，按申购日/代码排序；取源数据后再过滤已摘牌，unknown保留。源空报错，过滤后空表允许；默认结果不能作为完整历史样本。
- 状态按北京时间与市场字段判断：上市前upcoming，摘牌日及以后delisted，STAS00直接按delisted；listed不保证未停牌或正在交易。未来摘牌日不提前当已摘牌。
- 发行规模issue_size_100m为亿元，premium_pct为百分数（10表示10%）；报价、转股价值、溢价率直接采用源值，不重新计算或核验时效。缺失/非有限值不补0，低溢价不等于低估或可成交。
- 成功后读完整DataFrame JSON，按columns解释data并保留attrs；终端仅前三行，已有输出不覆盖，异常非零退出且不保存。筛选前核验报价有效性，研究转股还需核对转股起始日等条款。

---

## 估值计算公式

统一入口 `scripts/valuation.py`，依赖 requests、pandas；full的HTML解析另需lxml。执行前读 [估值公式详细说明](references/valuation-formulas.md)，其中包含精确公式、边界值、CLI/Python入口及原框架假设。

以下CLI均可加 `--output <新文件.json>`：

- 前向PE：`scripts/valuation.py forward-pe <价格> <预测EPS>`。价格/EPS；EPS≤0返回Infinity。
- PE消化时间：`scripts/valuation.py digestion <当前PE> <CAGR> --target-pe 30`。当前PE≤目标先返回0；否则CAGR≤0返回Infinity，其余用对数公式。30为可调整的默认目标。
- PEG：`scripts/valuation.py peg <PE> <CAGR>`。PE/(CAGR×100)；CAGR≤0返回Infinity。
- 单票组合估值：`scripts/valuation.py full <六位代码>`。先读下方完整调研流程，组合计算的缺失值/负EPS规则与独立公式不同。

CAGR输入小数，0.5表示50%；保证价格与EPS口径一致，先核验预测期、币种和数据有效性。消化时间是增长假设下的数学结果，不是价格预测；不能把返回0年或低PEG当作估值有效的证明。

CLI完整保存计算结果，非有限值用$float标记；已有文件不覆盖，未捕获异常非零退出且不保存。full可能警告后返回部分结果，检查stderr及终端JSON的warnings，不把成功退出等同于数据完整。原框架阈值在reference保留为自定义假设，不作为所有行业通用结论。

---

## 完整调研流程

执行组合任务前读 [完整调研流程详细说明](references/research-workflows.md)：文档包含单票估值、批量比较、主题研报检索和新标的调研四套Python示例，以及输入、警告和数据口径限制。按任务读取相应流程，无需顺序执行全部示例。

- **A 单票组合估值**：CLI为 `scripts/valuation.py full <六位代码> --output <新文件.json>`；[流程A](references/research-workflows.md#single)说明腾讯报价与同花顺预测的组合。预测首两行未经年份排序，代码沿用旧路由且不检查僵尸报价；先核验日期、预测期和来源。负EPS/缺失值规则与独立公式不同，警告后可能返回部分结果，0年消化不能证明数据有效。
- **B 批量比较**：[流程B](references/research-workflows.md#batch)串行调用full，每票异常分别记录。比较前统一预测期与口径，排除无法核验的值；不要只挑成功样本就称覆盖全体标的。
- **C 主题研报检索**：[流程C](references/research-workflows.md#reports)先用iwencai（需Key）多查询，再用东财补充相关标的列表。仅按非空UID去重，缺UID保留并注明可能重复；示例仅处理前10条的关联标的，不保证全覆盖，也不自动下载PDF。
- **D 新标的快速调研**：[流程D](references/research-workflows.md#research)组合预测、报价、板块、分钟/日资金流、龙虎榜、解禁、两融和股东户数。示例展示返回记录，遇WARN停止；实时数据与固定示例日期不可混成同日快照。分钟累计快照不求和，日资金流统计先按§4.5校验，空返回不直接解释为事件不存在。

Python调用先初始化脚本路径。完整返回文件/字段用于分析，终端预览不替代完整数据；单接口字段及降级限制仍按主文档各节读取对应reference。调研输出区分源事实、计算假设和推断，不把接口成功等同结论成立。

---

## 官方两融与北交所行情备胎（V3.8.0）

主源失败且需要沪深两融或北交所五档快照时，先读 [官方两融与北交所备用源详细说明](references/official-market-backups.md)，其中包含两个CLI、字段单位、与主源的差异、日期核验及Python示例。入口均为 `scripts/official_data.py`；不会自动切源。

- **沪深两融**：`margin <交易日> <SH或SZ> --code <代码> --output <新文件.json>`；省略--code取该所完整数据（包含源侧ETF）。完整源校验后筛代码，无匹配可返回空表；未发布则报错。两所进度可能不同，单所结果不能称沪深全市场。沪市核对源日期/总数，深市按请求日期下载但不另从文件提取日期交叉核验。
- **两融单位与损失**：余额/买入额为元，融券余量/卖出量为股或份；沪市缺失融券余额保留缺失，不能用量×价冒充官方金额。备用输出不覆盖东财全部字段，深市不含两种偿还字段，按所需字段判断能否替代。
- **北交所当前快照**：`bse-quote <期望交易日> --code <北交所六位代码> --output <新文件.json>`；省略--code取全板。逐行核对源日期，不能历史回填，盘中更新延迟未验证；五档为价格元/数量股，成交额元，零值保留，pe_source不称PE-TTM。不是逐笔Level-2。

完整DataFrame JSON保留来源及全部行，按columns解释data；终端仅前三行，已有输出不覆盖，失败非零退出且不保存部分页。北交所保留匿名会话、每页重定向后最多重试一次、最多100页及完整性检查，不以部分结果冒充全板。

## 数据源优先级

按前面的端点路由和任务章节选择默认CLI，不把数据源清单序号当作所有任务的统一优先级。需要核对来源覆盖与历史验证记录时，读 [数据源与降级策略详细说明](references/sources-and-fallbacks.md)：包含34项来源记录、备用源对照、未封装候选地址及3个备用CLI。

行情以腾讯和盘后包为主，mootdx仅用于财务/F10；研报按东财、iwencai及新浪能力选择；资金面与事件多走东财；期货和利率优先对应交易所/官方机构。具体市场、日期、复权与字段限制以各章节为准。历史“稳定”、低风控和请求耗时记录不保证今天可用。

## 备用源速查 & 降级策略（东财/主源被封时用）

主源报错、疑似缺失或需交叉核验时，先读 [备用入口、覆盖损失及完整示例](references/sources-and-fallbacks.md)。先核对参数和日期，再尝试满足任务的备用入口；来源不同不保证独立可用，返回空也不证明没有数据。仅列URL的历史候选不是已封装CLI，使用前另行核验。

- **沪深两融 / 北交所当前五档**：用上一节的 `official_data.py margin / bse-quote`。单所不等于沪深全市场，北交所不能历史回填，两融字段有缺失。
- **研报列表**：东财失败可用§2.4新浪，但缺评级与目标价。**快讯**可按§5切换来源，不能保证补齐同一新闻集合或个股完整检索。
- **龙虎榜**：`scripts/market_backups.py dragon-tiger <日期> --output <新文件.json>`。深市仅当前响应首块结构化数据，沪市为sse_raw全文；不自动分页或校验返回日期。
- **个股日资金流**：`scripts/market_backups.py fund-flow <六位代码> --days 60 --output <新文件.json>`。仅date/close/net_amount/turnover，无四档明细，不替代分钟资金流；沿用旧代码路由，不能假定全局ticker规则适用。
- **公告**：`scripts/market_backups.py announcements <六位代码> --page-size 20 --output <新文件.json>`。深市走深交所，沪市仍走东财，不是完全独立于东财故障的备用源。
- **盘后包缺日期**：腾讯只能逐只补沪深，需核对清单/日期，北交所缺口明确报告。逐笔、分钟资金流及其他无等价入口的能力，不用大单、量价、日度统计冒充补齐。

三个market_backups命令依赖requests及随附模块，沿用urllib请求，不自动接入em_get；深交所两处请求已恢复默认证书校验，证书错误会直接失败。成功后读完整输出，沪市龙虎榜全文在文件中，终端仅预览；已有文件不覆盖，异常非零退出且不保存。切源后说明来源、日期/时效、市场覆盖及缺失字段；无合适来源就报告缺口。

---

## 调用失败时

先核对所选接口的参数、市场和日期覆盖，再按「备用源速查 & 降级策略」选择替代入口，并说明缺失字段。空结果不能直接解释为没有数据。

遇到东财连接异常、iwencai 鉴权失败、mootdx 无法取数、EPS/问答为空、PDF 下载失败或北向历史不足时，按症状读取 [故障排查](references/troubleshooting.md) 对应条目，无需通读。

### 回测数据边界

本 skill 提供数据和估值计算，不带回测引擎。聚宽代码转换见「Ticker 格式归一化」；北交所代码不做聚宽转换。跨源比较须核对双方复权设置，需要前复权时用 §1.2 的 `adjust='qfq'` 或 §1.6 复权因子。历史估值用 §6.5、历史行业归属用 §6.7；§12 的当前指数成分快照不能当作历史成分。

涨停口径：首板/连板表示当前连续涨停；“9天5板”表示窗口内累计次数，两者可同时成立。题材标签是来源给出的归因线索，不能单凭标签断言上涨因果。
