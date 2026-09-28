<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# 公告查询与摘要

按任务读取：[巨潮公告列表](#cninfo)、[F10 公告摘要](#f10)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

<a id="cninfo"></a>

### 7.1 巨潮公告（直连 cninfo.com.cn）

实现位于 [scripts/cninfo_announcements.py](../scripts/cninfo_announcements.py)，依赖 requests：

```bash
python3 "<skill目录>/scripts/cninfo_announcements.py" 688017 --page-size 30 --output announcements.json
```

原生函数只请求第一页，page_size 默认 30，原样传给服务端，不自动翻页或本地截断。返回 title/type/date/url；url 是公告详情页，不是 PDF 下载地址，标题保留服务端原文（含可能的 HTML 高亮）。毫秒时间戳按运行机器本地时区转日期；其他真值取字符串前十位，空值为空串。

orgId 优先从官方股票映射表获取；非空映射在当前 Python 进程复用，空映射下次仍重取。映射查询异常会打印 WARN 后使用 gs+市场前缀+0+原代码的旧规则；硬编码并非所有股票都有效，空结果不证明没有公告。CLI 将该诊断转 stderr，仍按原行为继续查询。代码原样传递，不自动去除 SH/.SH。独立 CLI 进程不共享缓存，批量调用可复用 Python 模块。

CLI 全量列表保存为 JSON，只预览前三条；已有输出（含符号链接）不覆盖，请求/解析/保存异常非零退出。原接口不验证 HTTP/业务状态：announcements 缺失或 null 返回空列表，不能将其解释为完整性认证。未添加重试、缓存持久化或改变 HTTP 映射 URL。

Python 组合调用先初始化脚本路径：

```python
from cninfo_announcements import cninfo_announcements

# 用法
anns = cninfo_announcements("688017")
for a in anns[:10]:
    print(f"  {a['date']} | {a['type']} | {a['title']}")
```

<a id="f10"></a>

### 7.2 mootdx F10 公告摘要

使用 [tdx_client.py](../scripts/tdx_client.py)；先执行路径初始化后可用下方 Python 示例，或直接运行（[输出契约](market-data-details.md#mootdx)）：

```bash
python3 "<skill目录>/scripts/tdx_client.py" F10 --params '{"symbol":"688017","name":"最新提示"}' --output f10.json
```

```python
from tdx_client import tdx_client
client = tdx_client(check='finance')  # 见 Prerequisites 的 tdx_client()；财务/F10 按 finance 验活（#52：K 线命令失效不影响这里）
text = client.F10(symbol='688017', name='最新提示')
# 包含最近的公告/分红/股东大会决议等摘要
```

---
