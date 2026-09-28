<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 投资者问答与平台热度

按任务读取：[深市互动易](#irm)、[热榜与人气榜](#ranking)、[沪市上证e互动](#sse)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

> 投资者互动问答用于查阅提问与公司回复；同花顺热榜、东财人气榜及概念命中反映各平台的热度记录。不要把提问当公司已确认的事实，也不要把热度或概念标签直接当作涨跌原因。以下入口免登录、无需 Key。

<a id="irm"></a>

### 10.1 互动易问答（巨潮 — 投资者提问 + 公司回复）

实现位于 [scripts/investor_sentiment.py](../scripts/investor_sentiment.py)，依赖 requests：

```bash
python3 "<skill目录>/scripts/investor_sentiment.py" irm 002594 --page-size 30 --page-num 1 --output irm.json
```

先以POST表单keyWord查询，取第一条secid；没有匹配即返回[]，不缓存orgId。第二步仍为POST但参数放query string，body为空；页码/页大小原样传入，不自动翻页。保留未回复answer=None及原文本，pubDate毫秒按运行机器本地时区转分钟，假值时间为空串。沪市请走§10.3，北交所两个平台均无覆盖。

CLI完整列表写文件，终端前三条预览；请求异常原函数WARN+[]，CLI捕获WARN非零退出、不保存。无WARN的空结果仍按原生行为成功保存，不代表完整性已确认。已有输出含符号链接不覆盖。Python组合调用先初始化脚本路径：

```python
import io
from contextlib import redirect_stdout
from investor_sentiment import cninfo_irm

# 显示本页原文，保留未回复记录；提问不等于公司确认。
diagnostics = io.StringIO()
with redirect_stdout(diagnostics):
    rows = cninfo_irm("002594", page_size=30)
if "[WARN]" in diagnostics.getvalue():
    raise RuntimeError("问答请求失败：" + diagnostics.getvalue())
if not rows:
    print("本次未取得问答，不能据此认定公司没有回复。")
for q in rows:
    print(f"公司 {q.get('company')} 代码 {q.get('code')} 提问时间 {q.get('ask_time')}")
    print("Q:", q.get("question") or "（提问内容缺失）")
    print("A:", q.get("answer") or "（本条未取得回复内容）", "回答方:", q.get("answerer"))
```

> **坑：** ① 第二步参数放 **query string**（不是 body），否则 400。② `orgId` 取自第一步的 `secid`（即便前缀是 `gshk`，靠 `stockcode` 过滤照样拿 A 股问答）。③ 最新提问常未回复（`answer=None`），回复率因公司而异（实测立讯精密 002475 回复多、京东方 000725 几乎不回）。④ 时间是毫秒时间戳。⑤ **沪市公司查不到**（2026-09-20 实测 600519 / 600000 / 688981 均 0 条，互动易只覆盖深市），沪市问答用 §10.3 上证e互动。⑥ 请求失败时本函数打印 WARN 并返回 `[]`，与「确实没有问答」无法区分，批量使用时注意日志。

<a id="ranking"></a>

### 10.2 同花顺热榜 + 东财人气榜（市场热度 + 概念命中）

复用 [scripts/investor_sentiment.py](../scripts/investor_sentiment.py)：

```bash
python3 "<skill目录>/scripts/investor_sentiment.py" ths --period hour --output ths-hot.json
python3 "<skill目录>/scripts/investor_sentiment.py" rank --top 50 --output em-rank.json
python3 "<skill目录>/scripts/investor_sentiment.py" concepts 002594 --output concepts.json
```

ths保留源顺序与原字段类型，概念标签假值变[]，不新增排序/去重；period原样传递。rank先POST排名，再GET批量名称价格；diff为dict时取values，按裸代码合并，缺报价保持空名称及None价格/涨幅，排名列表顺序和重复项保留。top只传服务端pageSize，不本地截断。旧路由仅大写SZ→0，其余前缀→1，不额外修正未知或北交所记录。

concepts用get_prefix转大写并拼原输入，不剥SH/.SH等；保留服务端顺序与原hit值，函数没有本地按热度排序。三个原函数直接requests请求（包括东财补价），迁移未改用em_get或添加限流/重试。失败WARN时CLI拒绝保存，原生API仍WARN+[]；转换阶段异常仍抛出。完整JSON保存，终端只预览前三项。

```python
import io
from contextlib import redirect_stdout
from investor_sentiment import ths_hot_list, em_hot_rank, em_hot_concept


def checked_call(fn, *args, **kwargs):
    diagnostics = io.StringIO()
    with redirect_stdout(diagnostics):
        rows = fn(*args, **kwargs)
    if "[WARN]" in diagnostics.getvalue():
        raise RuntimeError("热度请求失败：" + diagnostics.getvalue())
    return rows


for s in checked_call(ths_hot_list)[:5]:
    print(f"  #{s['rank']} {s['name']} 热度{s['heat']} {s['concepts']} {s['tag']}")
hot = checked_call(em_hot_rank, 10)  # 请求10条，返回顺序/数量由源决定。
if not hot:
    print("未取得人气榜，不能判定排名或概念命中。")
else:
    first = hot[0]
    print("源列表首条:", first)  # 不将列表位置冒充rank=1；缺名称/价格保留原值。
    code = first.get("code")
    if isinstance(code, str) and len(code) == 6 and code.isascii() and code.isdigit():
        print("概念命中（前三条预览，不代表涨跌原因）:", checked_call(em_hot_concept, code)[:3])
    else:
        print("证券代码无效，不继续查询概念。")
```

> **坑：** ① 东财人气榜 `getAllCurrentList` 只返回带前缀代码（SZ/SH），名称要再走 `ulist.np` 补（`SZ`→`0.`、`SH`→`1.`）。② `ulist.np` 的 `diff` 偶尔是 dict（按序号为键），已做 `list(values())` 归一化。③ 同花顺热榜 `type` 可选 `hour`/`day`。

<a id="sse"></a>

### 10.3 上证e互动 — 沪市投资者问答（V3.9.0 新增）

上交所官方问答平台。§10.1 巨潮互动易**实测对沪市返回 0 条**（2026-09-20，600519 / 600000 / 688981），
沪市公司的问答只能走这里。`code=None` 看全市场；给沪市代码（60 / 68 / 900 开头）只看该公司。
`kind='answered'` 为最新已回复问答，`kind='questions'` 为最新提问（含未回复，`answer` 为 None）。
平台只开放近期问答，公司维度实测约近 1 个月。首次查某家公司要在公司列表里定位 uid（倍增 + 二分，约 10–13 次请求），之后走缓存。
北交所公司两个平台都没有。

实现位于 [scripts/sse_interaction.py](../scripts/sse_interaction.py)，依赖 requests、pandas；与§10.1深市互动易按市场分流：

```bash
python3 "<skill目录>/scripts/sse_interaction.py" --kind answered --page 1 --page-size 10 --output sse-feed.json
python3 "<skill目录>/scripts/sse_interaction.py" --code 600519 --kind questions --output sse-company.json
```

全市场GET feeds；公司先用沪市股票代码定位uid再POST userfeeds。page≥1、page_size为1–50，仍按原int转换；只取一页不自动翻页。公司页与uid均为进程内缓存，独立CLI运行不共享，批量查询可复用Python模块。倍增/二分依赖公司列表按代码升序，首空页或结构改变报错，不冒充公司不存在。

保留HTML正文去标签及实体解码、提问时间/回复时间解析；有回复块却缺内容或时间时报错，未回复answer/answer_time为None。只在明确“暂无/暂时没有”提示时允许空表，改版空页报错；公司模式发现别家公司记录也报错。返回DataFrame含source/source_url/fetched_at；CLI完整保存列/dtype/index/attrs/data，显式编码缺失值，只预览前三行，已有路径不覆盖，异常非零退出且不保存。原生接口及示例如下：

<!-- v39-sse-e:start -->
```python
from sse_interaction import sse_e_interaction
```
<!-- v39-sse-e:end -->

```python
feed = sse_e_interaction()                              # 全市场最新已回复
mine = sse_e_interaction("600519", kind="questions")    # 某公司最新提问（含未回复）
```

---
