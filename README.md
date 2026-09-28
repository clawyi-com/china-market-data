<!-- Modified by china-market-data contributors: rewritten for this derivative distribution. See UPSTREAM.md. -->
# china-market-data · 中国市场数据

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-green.svg)](requirements.txt)
[![Release](https://img.shields.io/github/v/release/clawyi-com/china-market-data?include_prereleases&label=release)](https://github.com/clawyi-com/china-market-data/releases)
[![skills.sh](https://img.shields.io/badge/skills.sh-china--market--data-111111.svg)](https://skills.sh/clawyi-com/china-market-data/china-market-data)
[![Repo](https://img.shields.io/badge/github-clawyi--com%2Fchina--market--data-111111.svg)](https://github.com/clawyi-com/china-market-data)

[English](README_en.md) · [技能入口](SKILL.md) · [来源与修改说明](UPSTREAM.md) · [Apache-2.0](LICENSE)

**`clawyi-com/china-market-data`** 是面向中国用户的 **中国市场数据 / 中国股票市场数据 Skill**：覆盖 A 股行情、K 线、逐笔、研报、资金流、公告、ETF、期货与宏观数据，给 Claude Code / AI Agent / Python CLI 直接调用，并标明时间戳、覆盖范围、字段含义和失败降级方式。

> 这不是投顾建议，也不是付费数据商 SDK。

## 目录

- [30 秒开始](#30-秒开始)
- [能做什么](#能做什么)
- [本版本的改进](#本版本的改进)
- [安装](#安装)
- [快速使用](#快速使用)
- [数据边界](#数据边界)
- [开发与验证](#开发与验证)
- [许可证与致谢](#许可证与致谢)

## 30 秒开始

```bash
# 自动识别 Cursor、Claude Code、Codex 等宿主并安装
npx --yes skills@latest add clawyi-com/china-market-data -g
```

安装后可直接向 AI 助手提问，例如“查询贵州茅台实时行情”“获取沪深 300 最近一年 K 线”。腾讯报价等标准库入口无需额外 Python 包；使用完整数据能力前，再按[安装 Python 依赖](#2-安装-python-依赖)创建虚拟环境。

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

### 1. 安装 Skill（推荐）

需要 Node.js 22.20+ / npm。Skills CLI 以 GitHub 为技能来源，不要求本仓库发布 npm 包；显式使用 `skills@latest` 可避开旧版全局目录兼容问题：

```bash
# 交互式全局安装，自动识别已安装的 Agent
npx --yes skills@latest add clawyi-com/china-market-data -g

# 指定宿主并跳过确认
npx --yes skills@latest add clawyi-com/china-market-data -g -y --agent cursor

# 只查看仓库中可安装的技能
npx --yes skills@latest add clawyi-com/china-market-data --list
```

支持的安装源可在 [skills.sh](https://skills.sh/clawyi-com/china-market-data/china-market-data) 查看。默认不加 `-g` 时安装到当前项目；加 `-g` 后全局可用。Skills CLI 只安装 `SKILL.md`、`scripts/` 和 `references/` 等技能文件，不会自动安装 Python 依赖。

### 2. 安装 Python 依赖

需要 Python 3.9+；建议使用已验证的 Python 3.12。环境初始化脚本会创建技能专用 `.venv`、安装依赖并执行离线检查。`npx skills` 全局安装的规范副本默认位于 `~/.agents/skills/china-market-data`。

macOS / Linux：

```bash
SKILL_DIR="$HOME/.agents/skills/china-market-data"
python3 "$SKILL_DIR/tools/setup_env.py"
```

Windows PowerShell：

```powershell
$SkillDir = "$env:USERPROFILE\.agents\skills\china-market-data"
py -3 "$SkillDir\tools\setup_env.py"
```

`--check` 检查全部列出的依赖，不请求行情。部分功能只需少量依赖；例如腾讯报价仅用标准库，可以直接运行而不安装全部包。依赖使用版本范围，尚未为所有系统锁定完整依赖组合；Windows 命令未经过完整平台实测。

多数业务 CLI 会使用技能目录内的 `.venv`；`run.py` 也可统一启动脚本。不会自动安装依赖或修改全局 Python。作为 Python 库导入时，调用方负责选择正确解释器。移动目录或换机器后应重新创建 `.venv`，不要复制已有虚拟环境。

Windows 通常没有 `python3` 命令，下文示例中的 `python3` 请换成 `py -3`；未安装 py 启动器时用 `python`。输出流编码无法表示中文时（如英文 Windows 管道默认的 cp1252），脚本自动改用 UTF-8 输出，读取方应按 UTF-8 解码。

### 3. 开发者安装

需要修改代码或保留完整 Git 历史时使用：

```bash
git clone https://github.com/clawyi-com/china-market-data.git
cd china-market-data
python3 tools/setup_env.py
```

手动复制或解压时，目标目录必须命名为 `china-market-data`，并保留 `SKILL.md`、`scripts/`、`references/`、`requirements.txt`、`LICENSE`、`NOTICE` 和 `UPSTREAM.md`；不能只复制一个 Markdown 文件。

### 技能目录只读时

宿主把技能装在只读位置时无法创建 `.venv`。可把虚拟环境建在可写位置，之后一律用该解释器运行脚本；技能目录内没有 `.venv` 时，脚本直接使用调用它的 Python，不会切换：

```bash
python3 <技能目录>/tools/setup_env.py --venv ~/.venvs/china-market-data
~/.venvs/china-market-data/bin/python <技能目录>/scripts/run.py --check
```

Windows 对应为 `py -3 <技能目录>\tools\setup_env.py --venv $env:USERPROFILE\.venvs\china-market-data`，解释器位于其中的 `Scripts\python.exe`。结果文件写到当前目录，请在可写目录下运行，或用 `--output` 指定可写路径。

### 在 AI 助手中使用

优先用 `npx --yes skills@latest add` 自动识别 Cursor、Claude Code、Codex 等宿主并安装到正确位置。需要手动安装时，再把整个目录复制到宿主支持的技能目录；其他助手需要能读取技能文件并执行本地 Python。仅支持聊天、不能执行脚本的环境不能直接取数。

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

开发验证使用当前仓库的 Git 检出；正式技能 ZIP 不含测试套件。

```bash
python3 -m compileall -q scripts tools tests
python3 -m unittest discover -s tests -v
python3 tools/build_release.py
npx --yes skills@latest add . --list
```

这些检查不请求实时行情；离线测试通过不证明上游数据源此刻可用。GitHub Actions 会在 push 和 pull request 上重复执行编译、smoke tests、Skills CLI 发现与发布包校验。贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)，发布检查见 [docs/PUBLISHING.md](docs/PUBLISHING.md)。

## 许可证与致谢

代码按 [Apache License 2.0](LICENSE) 分发，保留上游 `Copyright 2026 Simon Lin`。再分发时应保留许可证及相关声明，并为修改文件注明改动；详情见 [NOTICE](NOTICE)。第三方依赖按各自许可证提供。

感谢 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 的原始工作。[上游更新历史](CHANGELOG.md) 保留用于追溯；上游版本号不代表本衍生版本已经发布了同名版本。
