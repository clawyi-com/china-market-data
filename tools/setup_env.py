"""Create or verify the isolated Python environment used by china-market-data."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 9)


def venv_python(venv: Path) -> Path:
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return venv / relative


def run(command: List[str], env: Optional[Dict[str, str]] = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=env)


def validate_venv_path(venv: Path) -> None:
    if venv.is_symlink():
        raise ValueError(f"虚拟环境路径不能是符号链接: {venv}")
    if venv.exists() and not venv.is_dir():
        raise ValueError(f"虚拟环境路径已存在且不是目录: {venv}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="创建技能专用 .venv、安装 requirements.txt 并运行离线依赖检查。"
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=ROOT / ".venv",
        help="虚拟环境目录，默认是技能根目录下的 .venv",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="不创建或安装，只使用现有虚拟环境运行检查",
    )
    args = parser.parse_args(argv)

    if sys.version_info < MIN_PYTHON:
        parser.error("需要 Python 3.9 或更高版本")

    venv = args.venv.expanduser().resolve()
    validate_venv_path(venv)
    python = venv_python(venv)

    if args.check_only:
        if not python.is_file():
            parser.error(f"未找到虚拟环境解释器: {python}")
    else:
        if not python.is_file():
            run([sys.executable, "-m", "venv", str(venv)])
        install_env = {
            **os.environ,
            "PIP_USER": "0",
            "PYTHONNOUSERSITE": "1",
        }
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(ROOT / "requirements.txt"),
            ],
            env=install_env,
        )

    check = subprocess.run(
        [str(python), str(ROOT / "scripts/run.py"), "--check"],
        text=True,
        capture_output=True,
    )
    if check.stdout:
        print(check.stdout.rstrip())
    if check.stderr:
        print(check.stderr.rstrip(), file=sys.stderr)
    if check.returncode:
        return check.returncode

    print(
        json.dumps(
            {
                "ready": True,
                "skill": str(ROOT),
                "venv": str(venv),
                "python": str(python),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
