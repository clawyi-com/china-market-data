<!-- Modified by china-market-data contributors: rewritten for this derivative distribution. See UPSTREAM.md. -->
# china-market-data

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-green.svg)](requirements.txt)
[![Release](https://img.shields.io/github/v/release/clawyi-com/china-market-data?include_prereleases&label=release)](https://github.com/clawyi-com/china-market-data/releases)
[![skills.sh](https://img.shields.io/badge/skills.sh-china--market--data-111111.svg)](https://skills.sh/clawyi-com/china-market-data/china-market-data)
[![Repo](https://img.shields.io/badge/github-clawyi--com%2Fchina--market--data-111111.svg)](https://github.com/clawyi-com/china-market-data)

[简体中文](README.md) · [Skill entry point](SKILL.md) · [Provenance](UPSTREAM.md) · [Apache-2.0](LICENSE)

**`clawyi-com/china-market-data`** is a **China stock data skill** that lets Cursor, Claude Code, Codex and other AI agents run bundled Python CLIs to fetch real A-share quotes, research reports, fund flows, announcements, limit-up boards, options, futures and macro data, with timestamps, coverage limits and fallback notes.

**15 capability layers · 87 endpoints (including 5 fallbacks) · 34 data sources · no API key needed except iwencai**

> This is not investment advice and not a paid market-data vendor SDK.

## Contents

- [30-second start](#30-second-start)
- [Ask your agent](#ask-your-agent)
- [Why this skill](#why-this-skill)
- [The 15 layers](#the-15-layers)
- [Data sources](#data-sources)
- [Installation](#installation)
- [Command-line usage](#command-line-usage)
- [Data boundaries](#data-boundaries)
- [Development](#development)
- [License](#license)

## 30-second start

```bash
# Detect Cursor, Claude Code, Codex and other supported hosts
npx --yes skills@latest add clawyi-com/china-market-data -g
```

Then ask your AI assistant directly. Standard-library endpoints such as Tencent quotes need no extra Python packages; run the [setup script](#2-install-python-dependencies) once before using the full catalog.

## Ask your agent

| You want | Ask something like |
| --- | --- |
| Quotes and valuation | “Kweichow Moutai's price, PE, PB, market cap and turnover right now” |
| Historical candles | “One year of forward-adjusted daily candles for CATL” |
| Limit-up sentiment | “Today's limit-up pool, consecutive-board ladder and failed-board rate” |
| Hot themes | “Which stocks are strong today and what themes are they tagged with” |
| Fund flows | “Northbound minute flows today”, “Concept boards ranked by 5-day main-force inflow” |
| Dragon-tiger list | “Today's market-wide dragon-tiger net buying, plus the broker seats for one stock” |
| Research | “Recent broker reports and consensus EPS for BYD” |
| Announcements and IR | “Latest announcement PDFs for a company”, “How did the company answer this rumor on the IR Q&A platform” |
| Options | “300ETF option chain, implied volatility and Greeks” |
| Futures and commodities | “Rebar main-continuous daily candles”, “SHFE top-20 open-interest members” |
| Macro and rates | “Latest LPR, FR007 and the ChinaBond treasury yield curve” |
| Events and convertibles | “IPO subscriptions this week”, “Convertible bond conversion premiums” |
| Backtest preparation | “Convert these codes to JoinQuant format and fetch historical Shenwan industry membership” |

The skill is not loaded for concept explanations or opinion discussions that need no data.

## Why this skill

- **Built for agents**: data endpoints ship as CLIs with `--help`; SKILL.md contains an endpoint routing table so the agent reads only the section it needs.
- **Keyless by default**: every endpoint except iwencai semantic search works without registration or API keys.
- **Official and stable sources first**: Tencent, exchanges, ChinaBond and the PBoC are preferred; East Money calls are throttled, and a fallback table covers primary-source failures.
- **Verifiable results**: quote source, quote time and fetch time are kept, missing values are distinct from real zeros, and failures are reported instead of returning empty data as success.
- **Runs locally**: data goes straight from each source to JSON files on your machine, with no third-party relay service.

Compared with Python data libraries such as akshare or tushare, this project is a skill package for AI agents: routing, parameters, data limits and fallbacks are written for the agent to read.

## The 15 layers

| Layer | Capabilities | Main sources |
| --- | --- | --- |
| 1 Prices | Live quotes (PE/PB/market cap/limit prices), daily/weekly/monthly adjusted and 1–60 min candles, ticks, market-wide daily packages, adjustment factors | Tencent, TDX, Baidu, Sina |
| 2 Research | Stock/industry reports and PDFs, ratings, consensus EPS, natural-language report search | East Money, THS, Sina, iwencai |
| 3 Signals | Strong stocks and themes, northbound flows, board membership, minute fund flows, dragon-tiger seats, lock-up expiries, industry and board rankings | THS, East Money |
| 4 Funds and chips | Margin trading, block trades, shareholder counts, dividends, daily fund flows, chip distribution, ETF shares | East Money, SSE, SZSE, local model |
| 5 News | Stock news, CLS telegraph, global 7×24 feeds, CCTV Xinwen Lianbo transcripts | East Money, CLS, Wallstreetcn, CCTV |
| 6 Fundamentals | Financial statements, F10, valuation history, listing/delisting, Shenwan industry history, ST list | Sina, TDX, baostock, Shenwan, East Money |
| 7 Announcements | Announcement search and PDF download | CNINFO |
| 8 Limit-up boards | Limit-up/failed/limit-down pools, limit-up reasons, board ladder and failure rate, watch list, unusual moves | East Money, THS |
| 9 ETF options | Contract list, option chain, Delta/Gamma/Theta/Vega, implied volatility | Sina |
| 10 Sentiment and IR | SZSE Hudongyi, SSE e-Interaction, THS and East Money popularity lists | CNINFO, SSE, THS, East Money |
| 11 Macro and rates | Social financing, PMI, ChinaBond yield curves, repo fixing rates, LPR, global macro calendar | PBoC, NBS, ChinaBond, CFETS |
| 12 Indexes and calendar | Index constituents and weights, index PE and dividend yield, official trading calendar | CSI, CNI, SZSE |
| 13 Futures and commodities | Daily data from five futures exchanges, commodity and index options, position rankings, live futures, A50, Shanghai Gold | Futures exchanges, Sina, SGE |
| 14 Corporate events | Earnings previews, institutional surveys, insider trades, buybacks, share pledges, IPO subscriptions | East Money |
| 15 Convertible bonds | Terms, conversion value, conversion premium | East Money |

Local tools also cover ticker normalization, JoinQuant code conversion and valuation. See the [SKILL.md routing table](SKILL.md#端点路由速查按需定位不必通读全文) for every endpoint, parameter and market limit; availability of a data type does not imply coverage of every market or date.

## Data sources

Tencent Finance · East Money · Tonghuashun (THS) · Sina Finance · Baidu · TDX · CNINFO · CLS · Wallstreetcn · CCTV · baostock · Shenwan · iwencai · SSE · SZSE · SHFE · INE · CZCE · GFEX · CFFEX · Shanghai Gold Exchange · CSI · CNI · ChinaBond · CFETS · PBoC · National Bureau of Statistics

See [sources and fallbacks](references/sources-and-fallbacks.md) for each endpoint's purpose, limits and fallback relationships.

## Installation

### 1. Install the skill (recommended)

Requires Node.js 22.20+ / npm. The Skills CLI installs directly from the GitHub repository; no npm package is needed. Using `skills@latest` explicitly avoids older global-directory issues:

```bash
# Interactive global install; detects installed agents
npx --yes skills@latest add clawyi-com/china-market-data -g

# Install for one host without prompts
npx --yes skills@latest add clawyi-com/china-market-data -g -y --agent cursor

# List installable skills in this repository
npx --yes skills@latest add clawyi-com/china-market-data --list
```

Also listed on [skills.sh](https://skills.sh/clawyi-com/china-market-data/china-market-data). Without `-g` the skill installs into the current project; with `-g` it is global. The Skills CLI copies the repository files except `.git` (including `tools/setup_env.py`) but does not install Python dependencies.

### 2. Install Python dependencies

Requires Python 3.9+. The setup script creates a skill-local `.venv`, installs dependencies and runs an offline check. A global install is normally at `~/.agents/skills/china-market-data`.

macOS / Linux:

```bash
SKILL_DIR="$HOME/.agents/skills/china-market-data"
python3 "$SKILL_DIR/tools/setup_env.py"
```

Windows PowerShell:

```powershell
$SkillDir = "$env:USERPROFILE\.agents\skills\china-market-data"
py -3 "$SkillDir\tools\setup_env.py"
```

> **Re-run setup after updates**: `npx skills update` or a reinstall replaces the whole skill directory, including its `.venv`. Run `setup_env.py` again after updating, or keep the virtual environment outside the skill directory as described below.

`--check` covers every listed dependency and does not request market data. Standard-library endpoints such as Tencent quotes run without the full dependency set. Dependencies use version ranges and are not locked for every platform; the Windows commands have not been fully tested on Windows.

Business CLIs and `run.py` switch to the skill-local `.venv` automatically; they never install packages or modify global Python. When importing as a Python library, the caller chooses the interpreter. Recreate `.venv` after moving directories or machines instead of copying it. On Windows, replace `python3` below with `py -3` (or `python` without the py launcher); scripts switch to UTF-8 when the output stream cannot encode Chinese.

### 3. Developer install

To modify code or keep full Git history:

```bash
git clone https://github.com/clawyi-com/china-market-data.git
cd china-market-data
python3 tools/setup_env.py
```

For manual copies or extracted archives, the target directory must be named `china-market-data` and keep `SKILL.md`, `scripts/`, `references/`, `requirements.txt`, `LICENSE`, `NOTICE` and `UPSTREAM.md`; a single Markdown file is not enough.

### Virtual environment outside the skill directory

If the skill directory is read-only, or you want updates not to rebuild the environment, create the virtual environment elsewhere and always run scripts with that interpreter (without a skill-local `.venv`, scripts use the Python that launched them):

```bash
python3 <skill-dir>/tools/setup_env.py --venv ~/.venvs/china-market-data
~/.venvs/china-market-data/bin/python <skill-dir>/scripts/run.py --check
```

On Windows use `py -3 <skill-dir>\tools\setup_env.py --venv $env:USERPROFILE\.venvs\china-market-data`; the interpreter is `Scripts\python.exe` inside it. Result files are written to the current directory, so run from a writable directory or pass `--output`.

### Host requirements

The host must be able to read skill files and run local Python; chat-only environments cannot fetch data directly. The skill does not depend on a specific agent ID or extra project guidance files. Separately installed agent copies do not sync automatically; update scripts and docs together.

## Command-line usage

Run from the skill root; use new output filenames.

```bash
# Live quotes: bare 000001 is Ping An Bank; SSE Composite needs sh000001
python3 scripts/tencent_quote.py sh000001 sz000001 510300 --output quotes.json

# Strong stocks and source-provided theme labels
python3 scripts/run.py ths_hot_reason.py --output hot.json

# Concept-board 5-day price change ranking (not the fund-flow ranking)
python3 scripts/run.py eastmoney_signals.py board-quotes --board-type concept --period 5d --top-n 20 --output boards.json

# Inspect command parameters
python3 scripts/run.py eastmoney_signals.py board-quotes --help
```

If the default board endpoint fails, try `--source dataapi` explicitly. It is still East Money, not an independent vendor, and does not guarantee bypassing same-origin failures. See [board ranking notes](references/signals-ranking.md#industry) for reduced fields and unit conversions.

Most CLIs write the full payload to JSON and print only a preview. Read the file; do not treat preview counts as complete data. `top` / `bottom` remain limited by `--top-n` and do not keep every intermediate rank.

The iwencai entry requires your own `IWENCAI_API_KEY`; see [prerequisites](SKILL.md#prerequisites). Do not commit keys, cookies or session files.

## Data boundaries

- Fetch time is not quote time; unknown times must not be inferred as realtime. Theme labels are not proven causes of price moves.
- Some history exists only as locally saved records and cannot be promised complete; adjustment, market scope and date semantics follow each API.
- Completing board pagination is not an atomic snapshot. `complete` means record coverage; `ranking_complete` means all change values are valid; missing rows stay in `missing`.
- East Money throttling is mainly in-process; concurrent agents do not get a cross-process global limiter automatically.
- Providers may rate-limit, change auth, omit fields, delay or retire endpoints. Failures must be reported explicitly; empty payloads must not pretend success.
- A few inherited endpoints still use plaintext HTTP (for example some strong-stock or futures paths). Treat content as observable/modifiable and not end-to-end safe for trading.
- This tool helps fetch and research data. It does not execute trades, promise returns, or act as a backtest engine.

**Open-source code does not mean open data rights.** Use, storage, display and redistribution of quotes, news, reports, announcements and other returned content must follow each provider's terms. Free or keyless access is not free commercial redistribution; this project has not obtained redistributable rights for those datasets item by item.

## Development

Run development checks from a Git checkout of this repository; release skill ZIP packages omit the test suite.

```bash
python3 -m compileall -q scripts tools tests
python3 -m unittest discover -s tests -v
python3 tools/build_release.py
npx --yes skills@latest add . --list
```

These checks do not request live market data; an offline pass does not prove providers are currently available. GitHub Actions runs compilation, smoke tests, Skills CLI discovery and bundle verification on pushes and pull requests. See [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/PUBLISHING.md](docs/PUBLISHING.md).

## License

Code is distributed under [Apache License 2.0](LICENSE), retaining upstream `Copyright 2026 Simon Lin`. Keep the license and notices when redistributing, and mark modified files; see [NOTICE](NOTICE). Third-party dependencies follow their own licenses.

Thanks to the original work in [a-stock-data](https://github.com/simonlin1212/a-stock-data). [CHANGELOG.md](CHANGELOG.md) keeps upstream history for provenance; upstream version numbers are not release claims for this derivative.
