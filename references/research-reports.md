<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 研报列表、PDF、EPS 与主题搜索

按任务阅读：[§2.1 东财列表/PDF](#eastmoney)、[§2.2 一致预期 EPS](#eps)、[§2.3 主题搜索与本地去重](#iwencai)、[§2.4 新浪备用源](#sina)。`<skill目录>` 指技能根目录；组合调用前见 [Python 路径初始化](../SKILL.md#python-脚本路径初始化)。其他编号见 [SKILL.md](../SKILL.md)。

<a id="eastmoney"></a>

### 2.1 东财研报 API — 研报列表 + PDF下载（主力）

A级接口（公开JSON API），reportapi.eastmoney.com，免费无key。

实现位于 [scripts/eastmoney_reports.py](../scripts/eastmoney_reports.py)，仅需 requests；直接执行：

```bash
python3 "<skill目录>/scripts/eastmoney_reports.py" stock 688017 --max-pages 5 --output stock-reports.json
python3 "<skill目录>/scripts/eastmoney_reports.py" industry '*' --max-pages 2 --output industry-reports.json
python3 "<skill目录>/scripts/eastmoney_reports.py" industry 1238 --begin 2024-01-01 --max-pages 1 --output it-reports.json
python3 "<skill目录>/scripts/eastmoney_reports.py" pdf record.json --target-dir ./reports
```

stock/industry 始终全量保存 JSON 列表，stdout 仅给路径、行数和前三条预览；省略 `--output` 则在当前目录生成 `eastmoney-reports-*.json`，显式路径父目录须存在、不覆盖。默认 max_pages=5；页大小 100，先到空页或 TotalPage 即停；原函数对 max_pages≤0 返回空列表的行为保留。industry 默认 `'*'`、begin 默认今天减 730 天；结束时间仍为原接口的 2030-01-01。

`record.json` 必须是列表中一条完整 record 对象，不能传整个列表。PDF 命令保存原 PDF 并向 stdout 返回绝对路径；Python `download_pdf()` 仍返回路径或 None，CLI 对 None 明确退出 1。旧版按日期/机构/标题命名并复用同名文件；只检查 HTTP 200 且响应至少 1024 字节，**没有验证 PDF 文件头或已有文件内容**，不能据退出成功断言 PDF 有效。不要把任意不可信 JSON 当成下载指令；传入研报接口的原记录。`publishDate` 未做路径字符校验，异常的 `../` 值可使保存位置逸出 `target_dir`；这是旧版遗留限制，本次迁移未改变原函数。

Python 列表结构、原始字段及多层值保留；非有限数值 JSON 使用 `$float` 标记。列表文件沿用优先硬链接、否则独占创建后复制的发布方式，等待成功退出再读取；强制终止可能留下半成品。PDF 保存沿用原函数，不具备列表 JSON 的独占发布/失败清理保证。选页或下载异常写 stderr，CLI 非零退出。`--min-interval 1.5` 可调大本次调用的共享间隔，默认 1 秒；禁止小于 1 秒及非有限值，多进程之间不共享限流。

保留原接口的空结果语义：列表函数没有新增 HTTP/业务状态校验，某些错误载荷也可能返回 []。不要把零条数当作已验证的“无研报”；北交所 43/83/87 老码无结果时仍明确抛 ValueError。Python 组合使用先执行路径初始化：

```python
from eastmoney_reports import eastmoney_reports, eastmoney_industry_reports, download_pdf

# 用法
reports = eastmoney_reports("688017")
print(f"共 {len(reports)} 篇研报")
for r in reports[:5]:
    print(f"  {r.get('publishDate','')[:10]} | {r.get('orgSName')} | {r.get('title','')[:60]}")
```

#### 研报 record 关键字段

| 字段 | 含义 |
|------|------|
| title | 研报标题 |
| publishDate | 发布日期 |
| orgSName | 机构简称 |
| infoCode | 用于拼 PDF URL |
| predictThisYearEps | 今年EPS预测 |
| predictNextYearEps | 明年EPS预测 |
| predictNextTwoYearEps | 后年EPS预测 |
| emRatingName | 评级(买入/增持/...) |
| indvInduName | 行业分类 |

#### 行业研报列表（qType=1）

与个股研报**同一端点**（`reportapi.eastmoney.com/report/list`），仅 `qType` 不同：`qType=0` 个股研报，`qType=1` 行业研报。返回 record 可直接喂给上面的 `download_pdf()`（PDF 模板通用）。

直接命令见上方。Python 单独使用本块前执行路径初始化：

```python
from eastmoney_reports import eastmoney_industry_reports, download_pdf

# 用法
# 1) 全行业最新研报
reports = eastmoney_industry_reports("*", max_pages=2)
print(f"共 {len(reports)} 篇行业研报")
for r in reports[:5]:
    print(f"  {r.get('publishDate','')[:10]} | {r.get('industryName')} | {r.get('orgSName')} | {r.get('title','')[:50]}")

# 2) 单行业（IT服务Ⅱ，行业码 1238）+ 下载首篇 PDF（复用 2.1 的 download_pdf）
it = eastmoney_industry_reports("1238", max_pages=1)
if it:
    download_pdf(it[0])
```

行业研报特有/常用字段（其余字段同 2.1 个股研报）：

| 字段 | 含义 |
|------|------|
| industryName | 行业名称（如 IT服务Ⅱ、风电设备、光伏设备） |
| industryCode | 东财行业代码（用于 `industry_code` 精确过滤） |
| emRatingName | 行业评级（买入/增持/中性/...） |
| reportType | 报告类型 |
| attachPages / attachSize | PDF 页数 / 大小(KB) |
| infoCode | 喂给 `download_pdf()` 拼 PDF URL |

> **行业码怎么拿：** 东财行业码不是通用记忆码，没有公开的码表端点（`bxpa` 等已 404）。常用做法：先用 `industry_code="*"` 拉一批，从结果的 `industryName`/`industryCode` 找到目标行业的码，再用该码精确过滤。

<a id="eps"></a>

### 2.2 同花顺一致预期EPS（直连 basic.10jqka.com.cn）

实现位于 [scripts/ths_eps_forecast.py](../scripts/ths_eps_forecast.py)，需要 requests、pandas 与 HTML 解析器（推荐 lxml）。无需读取源码：

```bash
python3 "<skill目录>/scripts/ths_eps_forecast.py" 688017 --output eps.json
```

原规则保留：代码经 stock_only 归一化；页面按 GBK 解码；从 HTML 表格中取第一个列名含“每股收益”或“均值”的表，否则回退第一张表；read_html 返回空列表才返回空 DataFrame。未新增 HTTP 状态和表格真实性校验，首表回退不保证是 EPS，遇空结果/反爬页面须核查，不能直接当“没有机构预测”。原生 Python 返回完整 DataFrame。

CLI 始终全量保存，stdout 给路径、行数及前三行预览；省略 `--output` 时当前目录生成 `ths-eps-*.json`，不覆盖已有路径。文件包含 columns、columns_index、dtypes、index、attrs 和 data 行数组：每行按 columns 顺序排列，多层表头/索引另保存 levels/codes/names/sortorder，重复列不会被合并。日期索引保留 dtype/时区/频率；非有限浮点用 `$float`、缺失值用 `$missing`、日期用 `$date_type`/iso 标记。分类类型和无法明确表示的对象会报错，这类结果用 Python API。

保存优先硬链接、否则独占创建并复制；等待成功退出再读，强制终止可能留下半成品。请求、解析或保存失败写 stderr，CLI 非零退出。Python 组合使用先执行路径初始化：

```python
from ths_eps_forecast import ths_eps_forecast

# 用法
df = ths_eps_forecast("688017")
print(df)
# "预测机构数" < 3 的要谨慎
```

<a id="iwencai"></a>

### 2.3 iwencai — NL语义搜索研报（唯一能力）

需要 API Key + X-Claw Headers（SkillHub 2.0 强制要求）。

实现位于 [scripts/iwencai.py](../scripts/iwencai.py)，仅需 requests。先按 Prerequisites 设置 `IWENCAI_API_KEY`；`IWENCAI_BASE_URL` 默认 `https://openapi.iwencai.com`。这两个值在模块导入时读取，修改环境后须重新启动进程或显式修改模块配置。无需读取源码：

```bash
python3 "<skill目录>/scripts/iwencai.py" search "人形机器人 行星滚柱丝杠 2026" --channel report --size 50 --dedup --output reports.json
python3 "<skill目录>/scripts/iwencai.py" query "贵州茅台 ROE" --page 1 --limit 50 --output rows.json
python3 "<skill目录>/scripts/iwencai.py" dedup articles.json --output unique.json
```

search 的 channel 通常为 report/announcement/news，默认 report、size=50；query 默认 page=1、limit=50，请求中 page/limit 转字符串，保留 is_cache=1、expand_index=true。每次请求生成新 Trace-Id，保留全部 X-Claw 与 Bearer 鉴权头，超时 30 秒；非 HTTP 200 或非零业务 status_code 抛 RuntimeError，不新增重试。

默认搜索不去重；`--dedup` 或本地 dedup 命令才调用 `dedup_articles()`：同 uid 取最高 score，空 uid 按 title+publish_date 归组，同分保留先出现项，最后按 publish_date 倒序。原字典字段与 extra（字符串或对象）保留；调用方按下方示例处理 extra。缺失 score 默认 0，不能转换成浮点的 score 按原规则报错。

CLI 始终完整保存 JSON，stdout 仅给路径、行数、前三条预览；非列表结果也完整保存，但不伪造行数。省略 `--output` 时当前目录生成 `iwencai-*.json`，已有路径不覆盖。非有限浮点用保留 `$float` 单键标记，dedup 读取时还原。保存优先硬链接，兼容时独占创建后复制；等待成功退出再读，强制终止可能留下半成品。失败写 stderr、非零退出。

CLI 在缺 Key 时会在请求前失败，本地 dedup 不需要 Key/网络；Python 原函数仍保留原鉴权请求行为。原函数不校验返回 data/datas 一定是列表，缺失或假值仍变为 []；不要仅凭空结果判断数据覆盖。Python 用法：先执行路径初始化，再导入：

```python
import json
from iwencai import iwencai_search, iwencai_query, dedup_articles

# 用法: NL语义搜索研报
articles = iwencai_search("人形机器人 行星滚柱丝杠 2026", channel="report", size=50)
articles = dedup_articles(articles)
for a in articles[:5]:
    extra = a.get("extra") or {}
    if isinstance(extra, str):
        extra = json.loads(extra)
    print(f"{a.get('publish_date','')[:10]} | {extra.get('organization','')} | {a.get('title','')[:60]}")
```

**iwencai 的唯一价值：** NL 主题搜索。"人形机器人 行星滚柱丝杠" 这种跨主题检索只有 iwencai 能做。按标的搜研报走东财 reportapi 更稳定。

<a id="sina"></a>

### 2.4 新浪研报列表 — 研报第二来源（V3.9.0 新增 · #53）

东财研报（§2.1）之外的独立来源：标题、研报类型、日期、机构、研究员与详情页链接。**不含评级与目标价**（需要这些用 §2.1）。
新浪对连续请求会返回假的「没有找到相关内容」空页（HTTP 200，和真的没有研报一模一样），
本函数强制两次请求间隔 6 秒，遇到空页再等一次重试，批量翻页会比较慢。

实现位于 [scripts/sina_reports.py](../scripts/sina_reports.py)，需要 requests、pandas。无需读取源码：

```bash
python3 "<skill目录>/scripts/sina_reports.py" --page 1 --output latest-reports.json
python3 "<skill目录>/scripts/sina_reports.py" 600519 --page 2 --output stock-reports.json
python3 "<skill目录>/scripts/sina_reports.py" 920982 --output bse-reports.json
```

省略 code 取全市场最新，指定证券支持原前后缀/聚宽写法，北交所自动附 bj；单次只取指定页，不自动翻页。6 秒间隔与空页最多再请求一次保留，请求异常仍报错；间隔与时间戳为同进程模块状态，无跨进程或并发限流保证。批量分页应在一个进程串行调用，配置通过 `sina_reports.SINA_REPORT_MIN_INTERVAL` 修改，不要另起并发 CLI。

解析会校验研报表格标记、研究员表头和每一条带序号的行：解析数量不匹配或空白页没有明确“没有找到”提示则报错。正常字段为 date/title/type/org/author/report_id/url，附 source/source_url/fetched_at；GBK 解码、HTML 实体及组织/作者标签清理、协议相对链接补 https 均按旧规则。再次空页仍可能是源限流，不能保证等同于真实无研报。

CLI 全量保存 JSON（columns/dtypes/index/attrs/data），stdout 仅给路径、总行数与前三条预览；省略输出路径时当前目录生成 `sina-reports-*.json`，已有路径不覆盖。确实为空的结果保留完整列定义；Python 仍返回 DataFrame。保存优先原子硬链接，否则独占创建后复制，等待成功退出再读；强制终止可能留下半成品。失败写 stderr、非零退出。

Python 组合调用先执行路径初始化，再导入：

<!-- v39-sina-reports:start -->
```python
from sina_reports import sina_research_reports
```
<!-- v39-sina-reports:end -->

```python
latest = sina_research_reports()                  # 全市场最新一页（约 40 条）
moutai = sina_research_reports("600519", page=1)  # 只看某只股票
```

---
