# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""mootdx 客户端与行情/财务/F10 命令；原选服与验活顺序保留。"""
try:
    import _runtime  # noqa: F401  须在第三方库之前导入
except ModuleNotFoundError:  # 单文件复制安装时没有 helper
    pass
import socket
from mootdx.quotes import Quotes

# 实测可用的备选服务器（按延迟排序，2026-06 验证）
_TDX_SERVERS = [
    ('119.97.185.59', 7709), ('124.70.133.119', 7709), ('116.205.183.150', 7709),
    ('123.60.73.44', 7709),  ('116.205.163.254', 7709), ('121.36.225.169', 7709),
    ('123.60.70.228', 7709), ('124.71.9.153', 7709),    ('110.41.147.114', 7709),
    ('124.71.187.122', 7709),
]

def _probe(ip, port, timeout=2.0):
    """TCP 握手探测（快速粗筛）。注意：握手成功 ≠ 能取数，必须再经 _validate 验活。"""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def _validate(client, market: str = 'std', check: str = 'bars') -> bool:
    """真实取数验活：坏服务器可 TCP 握手通过却回 2 字节空 body → 静默空表。用一次真实请求兜底。

    check='bars'   ：用 K 线请求验活（§1.7 行情类调用）；
    check='finance'：财务快照、F10 类别表里的「最新提示」及其正文都要取到才算活（§6.1 财务 / §6.2、§7.2 F10 调用），
                     只验财务会选中「财务正常、F10 为空」的服务器，F10 随后静默给空文本；
                     只看类别表非空，又会放过只回别的类别或畸形对象的服务器。
    两者要分开：2026-09 起通达信公开服务器的行情类命令（bars / quotes / transaction）普遍返回空表，
    而 finance / F10「最新提示」/ 除权除息仍正常（#52）。财务类调用若仍用 K 线验活，会被误判成「全部不可达」。
    验活样本 '000001' 是 A 股代码，只对 market='std' 有意义。其它市场（如扩展行情 'ext'）
    用它必然取不到数，会把所有正常服务器都判死、误报「全部不可达」，故非 std 时跳过验活。
    """
    if market != 'std':
        return True
    try:
        if check == 'finance':
            cats = client.F10C(symbol='000001')
            if not any(isinstance(c, dict) and c.get('name') == '最新提示' for c in cats):
                return False
            text = client.F10(symbol='000001', name='最新提示')
            if not isinstance(text, str) or not text.strip():
                return False
            df = client.finance(symbol='000001')
        else:
            df = client.bars(symbol='000001', frequency=9, offset=1)
        return df is not None and not df.empty
    except Exception:
        return False

def tdx_client(market='std', check='bars'):
    """
    创建 mootdx 客户端，规避 0.11.x BESTIP.HQ 空串 bug + 坏服务器静默空表（#43）。
    check: 'bars'（默认，K 线 / 盘口 / 逐笔）或 'finance'（财务快照 / F10），决定用哪类请求验活（#52）。
    每个候选都必须「真实取数验活」通过才采用（_probe TCP 握手是假阳性来源）：
      1) 顺序探测 _TDX_SERVERS，对 probe 通过者再 _validate 真实取数，取第一个验活成功的；
      2) 全部失败 → 回退 mootdx 自带 bestip 测速选优（同样验活）；
      3) 再回退裸 factory（老用户 config 已有可用 BESTIP 时成立）；
      4) 仍失败 → 抛 RuntimeError，明确报错而非静默返回空表 / 崩溃。
    """
    if check not in ('bars', 'finance'):
        raise ValueError("check 只能是 'bars' 或 'finance'")
    for ip, port in _TDX_SERVERS:
        if not _probe(ip, port):
            continue
        try:
            c = Quotes.factory(market=market, server=(ip, port))
            if _validate(c, market, check):
                return c
        except Exception:
            continue                                        # 握手过但取数崩 → 跳过下一台
    for kwargs in ({'bestip': True}, {}):                   # fallback: bestip 测速 / 裸 factory
        try:
            c = Quotes.factory(market=market, **kwargs)
            if _validate(c, market, check):
                return c
        except Exception:
            continue
    hint = ("海外网络通常全部超时（TCP 7709），请走国内代理或更新 _TDX_SERVERS 列表。")
    if check == 'bars':
        hint += ("若国内网络也如此：2026-09 起通达信公开服务器的 K 线 / 盘口 / 逐笔命令普遍返回空（#52），"
                 "K 线改用 §1.2 tencent_kline()（日周月 + 1~60 分钟）或 §1.3 tdx_daily_package()"
                 "（全市场当日日线含成交额），逐笔改用 §1.4 tencent_ticks()（当日）；"
                 "财务与 F10 用 tdx_client(check='finance') 仍可取。")
    raise RuntimeError("所有 mootdx 服务器均无法取到数据（TCP 可达但返回空 / 被 reset）。" + hint)


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="mootdx-", suffix=".json", delete=False) as stream:
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


def _result_payload(result):
    """DataFrame 用列列表与行数组保留重名列；其他返回按原值保存。"""
    import pandas as pd

    if not isinstance(result, pd.DataFrame):
        return _json_safe(result)
    if (isinstance(result.index, pd.CategoricalIndex) or isinstance(result.columns, pd.CategoricalIndex)
            or any(isinstance(dtype, pd.CategoricalDtype) for dtype in result.dtypes)):
        raise TypeError("CLI 暂不序列化分类类型元信息，请使用 Python 原生 API")
    index = result.index
    if isinstance(index, pd.MultiIndex):
        raise TypeError("CLI 暂不序列化 MultiIndex，请使用 Python 原生 API")
    index_meta = {"type": type(index).__name__, "dtype": str(index.dtype), "name": index.name,
                  "values": list(index)}
    if isinstance(index, pd.RangeIndex):
        index_meta.update(start=index.start, stop=index.stop, step=index.step)
    elif isinstance(index, pd.DatetimeIndex):
        index_meta.update(tz=str(index.tz) if index.tz is not None else None, freq=index.freqstr)
    if isinstance(result.columns, pd.MultiIndex):
        raise TypeError("CLI 暂不序列化 MultiIndex 列，请使用 Python 原生 API")
    return _json_safe({"type": "DataFrame", "columns": list(result.columns),
                       "columns_name": result.columns.name, "columns_dtype": str(result.columns.dtype),
                       "dtypes": [str(dtype) for dtype in result.dtypes], "index": index_meta,
                       "attrs": dict(result.attrs), "data": list(result.itertuples(index=False, name=None))})


def main(argv=None):
    import argparse
    from contextlib import redirect_stdout
    import json
    from pathlib import Path
    import sys
    import pandas as pd

    parser = argparse.ArgumentParser(description="mootdx 行情/财务/F10：全量保存，stdout 仅给预览。")
    parser.add_argument("method", choices=("bars", "quotes", "transaction", "finance", "F10C", "F10"))
    parser.add_argument("--params", required=True, help='原样传递方法关键字 JSON，如 {"symbol":"688017","frequency":9,"offset":10}')
    parser.add_argument("--market", default="std", help="原样传入 Quotes.factory，默认 std")
    parser.add_argument("--check", choices=("bars", "finance"), help="覆盖验活类型；财务/F10 默认 finance，其余 bars")
    parser.add_argument("--output", type=Path, help="完整 JSON 新文件；不覆盖已有路径")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        params = json.loads(args.params)
        if not isinstance(params, dict):
            raise ValueError("--params 必须是 JSON 对象")
        check = args.check or ("finance" if args.method in ("finance", "F10C", "F10") else "bars")
        with redirect_stdout(sys.stderr):
            client = tdx_client(market=args.market, check=check)
            result = getattr(client, args.method)(**params)
        payload = _result_payload(result)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        if isinstance(result, pd.DataFrame):
            count, preview = len(result), _result_payload(result.head(3))
        elif isinstance(result, list):
            count, preview = len(result), payload[:3]
        elif isinstance(result, str):
            count, preview = len(result), payload[:200]
        else:
            count, preview = None, {"type": type(result).__name__, "see_full_file": True}
        path = _save_payload(encoded, args.output)
        print(json.dumps({"output": str(path), "method": args.method, "check": check,
                          "count": count, "count_unit": "characters" if isinstance(result, str) else "rows",
                          "preview_only": True, "preview": preview}, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
