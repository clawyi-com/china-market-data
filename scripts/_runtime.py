# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""直接运行本目录脚本时修正无法输出中文的流编码并切换到技能内 .venv；作为库导入或进程内执行时不生效，从不安装依赖。"""
import os
from pathlib import Path
import subprocess
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
VENV_DIR = SCRIPTS_DIR.parent / ".venv"
_GUARD = "CHINA_MARKET_DATA_REEXEC"


def venv_python():
    for candidate in (VENV_DIR / "bin/python", VENV_DIR / "Scripts/python.exe"):
        if candidate.is_file():
            return candidate
    return None


def in_skill_venv():
    return VENV_DIR.is_dir() and Path(sys.prefix).resolve() == VENV_DIR.resolve()


def exec_python(python, script, args, env=None):
    """用指定解释器运行脚本并以其退出码结束；POSIX 原地替换进程，信号与 stdin 不经中转。"""
    command = [str(python), *getattr(subprocess, "_args_from_interpreter_flags", list)(), str(script), *args]
    env = os.environ if env is None else env
    sys.stdout.flush()
    sys.stderr.flush()
    if os.name == "posix":
        os.execve(command[0], command, env)
    raise SystemExit(subprocess.call(command, env=env))


def ensure_utf8_stdio():
    """输出流无法编码中文时（如英文 Windows 管道的 cp1252）改用 UTF-8；已能编码中文的设置保持不变。"""
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if not encoding or not hasattr(stream, "reconfigure"):
            continue
        try:
            "中文".encode(encoding)
        except (UnicodeEncodeError, LookupError):
            stream.reconfigure(encoding="utf-8", errors=stream.errors)


def _reexec_entry_script():
    main = sys.modules.get("__main__")
    entry = getattr(main, "__file__", None)
    # 解释器直接执行脚本时 __main__ 有 loader 且无 __spec__；runpy.run_path/run_module
    # 等进程内执行不满足，切换进程会丢掉调用方的补丁与审计钩子。
    direct = getattr(main, "__loader__", None) is not None and getattr(main, "__spec__", None) is None
    if not entry or not direct or Path(entry).resolve().parent != SCRIPTS_DIR:
        return
    ensure_utf8_stdio()
    python = venv_python()
    # 守卫变量防止损坏的 .venv（sys.prefix 不指向自身）导致无限重启。
    if python is None or in_skill_venv() or os.environ.get(_GUARD):
        return
    exec_python(python, Path(entry).resolve(), sys.argv[1:], {**os.environ, _GUARD: "1"})


_reexec_entry_script()
