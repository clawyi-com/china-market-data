# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""腾讯最近交易日逐笔；保持原分页、节流、成交额及缺笔校验。"""
import _runtime  # noqa: F401  须在第三方库之前导入
from _ticker import get_prefix, norm_ticker
from _market_common import _v39_http, _v39_src_date, _v39_req_num, _v39_contract, _v39_frame

import re
import time

TENCENT_TICK_URL = "https://stock.gtimg.cn/data/index.php"
TENCENT_QT_URL = "https://qt.gtimg.cn/q="
_TICK_MAX_PAGES = 300            # 一页 70 笔；2026-09-22 实测最活跃的票全天约 4800 笔 / 69 页
_TICK_SESSION_END = "15:00:59"   # 连续竞价 + 收盘集合竞价到此为止（科创板收盘那笔在 15:00:02），之后是盘后定价


def _tencent_qt_snapshot(symbol):
    """腾讯行情快照 → (交易日 'YYYY-MM-DD', 时刻 'HHMMSS', 当日成交额 元)。代码不存在抛 ValueError。"""
    response = _v39_http(TENCENT_QT_URL + symbol)
    text = response.content.decode("gbk", "replace")
    if "v_pv_none_match" in text:
        raise ValueError(f"腾讯没有 {symbol} 这个代码")
    match = re.search(rf'v_{symbol}="([^"]*)"', text)
    if not match:
        raise RuntimeError(f"腾讯行情快照 {symbol} 的返回里没有 v_{symbol} 变量，格式可能已变")
    fields = match.group(1).split("~")
    if len(fields) < 36 or not re.fullmatch(r"[0-9]{14}", fields[30]):
        raise RuntimeError(f"腾讯行情快照 {symbol} 字段数 {len(fields)} 或时间字段不对，格式可能已变")
    parts = fields[35].split("/")          # 「最新价/成交量/成交额(元)」；科创板的成交量是股、其余是手，所以只用成交额
    if len(parts) != 3:
        raise RuntimeError(f"腾讯行情快照 {symbol} 的价/量/额字段是 {fields[35]!r}，格式可能已变")
    day = _v39_src_date(fields[30][:8])
    amount = _v39_req_num(parts[2], "成交额")
    if not re.fullmatch(r"(?:[01][0-9]|2[0-3])[0-5][0-9][0-5][0-9]", fields[30][8:]):
        raise RuntimeError(f"腾讯行情快照 {symbol} 时刻非法: {fields[30][8:]!r}")
    if amount < 0:
        raise RuntimeError(f"腾讯行情快照 {symbol} 成交额不能为负: {amount}")
    return day, fields[30][8:], amount


def _tencent_tick_page(symbol, page):
    """第 page 页逐笔（0 起）→ 记录列表；翻过最后一页时腾讯返回空内容，返回 None。"""
    response = _v39_http(TENCENT_TICK_URL, params={"appn": "detail", "action": "data", "c": symbol, "p": page})
    text = response.content.decode("gbk", "replace").strip()
    if not text:
        return None
    match = re.fullmatch(rf'v_detail_data_{symbol}=\[(\d+),"([^"]*)"\];?', text)
    if not match or int(match.group(1)) != page:
        raise RuntimeError(f"腾讯逐笔 {symbol} 第 {page} 页不是预期格式: {text[:80]!r}")
    if not match.group(2):
        return None
    records = []
    try:
        for item in match.group(2).split("|"):
            seq, clock, price, change, volume, amount, side = item.split("/")
            if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]", clock) or side not in ("B", "S", "M"):
                raise ValueError(item)
            records.append({"seq": int(seq), "time": clock, "price": _v39_req_num(price, "price"),
                            "change": _v39_req_num(change, "change"), "volume": _v39_req_num(volume, "volume"),
                            "amount": _v39_req_num(amount, "amount"), "side": side})
            for field in ("price", "volume", "amount"):
                if records[-1][field] < 0:
                    raise ValueError(f"{field} 不能为负: {records[-1][field]}")
    except ValueError as exc:      # 字段数不对 / 序号不是整数 / 方向认不出：源格式变了，不是参数错
        raise RuntimeError(f"腾讯逐笔 {symbol} 第 {page} 页记录格式改变: {exc}") from exc
    return records


@_v39_contract
def tencent_ticks(code):
    """腾讯逐笔成交（分笔）— 最近一个交易日的全部成交明细，沪深个股与 ETF。

    一行一笔：date / code / time / seq（腾讯序号）/ price / change（较上一笔）/ volume（手）/ amount（元）/
    side（B 主动买 · S 主动卖 · M 中性）。约 3 秒一笔的分笔，不是 Level-2 逐笔。
    北交所、指数、代码不存在、当日没有成交抛 ValueError。收盘后调用会用行情快照的当日成交额核对连续竞价段，
    对不上抛 RuntimeError；盘后定价段腾讯偶尔缺几笔，缺的序号在 frame.attrs["missing_seq"]。
    """
    prefix, ticker = get_prefix(code), norm_ticker(code)
    if prefix == "bj":
        raise ValueError("腾讯逐笔不支持北交所（返回空）；北交所日线见 §1.3 tdx_daily_package")
    if (prefix, ticker[:3]) in (("sh", "000"), ("sz", "399")):
        raise ValueError(f"{prefix}{ticker} 是指数，没有逐笔成交")
    symbol = prefix + ticker
    day, clock, amount_before = _tencent_qt_snapshot(symbol)
    if amount_before == 0:
        raise ValueError(f"{symbol} 在 {day} 没有成交（停牌、尚未开盘或集合竞价未撮合）")
    rows, missing = [], []
    for page in range(_TICK_MAX_PAGES):
        records = _tencent_tick_page(symbol, page)
        if records is None:
            break
        for r in records:
            expected = rows[-1]["seq"] + 1 if rows else 0
            if r["seq"] < expected or (rows and r["time"] < rows[-1]["time"]):
                raise RuntimeError(f"腾讯逐笔 {symbol} 序号或时间倒退（第 {page} 页 {r['seq']} {r['time']}），结果不可信")
            if r["seq"] > expected:
                if r["time"] <= _TICK_SESSION_END:
                    raise RuntimeError(f"腾讯逐笔 {symbol} 缺序号 {expected}–{r['seq'] - 1}（{r['time']} 之前，第 {page} 页），"
                                       "腾讯该页缓存不完整，稍后重试")
                missing.extend(range(expected, r["seq"]))
            rows.append(r)
        time.sleep(0.1)
    else:
        raise RuntimeError(f"腾讯逐笔 {symbol} 翻到第 {_TICK_MAX_PAGES} 页仍未结束，格式可能已变")
    if not rows:
        if clock < "092500":
            raise ValueError(f"{symbol} 集合竞价尚未撮合（{clock}），还没有逐笔")
        raise RuntimeError(f"{symbol} 在 {day} 成交 {amount_before:.0f} 元，腾讯逐笔却为空："
                           "开盘前腾讯可能已清空上一交易日的明细，否则是接口变了")
    day_after, _, amount_after = _tencent_qt_snapshot(symbol)
    if day_after != day:
        raise RuntimeError(f"取数期间交易日从 {day} 变成 {day_after}，请重试")
    session = sum(r["amount"] for r in rows if r["time"] <= _TICK_SESSION_END)
    # 两次快照成交额相同说明取数期间没有新成交（收盘后 / 午休 / 停牌），此时连续竞价段逐笔合计应与当日成交额相符
    if amount_after == amount_before and abs(session - amount_before) > amount_before * 0.001 + 1000:
        raise RuntimeError(f"腾讯逐笔 {symbol} 连续竞价段成交额 {session:.0f} 元，与行情快照 {amount_before:.0f} 元对不上，"
                           "逐笔可能不全")
    frame = _v39_frame(rows, "tencent", f"{TENCENT_TICK_URL}?appn=detail&action=data&c={symbol}",
                       ["time", "seq", "price", "change", "volume", "amount", "side"])
    frame.insert(0, "date", day)
    frame.insert(1, "code", symbol)
    frame.attrs["missing_seq"] = missing
    return frame


def _json_safe(value):
    """显式保存缺失/非有限值；不使用 default=str 静默改变类型。"""
    import math

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return {"$float": "NaN" if math.isnan(value) else
                ("Infinity" if value > 0 else "-Infinity")}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    # numpy 标量转为等值 Python 标量；逐笔字段没有任意对象列。
    if hasattr(value, "item"):
        return _json_safe(value.item())
    raise TypeError(f"无法无歧义地序列化 {type(value).__name__}")


def _frame_payload(frame):
    """保留本接口的列顺序、类型、RangeIndex、attrs 与全部行。"""
    index = frame.index
    return _json_safe({
        "columns": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "index": {"type": type(index).__name__, "name": index.name,
                  "start": index.start, "stop": index.stop, "step": index.step},
        "attrs": dict(frame.attrs),
        "data": frame.to_dict("records"),
    })


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="tencent-ticks-", suffix=".json", delete=False) as stream:
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


def main(argv=None):
    import argparse
    from contextlib import redirect_stdout
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(
        description="腾讯最近交易日逐笔：完整 JSON 落盘，stdout 仅显示路径与预览。",
        epilog="沪深个股与 ETF；成交量为手、成交额为元。仅最近交易日，不支持历史、北交所或指数。",
    )
    parser.add_argument("code", help="证券代码字符串，例如 000001、sh600519、510300")
    parser.add_argument("--output", type=Path, help="完整 JSON 的新文件路径；父目录须存在，不覆盖已有文件")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        with redirect_stdout(sys.stderr):
            frame = tencent_ticks(args.code)
        payload = _frame_payload(frame)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        path = _save_payload(encoded, args.output)
        preview = dict(payload)
        preview["data"] = payload["data"][:3]
        print(json.dumps({"output": str(path), "row_count": len(frame),
                          "preview_only": True, "preview": preview},
                         ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
