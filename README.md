<!-- Modified by china-market-data contributors: rewritten for this derivative distribution. See UPSTREAM.md. -->
# china-market-data · 中国市场数据

[English](README_en.md) · [技能入口](SKILL.md) · [来源与修改说明](UPSTREAM.md) · [Apache-2.0](LICENSE)

面向 AI 助手和 Python 用户的中国证券市场取数工具。将用户的数据需求映射到可执行 CLI，并说明数据时间、覆盖范围、字段含义和失败后的降级方式。

本项目基于 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 开发，沿用 Apache-2.0 许可证，由本项目贡献者独立维护。上游作者不为本衍生版本提供背书或维护承诺。来源基准、保留声明和主要改动见 [UPSTREAM.md](UPSTREAM.md) 与 [NOTICE](NOTICE)。

## 能做什么

| 需求 | 数据范围 |
| --- | --- |
| 行情与历史价格 | 个股、指数、ETF 报价，K 线、逐笔、盘后日线与复权因子 |
| 题材与市场信号 | 强势股及来源题材标签、板块归属、涨幅排名、资金流、龙虎榜、涨停与异动 |
| 公司研究 | 研报、公告、财务、估值、股东户数、分红、限售解禁及公司事件 |
| 其他市场数据 | 宏观利率、指数成分与交易日历、期货、商品、ETF 期权与可转债 |

具体市场、历史区间、参数与缺失字段，以 [SKILL.md 的路由表](SKILL.md#端点路由速查) 和对应 `references/` 文档为准。不同接口能力不同；能够取到某类数据不代表覆盖所有市场或所有日期。

## 本版本的改进

- 将取数代码从长文档拆为可运行脚本，详细说明按需阅读。
- 增加 CLI 参数、结果文件保护、环境检查与技能目录内虚拟环境支持。
- 行业涨幅排名检查分页完整性；板块涨幅与资金流排名分别提供入口。
- 保留报价来源、行情时间与抓取时间，区分缺失值和真实的 0。
- 使用冻结上游样本和回归测试核对迁移与有意修复的行为。

这些改进不保证第三方接口永久可用，也不构成对所有 AI 产品的兼容性认证。

## 安装

需要 Python 3.9+；建议使用已验证的 Python 3.12。安装 Python 包时需要访问包源，实际取数时需要访问相应数据源。

将技能发布包解压为 `china-market-data/`，或使用保留历史的仓库检出。必须保留 `SKILL.md`、`scripts/`、`references/`、`requirements.txt`、`LICENSE`、`NOTICE` 和 `UPSTREAM.md`，不能只复制一个 Markdown 文件。

使用 `git clone` 时，目标目录须命名为 `china-market-data`，与 `SKILL.md` 中的 `name` 一致。Agent Skills 约定技能名与所在目录名相同，直接克隆得到的默认目录名 `a-stock-data` 可能导致宿主无法加载或以错误名称注册：

```bash
git clone <本项目仓库地址> ~/.claude/skills/china-market-data
```

macOS / Linux，在技能根目录执行：

```bash
python3 -m venv .venv
PIP_USER=0 .venv/bin/python -m pip install -r requirements.txt
python3 scripts/run.py --check
```

Windows PowerShell，在技能根目录执行：

```powershell
py -3 -m venv .venv
$env:PIP_USER = "0"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
py -3 scripts/run.py --check
```

`--check` 检查全部列出的依赖，不请求行情。部分功能只需少量依赖；例如腾讯报价仅用标准库，可以直接运行而不安装全部包。依赖使用版本范围，尚未为所有系统锁定完整依赖组合；Windows 命令未经过完整平台实测。

多数业务 CLI 会使用技能目录内的 `.venv`；`run.py` 也可统一启动脚本。不会自动安装依赖或修改全局 Python。作为 Python 库导入时，调用方负责选择正确解释器。移动目录或换机器后应重新创建 `.venv`，不要复制已有虚拟环境。

Windows 通常没有 `python3` 命令，下文示例中的 `python3` 请换成 `py -3`；未安装 py 启动器时用 `python`。输出流编码无法表示中文时（如英文 Windows 管道默认的 cp1252），脚本自动改用 UTF-8 输出，读取方应按 UTF-8 解码。

### 技能目录只读时

宿主把技能装在只读位置时无法创建 `.venv`。可把虚拟环境建在可写位置，之后一律用该解释器运行脚本；技能目录内没有 `.venv` 时，脚本直接使用调用它的 Python，不会切换：

```bash
python3 -m venv ~/.venvs/china-market-data
PIP_USER=0 ~/.venvs/china-market-data/bin/python -m pip install -r <技能目录>/requirements.txt
~/.venvs/china-market-data/bin/python <技能目录>/scripts/run.py --check
```

Windows 对应为 `py -3 -m venv $env:USERPROFILE\.venvs\china-market-data`，解释器位于其中的 `Scripts\python.exe`。结果文件写到当前目录，请在可写目录下运行，或用 `--output` 指定可写路径。

### 在 AI 助手中使用

把整个目录放到宿主支持的技能目录，例如 Claude Code 的 `~/.claude/skills/china-market-data/`，或 Codex 默认的 `~/.codex/skills/china-market-data/`；自定义配置以宿主设置为准。其他助手需要能读取技能文件并执行本地 Python。仅支持聊天、不能执行脚本的环境不能直接取数。

技能本身不依赖可易、某个 agent ID 或 `CLAUDE.md`。仓库中的 `CLAUDE.md` 是可选研究助手指引，不是执行 CLI 的必要条件。更新时同时更新脚本与文档；各 agent 的独立安装副本不会自动同步。

## 快速使用

以下命令在技能根目录运行；输出文件需使用新文件名。

```bash
# 实时行情：裸 000001 是平安银行；上证指数用 sh000001
python3 scripts/tencent_quote.py sh000001 sz000001 510300 --output quotes.json

# 当日强势股与来源给出的题材标签
python3 scripts/run.py ths_hot_reason.py --output hot.json

# 概念板块最近 5 日涨幅；与主力资金流排名不同
python3 scripts/run.py eastmoney_signals.py board-quotes --board-type concept --period 5d --top-n 20 --output boards.json

# 查看某个命令的参数
python3 scripts/run.py eastmoney_signals.py board-quotes --help
```

默认板块接口失败后，可显式尝试 `--source dataapi`。它仍属于东财，不是独立供应商，也不保证能绕开同源故障；字段减少和单位转换见 [板块排名说明](references/signals-ranking.md#industry)。

大部分 CLI 将完整返回结构写入 JSON，终端只给预览。需要读取实际文件，不能把预览条数当成全部数据。`top` / `bottom` 本身仍受 `--top-n` 限制，并不保存所有中间排名。

iwencai 入口需要用户自己的 `IWENCAI_API_KEY`；配置方法见 [技能前置说明](SKILL.md#prerequisites)。不要把 Key、Cookie 或会话文件提交到仓库。

## 数据边界

- 抓取时间不是行情时间；未知时间不能推断为“实时”。题材标签也不是已证实的上涨原因。
- 部分历史数据只有本地已保存记录，不能承诺补齐；复权、市场范围与日期语义按接口说明处理。
- 板块分页取齐不等于同一时刻的原子快照。`complete` 表示记录覆盖，`ranking_complete` 表示涨幅是否全部有效；缺失记录保留在 `missing`。
- 东财节流主要在单个进程内生效，多 agent 并发不会自动获得跨进程全局限流。
- 接口可能出现限流、认证变化、缺失、延迟或下线。失败应明确报告，不用空数据伪装成功。
- 少数继承接口仍使用明文 HTTP（如强势股、部分期货接口），传输内容存在被观察或篡改的风险，不应据此宣称端到端安全或直接驱动交易。
- 本工具提供数据获取与研究辅助，不提供交易执行或收益保证；也不是回测引擎。

**代码开源不代表数据开放授权。** 行情、新闻、研报、公告及其他返回内容的使用、存储、展示和再分发需遵守对应供应商条款。免费或免 Key 不等于可以自由商用；本项目没有逐项取得这些数据的再分发授权。

## 开发与验证

开发使用保留上游基准提交的 Git 检出；技能 ZIP 不含测试套件。

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tests/audit_installed_bundle.py
python3 tools/build_release.py
```

部分测试依赖完整 Git 历史，浅克隆或 GitHub 自动生成的源码压缩包可能无法运行这些检查。可选实时测试默认跳过；离线测试通过不证明上游此刻可用。贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)，发布检查见 [docs/PUBLISHING.md](docs/PUBLISHING.md)。

## 许可证与致谢

代码按 [Apache License 2.0](LICENSE) 分发，保留上游 `Copyright 2026 Simon Lin`。再分发时应保留许可证及相关声明，并为修改文件注明改动；详情见 [NOTICE](NOTICE)。第三方依赖按各自许可证提供。

感谢 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 的原始工作。[上游更新历史](CHANGELOG.md) 保留用于追溯；上游版本号不代表本衍生版本已经发布了同名版本。
