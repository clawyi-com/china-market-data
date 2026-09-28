<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 官方两融与北交所行情备用源

主源失败且需要沪深两融或北交所五档快照时读取本文：包含两个CLI、字段单位、覆盖差异、日期核验、完整性检查及Python示例。`<skill目录>` 为技能根目录；Python调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

先完成「Python 脚本路径初始化」，再执行本节的 `official_data` 导入与调用示例；或直接运行下方 CLI。两个**能力入口**按入口计数，
不将同一函数的交易所路由重复算成端点。使用 `margin_trading_backup("2026-09-03", "SH")`
或 `"SZ"` 分别取数，`code="600519"` 可在完整快照中筛选个股；未指定代码时包含源侧融资融券标的（也含 ETF）。
两所发布进度可能不同，不能将单所结果标成沪深全市场。源未发布该日数据时抛错，完整列表中
个股未命中则返回有列定义的空表。

**单位及字段：** `margin_balance` / `margin_buy` / `short_balance` 为元；
`short_volume` / `short_sell_volume` 为股或份。上交所 `short_balance` 源值为空时保留为空，
不以余量乘价格冒充官方金额。该备胎并非东财所有字段的等价替代，深交所不含两种偿还字段。

`bse_quote_backup("2026-09-04", code="920021")` 只接受沪深北中的 **北交所纯 6 位代码**；
省略 `code` 拉全板。首参是调用方期望的交易日，必须与源侧每行日期一致，返回五档盘快照
（价格元、量股）、OHLC、成交量额、`pe_source`（官网字段口径未细分，不称 PE-TTM）。
**这是当前快照，没有历史回填，也未验证盘中更新延迟；不是逐笔 Level-2。**

实现复用 [scripts/official_data.py](../scripts/official_data.py)，Python 导入前执行「Python 脚本路径初始化」：

```bash
python3 "<skill目录>/scripts/official_data.py" margin 2026-09-24 SH --code 600519 --output margin.json
python3 "<skill目录>/scripts/official_data.py" bse-quote 2026-09-24 --code 920021 --output bse.json
```

两融完整源校验后才按代码筛选，筛选无匹配可返回空表。沪市核源日期和总条数；深市按请求日期下载文件，原解析器没有从文件另取日期交叉核验。北交所仅当前快照，必须显式给交易日并与源日期一致；不能历史回填。保留匿名 Cookie、单页重定向后只重试一次、最多100页、翻页0.2秒间隔及完整性检查。价格/五档零值保留，成交量股、成交额元，不换成手/万元。

CLI完整保存列/dtype/索引/attrs/来源与全部行，只预览三行；已有路径不覆盖，异常非零退出、不保存部分页。原Python异常类型保持，未增加自动切源或额外重试。

<!-- official-data-backups:start -->
```python
from official_data import margin_trading_backup, bse_quote_backup
```
<!-- official-data-backups:end -->

示例日期仅演示参数格式；实际调用北交所快照时须换成期望且源当前提供的交易日，不能用下方固定历史日期要求回填。两融也须选择已发布日期。

```python
sh_margin = margin_trading_backup("2026-09-03", "SH", code="600519")
sz_margin = margin_trading_backup("2026-09-03", "SZ", code="000001")
bj_quote = bse_quote_backup("2026-09-04", code="920021")
```

端点与字段交叉参考 [CNEquity 两融适配](https://github.com/rootSunc/CNEquity/blob/main/src/cnequity/adapters/exchange/margin_trading.py)
及 [北交所适配](https://github.com/rootSunc/CNEquity/blob/main/src/cnequity/adapters/bse/daily_quotes.py)。
本版只参考官方端点与字段契约，数据直接来自交易所。
