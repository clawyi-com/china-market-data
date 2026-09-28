<!-- Modified by china-market-data contributors: rewritten for this derivative distribution. See UPSTREAM.md. -->
# china-market-data

[简体中文](README.md) · [Skill entry point](SKILL.md) · [Provenance](UPSTREAM.md) · [Apache-2.0](LICENSE)

Chinese securities-market data tools for AI assistants and Python users. The skill maps requests to executable CLIs, with documentation for timestamps, coverage, fields and fallback limitations.

This independently maintained derivative is based on [a-stock-data](https://github.com/simonlin1212/a-stock-data), under Apache-2.0. The upstream author does not endorse or maintain this derivative. See [UPSTREAM.md](UPSTREAM.md) and [NOTICE](NOTICE) for the baseline and attribution.

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

Python 3.9+ is required; Python 3.12 is the tested recommendation. Package installation requires package-index access; fetching data requires access to the relevant provider.

Extract the skill release into `china-market-data/`, or use a Git checkout retaining upstream history. Keep `SKILL.md`, `scripts/`, `references/`, `requirements.txt`, `LICENSE`, `NOTICE` and `UPSTREAM.md` together. A single Markdown download is insufficient.

When using `git clone`, name the target directory `china-market-data` to match the `name` in `SKILL.md`. Agent Skills expects the skill name to equal its directory name; the default clone directory `a-stock-data` may prevent loading or register the skill under the wrong name:

```bash
git clone <this-project-repository-url> ~/.claude/skills/china-market-data
```

From the skill root on macOS / Linux:

```bash
python3 -m venv .venv
PIP_USER=0 .venv/bin/python -m pip install -r requirements.txt
python3 scripts/run.py --check
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
$env:PIP_USER = "0"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
py -3 scripts/run.py --check
```

The check imports all listed dependencies without requesting market data. Standard-library-only commands such as Tencent quotes do not require the entire dependency set. Requirements are version ranges, not a complete cross-platform lockfile. Windows has not been fully tested.

Most business CLIs use a skill-local `.venv` if present. `run.py` provides a common launcher. Neither installs dependencies nor changes global Python. Library callers choose their own interpreter. Recreate the environment after moving the installation or changing machines.

Windows usually has no `python3` command; replace `python3` in the examples below with `py -3`, or `python` if the py launcher is not installed. When an output stream cannot encode Chinese (for example cp1252 pipes on English Windows), scripts switch that stream to UTF-8; readers should decode output as UTF-8.

### Read-only skill directory

If the host installs skills in a read-only location, `.venv` cannot be created there. Create the environment in a writable location and always run scripts with that interpreter. Without a skill-local `.venv`, scripts keep the interpreter that launched them:

```bash
python3 -m venv ~/.venvs/china-market-data
PIP_USER=0 ~/.venvs/china-market-data/bin/python -m pip install -r <skill-dir>/requirements.txt
~/.venvs/china-market-data/bin/python <skill-dir>/scripts/run.py --check
```

On Windows use `py -3 -m venv $env:USERPROFILE\.venvs\china-market-data`; the interpreter is `Scripts\python.exe` inside it. Result files are written relative to the current directory, so run from a writable directory or pass a writable `--output` path.

### AI hosts

Install the entire directory in the host's configured skills location, for example `~/.claude/skills/china-market-data/` for Claude Code or the default `~/.codex/skills/china-market-data/` for Codex. Custom configurations may differ. The host must be able to read the skill and execute Python; a chat-only environment cannot run these data tools.

There is no dependency on Keyi, a particular agent ID or `CLAUDE.md`. The repository's `CLAUDE.md` is optional research-assistant guidance. Update scripts and documentation together; separate agent installations do not update automatically.

## Examples

Run from the skill root and use a new output filename each time:

```bash
# Bare 000001 means Ping An Bank; sh000001 means the Shanghai Composite
python3 scripts/tencent_quote.py sh000001 sz000001 510300 --output quotes.json

# Strong stocks and provider-supplied theme labels
python3 scripts/run.py ths_hot_reason.py --output hot.json

# Five-day concept-board price ranking, not a fund-flow ranking
python3 scripts/run.py eastmoney_signals.py board-quotes --board-type concept --period 5d --top-n 20 --output boards.json

python3 scripts/run.py eastmoney_signals.py board-quotes --help
```

If the default board endpoint fails, `--source dataapi` is an explicit alternative. It is still Eastmoney, not an independent provider, and has fewer fields. See [ranking documentation](references/signals-ranking.md#industry).

Most CLIs save their full return structure to JSON and print only a preview. Read the saved file. Ranking `top` and `bottom` lists are themselves bounded by `--top-n`; intermediate ranks are not all saved.

The iwencai integration requires your own `IWENCAI_API_KEY`; configuration is documented in [SKILL.md](SKILL.md). Never commit credentials or session files.

## Limitations and data rights

- Fetch time is not quote time. Unknown freshness must not be described as live; theme labels are not proof of causation.
- History may be limited to locally saved observations. Adjustment, market and date semantics vary by endpoint.
- Complete pagination is not an atomic market snapshot. `complete` describes record coverage; `ranking_complete` describes availability of valid price changes. Missing records are retained separately.
- Eastmoney throttling is primarily per process, not a global limiter across concurrent agents.
- Providers may change authentication, limit access or return delayed, missing or unavailable data. Report failures explicitly.
- Some inherited endpoints still use plaintext HTTP, including strong-stock and certain futures endpoints. Traffic may be observed or modified; this is not an end-to-end secure trading data feed.
- This is a data and research tool, not a trading executor, return guarantee or backtesting engine.

**The code license does not license provider data.** Use, storage, display and redistribution of quotes, news, reports and other results remain subject to the relevant terms. Free or keyless access is not a commercial redistribution grant; this project has not obtained blanket data-redistribution permission.

## Development

Use a Git checkout retaining the upstream baseline; the skill ZIP excludes tests.

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python tests/audit_installed_bundle.py
python3 tools/build_release.py
```

Some tests require Git history and will not work in a shallow clone or GitHub-generated source archive. Optional live tests are skipped by default. Offline success does not establish current provider availability. See [CONTRIBUTING.md](CONTRIBUTING.md) and [publishing instructions](docs/PUBLISHING.md).

## License and acknowledgments

Distributed under [Apache-2.0](LICENSE), retaining `Copyright 2026 Simon Lin`. Preserve the license and applicable notices, and mark modified files when redistributing. See [NOTICE](NOTICE). Dependencies retain their own licenses.

Thanks to the [upstream project](https://github.com/simonlin1212/a-stock-data). Historical upstream releases remain in [CHANGELOG.md](CHANGELOG.md); they are not release claims for this derivative.
