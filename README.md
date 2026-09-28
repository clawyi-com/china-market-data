<!-- Modified by china-market-data contributors: rewritten for this derivative distribution. See UPSTREAM.md. -->
# china-market-data · 中国市场数据

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-green.svg)](requirements.txt)
[![Release](https://img.shields.io/github/v/release/clawyi-com/china-market-data?include_prereleases&label=release)](https://github.com/clawyi-com/china-market-data/releases)
[![skills.sh](https://img.shields.io/badge/skills.sh-china--market--data-111111.svg)](https://skills.sh/clawyi-com/china-market-data/china-market-data)
[![Repo](https://img.shields.io/badge/github-clawyi--com%2Fchina--market--data-111111.svg)](https://github.com/clawyi-com/china-market-data)

[English](README_en.md) · [技能入口](SKILL.md) · [来源与修改说明](UPSTREAM.md) · [Apache-2.0](LICENSE)

**`clawyi-com/china-market-data`** 是面向中国用户的 **中国市场数据 / 中国股票市场数据 Skill**：让 Cursor、Claude Code、Codex 等 AI Agent 直接调用可运行的 Python CLI，取到 A 股行情、研报、资金、公告、打板、期权、期货与宏观等真实数据，并标明时间戳、覆盖范围和失败降级方式。

**15 层能力 · 87 个端点（含 5 个备用入口）· 34 个数据来源 · 除 iwencai 外全部免 API Key**

> 这不是投顾建议，也不是付费数据商 SDK。

## 目录

- [30 秒开始](#30-秒开始)
- [直接这样问 AI](#直接这样问-ai)
- [为什么用它](#为什么用它)
- [15 层能力一览](#15-层能力一览)
- [数据来源](#数据来源)
- [安装](#安装)
- [命令行使用](#命令行使用)
- [数据边界](#数据边界)
- [开发与验证](#开发与验证)
- [许可证与致谢](#许可证与致谢)

## 30 秒开始

```bash
# 自动识别 Cursor、Claude Code、Codex 等宿主并安装
npx --yes skills@latest add clawyi-com/china-market-data -g
```

装好后直接向 AI 助手提问即可。腾讯报价等入口只用 Python 标准库；需要完整数据能力时，再按[安装 Python 依赖](#2-安装-python-依赖)执行一次初始化脚本。

## 直接这样问 AI

| 你想知道 | 可以这样问 |
| --- | --- |
| 实时行情与估值 | “贵州茅台现在的价格、PE、PB、市值和换手率” |
| 历史 K 线 | “拉宁德时代近一年前复权日 K 线” |
| 打板情绪 | “今天涨停池、连板梯队和炸板率怎么样” |
| 题材热点 | “今天有哪些强势股，分别是什么题材” |
| 资金动向 | “北向资金今天的分钟流向”“概念板块近 5 日主力资金流入排名” |
| 龙虎榜 | “今天全市场龙虎榜净买入排名，以及某只股票的买卖席位” |
| 研报与预期 | “比亚迪最近的券商研报和机构一致预期 EPS” |
| 公告与互动 | “查某公司最新公告 PDF”“公司在互动易上怎么回应这个传闻” |
| 期权 | “300ETF 期权 T 型报价、隐含波动率和希腊字母” |
| 期货与商品 | “螺纹钢主力连续日 K”“上期所持仓前 20 名” |
| 宏观利率 | “最新 LPR、FR007 和中债国债收益率曲线” |
| 事件与可转债 | “本周新股申购”“可转债转股溢价率” |
| 回测准备 | “把这些代码转成聚宽格式，并拉申万行业历史归属” |

只讨论概念或投资观点、不需要实际取数时，技能不会被加载。

## 为什么用它

- **为 Agent 设计**：数据端点都提供 CLI 和 `--help`，SKILL.md 内置端点路由表，AI 按需读取对应章节，不必把全部文档塞进上下文。
- **免 Key 开箱即用**：除 iwencai 语义搜索外，全部接口不需要注册或 API Key。
- **优先官方与稳定来源**：优先腾讯、交易所、中债、人民银行等来源；东财接口内置节流，主源不可用时按“备用源速查”降级。
- **结果可核对**：保留报价来源、行情时间和抓取时间，区分缺失值与真实的 0，失败时明确报错，不用空数据冒充成功。
- **本地运行**：数据直接从来源取回本机，写入 JSON 文件，不经过第三方中转服务。

与 akshare、tushare 等 Python 数据库相比，本项目的定位是让 AI Agent 直接调用的技能包：路由说明、参数、数据边界与降级方式都写给 Agent 读。

## 15 层能力一览

| 层 | 能力 | 主要来源 |
| --- | --- | --- |
| 1 行情 | 实时报价（PE/PB/市值/涨跌停）、日周月前后复权与 1–60 分钟 K 线、逐笔成交、全市场盘后日线、复权因子 | 腾讯、通达信官网、百度、新浪 |
| 2 研报 | 个股/行业研报与 PDF、机构评级、一致预期 EPS、自然语言搜研报 | 东财、同花顺、新浪、iwencai |
| 3 信号 | 强势股与题材、北向资金、板块归属、分钟资金流、龙虎榜席位、解禁、行业与板块排名 | 同花顺、东财 |
| 4 资金与筹码 | 融资融券、大宗交易、股东户数、分红送转、日级资金流、筹码分布、ETF 份额 | 东财、上交所、深交所、本地计算 |
| 5 新闻 | 个股新闻、财联社电报、全球 7×24 快讯、新闻联播文字稿 | 东财、财联社、华尔街见闻、央视网 |
| 6 基础数据 | 财报三表、F10、估值历史、上市退市信息、申万行业变迁、ST 名单 | 新浪、通达信、baostock、申万、东财 |
| 7 公告 | 公告检索与 PDF 下载 | 巨潮 |
| 8 打板 | 涨停/炸板/跌停池、涨停原因、连板梯队与炸板率、监控池、异动 | 东财、同花顺 |
| 9 ETF 期权 | 合约清单、T 型报价、Delta/Gamma/Theta/Vega、隐含波动率 | 新浪 |
| 10 舆情互动 | 互动易、上证 e 互动、同花顺热榜与东财人气榜 | 巨潮、上交所、同花顺、东财 |
| 11 宏观利率 | 社融、PMI、中债收益率曲线、回购定盘利率、LPR、全球宏观日历 | 人民银行、国家统计局、中债、中国货币网 |
| 12 指数与日历 | 指数成分与权重、指数 PE 与股息率、官方交易日历 | 中证、国证、深交所 |
| 13 期货商品 | 五家期货交易所日行情、商品与股指期权、持仓排名、实时期货、A50、上海金 | 各期货交易所、新浪、上金所 |
| 14 事件驱动 | 业绩预告、机构调研、增减持、回购、股权质押、新股申购 | 东财 |
| 15 可转债 | 条款、转股价值、转股溢价率 | 东财 |

另有证券代码归一化、聚宽代码转换和估值计算等本地工具。完整端点、参数和市场限制见 [SKILL.md 路由表](SKILL.md#端点路由速查按需定位不必通读全文)；能取到某类数据不代表覆盖所有市场或所有日期。

## 数据来源

腾讯财经 · 东方财富 · 同花顺 · 新浪财经 · 百度股市通 · 通达信 · 巨潮资讯 · 财联社 · 华尔街见闻 · 央视网 · baostock · 申万 · iwencai · 上交所 · 深交所 · 上期所 · 上期能源 · 郑商所 · 广期所 · 中金所 · 上海黄金交易所 · 中证指数 · 国证指数 · 中债 · 中国货币网 · 人民银行 · 国家统计局

各接口的用途、限制和备用关系见 [来源与降级说明](references/sources-and-fallbacks.md)。

## 安装

### 1. 安装 Skill（推荐）

需要 Node.js 22.20+ / npm。Skills CLI 直接以 GitHub 仓库为来源，不需要 npm 包；显式使用 `skills@latest` 可避开旧版全局目录兼容问题：

```bash
# 交互式全局安装，自动识别已安装的 Agent
npx --yes skills@latest add clawyi-com/china-market-data -g

# 指定宿主并跳过确认
npx --yes skills@latest add clawyi-com/china-market-data -g -y --agent cursor

# 只查看仓库中可安装的技能
npx --yes skills@latest add clawyi-com/china-market-data --list
```

也可在 [skills.sh](https://skills.sh/clawyi-com/china-market-data/china-market-data) 查看。不加 `-g` 时安装到当前项目，加 `-g` 后全局可用。Skills CLI 会复制仓库中除 `.git` 外的文件（包括 `tools/setup_env.py`），但不会安装 Python 依赖。

### 2. 安装 Python 依赖

需要 Python 3.9+。初始化脚本会在技能目录内创建 `.venv`、安装依赖并执行离线检查；全局安装的副本默认位于 `~/.agents/skills/china-market-data`。

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

> **更新后需重新初始化**：`npx skills update` 或重新安装会整体替换技能目录，目录内的 `.venv` 也会被删除。更新后请再运行一次上面的 `setup_env.py`，或者按下文把虚拟环境放在技能目录外。

`--check` 检查全部依赖，不请求行情。腾讯报价等入口只用标准库，可以不装全部依赖直接运行。依赖使用版本范围，没有为所有系统锁定完整组合；Windows 命令未经过完整平台实测。

业务 CLI 与 `run.py` 会自动切换到技能目录内的 `.venv`，不会自动安装依赖或修改全局 Python。作为 Python 库导入时，由调用方选择解释器。移动目录或换机器后应重新创建 `.venv`，不要复制已有虚拟环境。Windows 下文中的 `python3` 换成 `py -3`（没有 py 启动器时用 `python`）；输出流不支持中文时脚本自动改用 UTF-8。

### 3. 开发者安装

需要修改代码或保留完整 Git 历史时：

```bash
git clone https://github.com/clawyi-com/china-market-data.git
cd china-market-data
python3 tools/setup_env.py
```

手动复制或解压时，目标目录必须命名为 `china-market-data`，并保留 `SKILL.md`、`scripts/`、`references/`、`requirements.txt`、`LICENSE`、`NOTICE` 和 `UPSTREAM.md`；不能只复制一个 Markdown 文件。

### 虚拟环境放在技能目录外

技能目录只读，或希望更新技能时不重建环境，可把虚拟环境放在其他位置，之后一律用该解释器运行脚本（技能目录内没有 `.venv` 时，脚本直接使用调用它的 Python）：

```bash
python3 <技能目录>/tools/setup_env.py --venv ~/.venvs/china-market-data
~/.venvs/china-market-data/bin/python <技能目录>/scripts/run.py --check
```

Windows 对应为 `py -3 <技能目录>\tools\setup_env.py --venv $env:USERPROFILE\.venvs\china-market-data`，解释器位于其中的 `Scripts\python.exe`。结果文件写到当前目录，请在可写目录下运行，或用 `--output` 指定路径。

### 宿主要求

宿主需要能读取技能文件并执行本地 Python；只能聊天、不能执行脚本的环境无法直接取数。技能不依赖特定 agent ID 或额外的项目指引文件。各 agent 的独立安装副本不会自动同步，更新时脚本与文档一起更新。

## 命令行使用

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

这些检查不请求实时行情；离线测试通过不证明上游数据源此刻可用。GitHub Actions 会在 push 和 pull request 上执行编译、smoke tests、Skills CLI 发现与发布包校验。版本变化见 [CHANGELOG.md](CHANGELOG.md)，贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)，发布检查见 [docs/PUBLISHING.md](docs/PUBLISHING.md)。

## 许可证与致谢

代码按 [Apache License 2.0](LICENSE) 分发，保留上游 `Copyright 2026 Simon Lin`。再分发时应保留许可证及相关声明，并为修改文件注明改动；详情见 [NOTICE](NOTICE)。第三方依赖按各自许可证提供。

感谢 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 的原始工作。[上游更新历史](CHANGELOG.md) 保留用于追溯；上游版本号不代表本衍生版本已经发布了同名版本。
