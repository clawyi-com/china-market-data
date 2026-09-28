# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""申万行业变迁表与历史时点查询，保留官方代码口径。"""
try:
    import _runtime  # noqa: F401  须在第三方库之前导入
except ModuleNotFoundError:  # 单文件复制安装时没有 helper
    pass
import io

from typing import Optional

import pandas as pd
import requests

SW_URL = "https://www.swsresearch.com/swindex/pdf/SwClass2021/StockClassifyUse_stock.xls"


def sw_industry_history() -> pd.DataFrame:
    """申万行业归属变迁史 — 每只股票每次行业调整一行"""
    try:
        r = requests.get(SW_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        r.raise_for_status()
    except requests.exceptions.SSLError as e:
        # 2026-08-19 实测：纯 certifi 环境握手正常，证书链完整，无需手动补中间证书。
        # 保留此分支是为了在站点证书回归时给出可操作的提示，而不是吞掉异常。
        raise RuntimeError(
            "申万站点 SSL 握手失败。2026-08 实测其证书链正常，若你遇到此错误，"
            "多半是本机 CA 包过旧或中间人代理：先试 `pip install -U certifi`。"
            f"原始错误: {e}"
        ) from e
    df = pd.read_excel(io.BytesIO(r.content))
    df = df.rename(columns={"股票代码": "code", "计入日期": "start_date",
                            "行业代码": "industry_code", "更新日期": "update_date"})
    missing = {"code", "start_date", "industry_code"} - set(df.columns)
    if missing:
        raise RuntimeError(f"申万表结构变了，缺列 {sorted(missing)}；实际列={list(df.columns)}")
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["industry_code"] = df["industry_code"].astype(str).str.zfill(6)
    # 层级码要补成规范的 6 位（申万官方一级是 480000、二级是 480300），
    # 直接截断成 "48"/"4803" 无法与官方指数/名称表 join。
    df["l1_code"] = df["industry_code"].str[:2] + "0000"    # 一级，如 480000
    df["l2_code"] = df["industry_code"].str[:4] + "00"      # 二级，如 480300
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    return df.sort_values(["code", "start_date"]).reset_index(drop=True)


def sw_industry_as_of(df: pd.DataFrame, code: str, as_of: str) -> Optional[dict]:
    """某只股票在 as_of 日所属的申万行业（取不晚于该日的最后一次调整）"""
    code = str(code).zfill(6)
    sub = df[(df["code"] == code) & (df["start_date"] <= pd.Timestamp(as_of))]
    if sub.empty:
        return None                  # 该日尚未上市 / 无归属记录
    row = sub.iloc[-1]
    return {"code": code, "as_of": as_of,
            "industry_code": row["industry_code"],
            "l1_code": row["l1_code"], "l2_code": row["l2_code"],
            "since": row["start_date"].strftime("%Y-%m-%d")}



def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="sw-industry-", suffix=".json", delete=False) as stream:
            stage = Path(stream.name)
            stream.write(encoded + "\n")
        if output is None:
            result, stage = stage, None
            return result.resolve()
        # 优先原子发布；仅链接能力受限时降级，不掩盖目标冲突、磁盘满等错误。
        import errno
        import shutil
        try:
            os.link(stage, output)
        except (OSError, NotImplementedError) as exc:
            unsupported = {errno.EPERM, errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}
            if isinstance(exc, OSError) and exc.errno not in unsupported:
                raise
            created = None
            try:
                # xb 使用独占创建，目标在此刻出现（含悬空符号链接）也不会覆盖。
                # 此兼容路径写完前目标可见；消费者须等待 CLI 成功再读取。
                with Path(output).open("xb") as destination:
                    created = os.fstat(destination.fileno())
                    with stage.open("rb") as source:
                        shutil.copyfileobj(source, destination)
            except BaseException:
                # 清理自己创建的半成品；不要删除已被其他进程替换的文件。
                if created is not None:
                    try:
                        current = Path(output).lstat()
                    except FileNotFoundError:
                        pass
                    else:
                        if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                            Path(output).unlink()
                raise
        return Path(output).resolve()
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)


def _json_safe(value):
    """保留缺失值、非有限值和日期类型，不使用 default=str。"""
    from datetime import date, datetime
    import math
    import pandas as pd

    if value is pd.NA:
        return {"$missing": "NA"}
    if value is pd.NaT:
        return {"$missing": "NaT"}
    if isinstance(value, (datetime, date)):
        return {"$date_type": type(value).__name__, "iso": value.isoformat()}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"$float": "NaN" if math.isnan(value) else
                                                   "Infinity" if value > 0 else "-Infinity"}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON 对象键必须为字符串")
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return _json_safe(value.item())
    raise TypeError(f"无法无歧义地序列化 {type(value).__name__}")


def _index_payload(index):
    """保存 表格多层列名及其层级编码。"""
    if isinstance(index, pd.CategoricalIndex):
        raise TypeError("CLI 暂不支持分类索引，请用 Python API")
    result = {"type": type(index).__name__}
    if isinstance(index, pd.MultiIndex):
        result.update(names=list(index.names), levels=[_index_payload(level) for level in index.levels],
                      codes=[list(code) for code in index.codes], sortorder=index.sortorder)
    else:
        result.update(name=index.name, dtype=str(index.dtype), values=list(index))
        if isinstance(index, pd.RangeIndex):
            result.update(start=index.start, stop=index.stop, step=index.step)
        elif isinstance(index, pd.DatetimeIndex):
            result.update(tz=str(index.tz) if index.tz is not None else None, freq=index.freqstr)
    return result


def _frame_payload(frame):
    if any(isinstance(dtype, pd.CategoricalDtype) for dtype in frame.dtypes):
        raise TypeError("CLI 暂不支持分类列，请用 Python API")
    return _json_safe({"type": "DataFrame", "columns": list(frame.columns),
                       "columns_index": _index_payload(frame.columns),
                       "dtypes": [str(dtype) for dtype in frame.dtypes], "index": _index_payload(frame.index),
                       "attrs": dict(frame.attrs), "data": list(frame.itertuples(index=False, name=None))})


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description="申万行业历史与时点归属：完整JSON保存。")
    commands = parser.add_subparsers(dest="command", required=True)
    history = commands.add_parser("history", help="完整行业变迁表")
    asof = commands.add_parser("as-of", help="下载一次表并查询指定时点；批量使用Python复用表")
    asof.add_argument("code")
    asof.add_argument("date")
    for command in (history, asof):
        command.add_argument("--output", type=Path, help="完整JSON新文件，不覆盖")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        frame = sw_industry_history()
        if args.command == "history":
            payload, preview = _frame_payload(frame), _frame_payload(frame.head(3))
        else:
            payload = preview = _json_safe(sw_industry_as_of(frame, args.code, args.date))
        path = _save_payload(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2), args.output)
        summary = {"output": str(path), "preview_only": True, "preview": preview}
        if args.command == "history":
            summary["row_count"] = len(frame)
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
