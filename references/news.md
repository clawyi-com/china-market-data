<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 新闻与快讯

按任务读取：[个股新闻](#stock)、[财联社](#cls)、[东财全球资讯](#global)、[华尔街见闻](#wscn)、[新闻联播](#cctv)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

**§5.1–§5.3 共用规则：** --page-size 保留原参数含义，默认个股20、快讯50。CLI 全量保存函数返回列表，stdout 仅路径/条数/前三条预览；已有文件不覆盖、未指定输出时自动新建，完整分析读取文件。函数原生的200字符截断仍保留，不是CLI预览造成的截断。两个东财入口共用 em_get 限流，--min-interval 至少1秒、本次结束恢复；cls 不提供该参数，保持独立请求。请求/解析/保存异常非零退出、不生成结果文件。原函数未验证HTTP/业务成功状态，错误载荷仍可能返回空列表；不据空列表断言没有新闻。

<a id="stock"></a>

### 5.1 东财个股新闻（直连 search-api-web）

实现位于 [scripts/market_news.py](../scripts/market_news.py)，仅需 requests：

```bash
python3 "<skill目录>/scripts/market_news.py" stock 688017 --output news.json
```

个股新闻使用原 JSONP 参数、第一页与默认相关性排序；代码直接作为 keyword，不自动规范化。取首个左括号至最后右括号之间的 JSON；文章列表来自 result.cmsArticleWebOld。title 去标签，content 去标签后截前 200 字符；不解码 HTML 实体、不将摘要冒充全文。time/source/url 原样保留。

输出和限流规则见本层 §5.1–§5.3 共用规则。Python 组合调用先初始化脚本路径：

```python
from market_news import eastmoney_stock_news

# 用法
news = eastmoney_stock_news("688017")
for n in news[:5]:
    print(f"  {n['time']} | {n['source']} | {n['title']}")
```

> **⚠️ 间歇性返回空（#18）：** 部分大陆住宅 IP 调本接口会只拿到 `passportWeb`（股民资料）而无 `cmsArticleWebOld`（文章列表）——这是东财对该 IP 的间歇风控，非代码问题。代码已对空结果安全返回 `[]`；遇到时隔几分钟或换网络重试即可。

<a id="cls"></a>

### 5.2 财联社快讯（直连 cls.cn，v1 API + 本地签名）✅ 已复活（2026-07）

> **✅ 2026-07 复活：** 旧接口 `cls.cn/nodeapi/telegraphList` 2026-05 下线（站点改
> Next.js，旧址返回 HTML 而非 JSON，#14）。现走新版 `cls.cn/v1/roll/get_roll_list`——它
> 强制校验 `sign`，但签名**纯本地计算、无需任何 key**：`sign = md5(sha1(按 key 字典序
> 拼接的 query 串))`。财联社快讯偏 A 股财经、时效强，与 §5.3 东财 7×24 **互为独立备份**
> （两条不同源、不同风控面，一条被封另一条仍在）。2026-07-11 实测 errno=0 正常返回。

实现位于 [scripts/market_news.py](../scripts/market_news.py)，仅需 requests：

```bash
python3 "<skill目录>/scripts/market_news.py" cls --output news.json
```

财联社保持按参数 key 排序构造查询串，再 md5(sha1(query).hexdigest()) 本地签名，不需要 Key。使用独立 requests.get（不是东财 em_get）；ctime 按本机时区 datetime.fromtimestamp 转字符串，0/None 为时间空串，不自动切换北京时间。title/content 假值时回退 brief，正文不截断。

输出和限流规则见本层 §5.1–§5.3 共用规则。Python 组合调用先初始化脚本路径：

```python
from market_news import cls_telegraph

# 用法
news = cls_telegraph()
for n in news[:10]:
    print(f"  {n['time']} | {n['title'][:60]}")
```

<a id="global"></a>

### 5.3 东财全球资讯（7x24）

实现位于 [scripts/market_news.py](../scripts/market_news.py)，仅需 requests：

```bash
python3 "<skill目录>/scripts/market_news.py" global --output news.json
```

全球资讯每次生成新的 req_trace UUID，请求 pageSize 字符串、fastColumn=102；保留标题、showTime 原值，summary 截前 200 字符。不自动翻页、去重或合并财联社内容。

输出和限流规则见本层 §5.1–§5.3 共用规则。Python 组合调用先初始化脚本路径：

```python
from market_news import eastmoney_global_news

# 用法
news = eastmoney_global_news()
for n in news[:10]:
    print(f"  {n['time']} | {n['title']}")
```

<a id="wscn"></a>

### 5.4 华尔街见闻 7×24 快讯（V3.9.0 新增）

新闻层第三个来源，与 §5.2 财联社、§5.3 东财互为备份。`channel` 常用 `global-channel`（要闻）/ `a-stock-channel`（A 股）。
`importance` 取见闻的 score 字段，实测只有 1 / 2，100 条里约 6 条为 2（头条级快讯）。时间为北京时间。
翻页：把返回表的 `attrs['next_cursor']` 传给下一次的 `cursor`。

实现位于 [scripts/news_sources.py](../scripts/news_sources.py)，依赖 requests、pandas；与仅 requests 的前三节入口分开，避免增加其运行依赖。

```bash
python3 "<skill目录>/scripts/news_sources.py" wscn --channel a-stock-channel --limit 50 --output flash.json
```

原频道校验、limit 1–100、code=20000 检查保留。display_time 必须为数值且不是 bool，按 UTC+8 转时间；content_text 去首尾空白，channels 必须字符串数组并用逗号连接。空条目报错，不返回成功空表。翻页显式使用 --cursor，完整 JSON 的 attrs.next_cursor 保留；不新增自动翻页、合并或去重。

两命令完整保存 DataFrame 的 columns/columns_index/dtypes/index/attrs/data，保留 source/source_url/fetched_at；stdout 仅路径/总行数/前三行，分析正文须读文件。未指定输出则当前目录新建 JSON，已有文件不覆盖；优先硬链接、兼容时独占复制，等待成功退出再读取。异常非零退出，不保存部分类结果。

<!-- v39-wscn-lives:start -->
```python
from news_sources import wallstreetcn_lives
```
<!-- v39-wscn-lives:end -->

<a id="cctv"></a>

### 5.5 央视《新闻联播》文字稿（V3.9.0 新增）

央视网官方页面：当日条目标题 + 逐条正文（`with_content=True` 约 15 次请求）。页面结构 2016 / 2019 / 2021 年改过三次，
三种写法都能解析。个别老视频已被下架，其 `content` 为 None（标题仍在）。当晚约 20:00 后更新，未发布抛 `ValueError`。
**内容以时政为主：可用于政策信号研究，做短视频文案时不要引用。**

实现同样位于 [scripts/news_sources.py](../scripts/news_sources.py)：

```bash
python3 "<skill目录>/scripts/news_sources.py" cctv 2026-09-18 --titles-only --output xwlb.json
```

默认抓正文，--titles-only 等价 with_content=False（不生成 content 列）。保留三代标题解析优先级，跳过整期节目，协议相对链接加 https:；正文支持 content_area/cnt_bd，保留换行、解码实体并去开头央视署名。短错误跳转页返回 None，其他正文结构错误抛 RuntimeError；每篇正文后 sleep(0.2) 保留，不因某篇失败而保存前面部分为成功。列表404为 ValueError，200但无条目为 RuntimeError。输出规则同上。

<!-- v39-cctv-news:start -->
```python
from news_sources import cctv_news, _cctv_body
```
<!-- v39-cctv-news:end -->

```python
flash = wallstreetcn_lives("a-stock-channel", limit=50)
more = wallstreetcn_lives("a-stock-channel", limit=50, cursor=flash.attrs["next_cursor"])
xwlb = cctv_news("2026-09-18", with_content=False)
```

---
