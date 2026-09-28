# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""同花顺热点题材归因；保留日期、字段和值的原始转换规则。"""
try:
    import _runtime  # noqa: F401  须在第三方库之前导入
except ModuleNotFoundError:  # 单文件复制安装时没有 helper
    pass
import requests
import pandas as pd

def ths_hot_reason(date: str = None) -> pd.DataFrame:
    """
    同花顺当日强势股归因。
    date: 'YYYY-MM-DD' 格式，None=今天
    返回 DataFrame，含每只股票的题材标签 (reason)。

    实测: 73ms 拿到 ~125 只 + 完整字段
    """
    from datetime import date as _date
    if date is None:
        date = _date.today().strftime("%Y-%m-%d")

    url = (
        f"http://zx.10jqka.com.cn/event/api/getharden/"
        f"date/{date}/orderby/date/orderway/desc/charset/GBK/"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    if data.get("errocode", 0) != 0:
        raise RuntimeError(f"同花顺热点错误: {data.get('errormsg', '')}")

    rows = data.get("data") or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 字段重命名（中文友好）
    rename_map = {
        "name": "名称", "code": "代码", "reason": "题材归因",
        "close": "收盘价", "zhangdie": "涨跌额", "zhangfu": "涨幅%",
        "huanshou": "换手率%", "chengjiaoe": "成交额",
        "chengjiaoliang": "成交量", "ddejingliang": "大单净量",
        "market": "市场",
    }
    df = df.rename(columns=rename_map)
    return df


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="ths-hot-", suffix=".json", delete=False) as stream:
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
    from contextlib import redirect_stdout
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description="同花顺热点题材归因：完整表格保存，终端仅三行预览。")
    parser.add_argument("--date", help="原样传日期；省略使用本机今天 YYYY-MM-DD")
    parser.add_argument("--output", type=Path, help="完整 JSON 新文件，不覆盖已有路径")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        with redirect_stdout(sys.stderr):
            frame = ths_hot_reason(args.date)
        payload, preview = _frame_payload(frame), _frame_payload(frame.head(3))
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        path = _save_payload(encoded, args.output)
        print(json.dumps({"output": str(path), "row_count": len(frame), "preview_only": True,
                          "preview": preview}, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
