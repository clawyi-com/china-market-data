<!-- Modified by china-market-data contributors: rewritten for this derivative distribution. See UPSTREAM.md. -->
# china-market-data

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-green.svg)](requirements.txt)
[![Release](https://img.shields.io/github/v/release/clawyi-com/china-market-data?include_prereleases&label=release)](https://github.com/clawyi-com/china-market-data/releases)
[![skills.sh](https://img.shields.io/badge/skills.sh-china--market--data-111111.svg)](https://skills.sh/clawyi-com/china-market-data/china-market-data)
[![Repo](https://img.shields.io/badge/github-clawyi--com%2Fchina--market--data-111111.svg)](https://github.com/clawyi-com/china-market-data)

[简体中文](README.md) · [Skill entry point](SKILL.md) · [Provenance](UPSTREAM.md) · [Apache-2.0](LICENSE)

**`clawyi-com/china-market-data`** is a **China stock data skill** for Chinese-market users: A-share quotes, K-line, ticks, research reports, fund flow, announcements, ETFs, futures and macro data, exposed to Claude Code / AI agents / Python CLI with timestamps, coverage, fields and fallback notes.

> This is not investment advice and not a paid market-data vendor SDK.

## Contents

- [30-second start](#30-second-start)
- [Coverage](#coverage)
- [Changes from upstream](#changes-from-upstream)
- [Installation](#installation)
- [Quick usage](#quick-usage)
- [Data boundaries](#data-boundaries)
- [Development](#development)
- [License](#license)

## 30-second start

```bash
# Detect Cursor, Claude Code, Codex and other supported hosts
npx skills add clawyi-com/china-market-data -g
```

After installation, ask your AI assistant questions such as “fetch the latest Kweichow Moutai quote” or “get one year of CSI 300 candles.” Standard-library endpoints such as Tencent quotes need no extra Python packages. Set up the [Python dependencies](#2-install-python-dependencies) before using the full data-source catalog.

## Coverage

| Area | Examples |
| --- | --- |
| Prices | Stock, index and ETF quotes; candles, ticks, daily packages and adjustment factors |
| Market signals | Strong stocks and source theme labels, board membership, price rankings, fund flows, trading disclosures and price-limit activity |
| Company research | Reports, announcements, financial statements, valuation, shareholders, dividends, lockups and events |
| Related markets | Macro and rates, index constituents and calendars, futures, commodities, ETF options and convertible bonds |

Consult the routing table in [SKILL.md](SKILL.md) and its linked references for exact markets, dates and parameters. Capability names do not imply complete coverage.

## Changes from upstream

- Executable scripts and focused reference documents replace embedded implementations in a long skill document.
- CLI interfaces, output protection, environment checks and a skill-local virtual environment.
- Complete-page validation for industry rankings, with separate commands for price changes and fund flows.
- Source and time metadata, and explicit treatment of missing values versus zero.
- Frozen upstream fixtures and regression tests for migrations and intentional fixes.

These changes do not guarantee provider availability or certify every AI host.

## Installation

### 1. Install the skill (recommended)

Node.js / npm is required. The Skills CLI uses GitHub as the skill source; this repository does not need to be published as an npm package:

```bash
# Interactive global install; detects installed agents
npx skills add clawyi-com/china-market-data -g

# Target one host and skip confirmation
npx skills add clawyi-com/china-market-data -g -y --agent cursor

# Inspect available skills without installing
npx skills add clawyi-com/china-market-data --list
```

See the installable skill on [skills.sh](https://skills.sh/clawyi-com/china-market-data/china-market-data). Without `-g`, installation is scoped to the current project; `-g` makes it available globally. The Skills CLI installs files such as `SKILL.md`, `scripts/` and `references/`; it does not install Python dependencies.

### 2. Install Python dependencies

Python 3.9+ is required; Python 3.12 is the tested recommendation. The canonical copy from a global `npx skills` install is normally at `~/.agents/skills/china-market-data`.

macOS / Linux:

```bash
SKILL_DIR="$HOME/.agents/skills/china-market-data"
python3 -m venv "$SKILL_DIR/.venv"
PIP_USER=0 "$SKILL_DIR/.venv/bin/python" -m pip install -r "$SKILL_DIR/requirements.txt"
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/run.py" --check
```

Windows PowerShell:

```powershell
$SkillDir = "$env:USERPROFILE\.agents\skills\china-market-data"
py -3 -m venv "$SkillDir\.venv"
$env:PIP_USER = "0"
& "$SkillDir\.venv\Scripts\python.exe" -m pip install -r "$SkillDir\requirements.txt"
& "$SkillDir\.venv\Scripts\python.exe" "$SkillDir\scripts\run.py" --check
```

The check imports all listed dependencies without requesting market data. Standard-library-only commands such as Tencent quotes do not require the entire dependency set. Requirements are version ranges, not a complete cross-platform lockfile. Windows has not been fully tested.

Most business CLIs use the skill-local `.venv`; `run.py` can also launch scripts. Dependencies are not installed automatically and the global Python is not modified. When importing as a library, the caller chooses the interpreter. Recreate `.venv` after moving directories or machines; do not copy an existing virtualenv.

Windows usually lacks `python3`; replace `python3` below with `py -3`, or `python` if the launcher is unavailable. When the output encoding cannot represent Chinese (for example cp1252 on English Windows pipes), scripts switch to UTF-8 output and consumers should decode as UTF-8.

### 3. Developer installation

Use a Git checkout when modifying code or retaining complete history:

```bash
git clone https://github.com/clawyi-com/china-market-data.git
cd china-market-data
python3 -m venv .venv
PIP_USER=0 .venv/bin/python -m pip install -r requirements.txt
python3 scripts/run.py --check
```

For manual copies or release archives, the target directory must be named `china-market-data`. Keep `SKILL.md`, `scripts/`, `references/`, `requirements.txt`, `LICENSE`, `NOTICE` and `UPSTREAM.md` together; a single Markdown download is insufficient.

### Read-only skill directory

If the host installs the skill read-only, create the virtualenv in a writable location and always use that interpreter. Without a local `.venv`, scripts use the calling Python as-is:

```bash
python3 -m venv ~/.venvs/china-market-data
PIP_USER=0 ~/.venvs/china-market-data/bin/python -m pip install -r <skill-dir>/requirements.txt
~/.venvs/china-market-data/bin/python <skill-dir>/scripts/run.py --check
```

On Windows: `py -3 -m venv $env:USERPROFILE\.venvs\china-market-data`, interpreter under `Scripts\python.exe`. Result files write to the current directory; run from a writable location or pass `--output`.

### Using with AI assistants

Prefer `npx skills add`, which detects hosts such as Cursor, Claude Code and Codex and installs to the appropriate location. For a manual fallback, copy the entire directory into a host-supported skill path. Other assistants must be able to read skill files and run local Python. Chat-only environments cannot fetch data directly.

The skill does not depend on a specific agent ID or `CLAUDE.md`. Any `CLAUDE.md` is optional research guidance, not required to run CLIs. Update scripts and docs together; separately installed agent copies do not sync automatically.

## Quick usage

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

Develop against a Git checkout that retains the upstream baseline commit; skill ZIP packages omit the test suite.

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tests/audit_installed_bundle.py
python3 tools/build_release.py
```

Some tests need full Git history; shallow clones or GitHub auto-generated source archives may fail those checks. Optional live tests are skipped by default; offline pass does not prove providers are available now. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/PUBLISHING.md](docs/PUBLISHING.md).

## License

Code is distributed under [Apache License 2.0](LICENSE), retaining upstream `Copyright 2026 Simon Lin`. Keep the license and notices when redistributing, and mark modified files; see [NOTICE](NOTICE). Third-party dependencies follow their own licenses.

Thanks to the original work in [a-stock-data](https://github.com/simonlin1212/a-stock-data). [CHANGELOG.md](CHANGELOG.md) keeps upstream history for provenance; upstream version numbers are not release claims for this derivative.
