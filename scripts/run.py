# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""Portable skill launcher. Uses skill-local .venv when present; never installs packages."""
import _runtime
import argparse
import importlib
import json
import sys

ROOT = _runtime.SCRIPTS_DIR.parent
DEPENDENCIES = ('requests', 'pandas', 'numpy', 'stockstats', 'baostock', 'mootdx', 'xlrd', 'openpyxl', 'lxml')
MIN_PYTHON = (3, 9)


def check():
    failures = {}
    for name in DEPENDENCIES:
        try:
            importlib.import_module(name)
        except Exception as exc:
            failures[name] = f'{type(exc).__name__}: {exc}'
    python_ok = sys.version_info >= MIN_PYTHON
    print(json.dumps({'python': sys.executable, 'python_version': '.'.join(map(str, sys.version_info[:3])),
                      'python_ok': python_ok, 'skill_venv': _runtime.in_skill_venv(),
                      'ready': python_ok and not failures, 'failures': failures,
                      'requirements': str(ROOT / 'requirements.txt')}, ensure_ascii=False))
    return int(not python_ok or bool(failures))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # 脚本名之后的参数原样转发（含 `--`），不交给本入口的 argparse 解析。
    if argv and not argv[0].startswith('-'):
        name, rest = argv[0], argv[1:]
        script = _runtime.SCRIPTS_DIR / name
        if (name != script.name or script.suffix != '.py' or name == 'run.py'
                or name.startswith('_') or not script.is_file()):
            print(f'run.py: error: 须指定 scripts 下的业务 .py 文件名: {name}', file=sys.stderr)
            return 2
        _runtime.exec_python(sys.executable, script, rest)
    parser = argparse.ArgumentParser(description=__doc__, usage='run.py (--check | <脚本名.py> [参数 ...])')
    parser.add_argument('--check', action='store_true', help='检查全部运行依赖，不访问数据源')
    args = parser.parse_args(argv)
    if not args.check:
        parser.error('请指定脚本或 --check')
    return check()


if __name__ == '__main__':
    raise SystemExit(main())
