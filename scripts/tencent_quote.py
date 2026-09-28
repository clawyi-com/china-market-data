# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""腾讯实时行情：原生 Python 函数与标准库 CLI（Python 3.9+）。"""

import urllib.request
from datetime import datetime, timezone, timedelta

def tencent_quote(codes: list[str]) -> dict[str, dict]:
    """
    批量拉取腾讯财经实时行情。
    codes: ["688017", "300476", "002463"]
    也支持指数: ["sh000001", "000300", "399006"]（裸 000001 是平安银行）
    也支持ETF: ["510050", "510300"]
    返回: {code: {name, price, pe_ttm, pb, mcap, ...}}
    """
    # 前缀路由：与全局 get_prefix() 一致。5x 沪ETF / 000300 等沪指数不能落到 sz（会返回空或错票）。
    SH_INDEX = {"000300", "000905", "000016", "000688", "000852", "000010"}   # 沪指数白名单
    prefixed = []
    key_of = {}          # 带前缀的查询键 → 调用方原始写法，保证结果键与入参一一对应
    for c in codes:
        low = c.lower()
        if low.startswith(("sh", "sz", "bj")):        # 显式前缀透传，解决 000001 等歧义
            p = low
        elif c.startswith("92"):                      # 北交所 920 号段须先于 9x 判断
            p = f"bj{c}"
        elif c in SH_INDEX or c.startswith(("5", "6", "9")):
            p = f"sh{c}"
        elif c.startswith(("4", "8")):
            p = f"bj{c}"
        else:
            p = f"sz{c}"
        prefixed.append(p)
        key_of[p] = c    # 显式前缀入参原样返回，裸代码返回裸代码

    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=10)
    data = resp.read().decode("gbk")

    fetched_at = datetime.now(timezone.utc).isoformat()
    result = {}
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        # 用入参原样做键：批量里同时传 sh000001 与 sz000001 时，若都退回裸 6 位码
        # 会撞成同一个键、后者静默覆盖前者，显式前缀这个特性就白做了。
        code = key_of.get(key, key[2:])
        raw_time = vals[30]
        try:
            quote_time = datetime.strptime(raw_time, "%Y%m%d%H%M%S").replace(
                tzinfo=timezone(timedelta(hours=8))).isoformat() if len(raw_time) == 14 else None
        except ValueError:
            quote_time = None
        result[code] = {
            "source": "https://qt.gtimg.cn/",
            "quote_time": quote_time,
            "quote_time_raw": raw_time,
            "fetched_at": fetched_at,
            "name":         vals[1],
            "price":        float(vals[3]) if vals[3] else 0,
            "last_close":   float(vals[4]) if vals[4] else 0,
            "open":         float(vals[5]) if vals[5] else 0,
            "change_amt":   float(vals[31]) if vals[31] else 0,
            "change_pct":   float(vals[32]) if vals[32] else 0,
            "high":         float(vals[33]) if vals[33] else 0,
            "low":          float(vals[34]) if vals[34] else 0,
            "amount_wan":   float(vals[37]) if vals[37] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "pe_ttm":       float(vals[39]) if vals[39] else 0,
            "amplitude_pct":float(vals[43]) if vals[43] else 0,
            # ⚠️ 44=流通市值、45=总市值（曾标反）。总股本≠流通股本时差数倍，见上方踩坑提醒二
            "float_mcap_yi":float(vals[44]) if vals[44] else 0,
            "mcap_yi":      float(vals[45]) if vals[45] else 0,
            "pb":           float(vals[46]) if vals[46] else 0,
            "limit_up":     float(vals[47]) if vals[47] else 0,
            "limit_down":   float(vals[48]) if vals[48] else 0,
            "vol_ratio":    float(vals[49]) if vals[49] else 0,
            "pe_static":    float(vals[52]) if vals[52] else 0,
        }
        # 僵尸报价检测：腾讯对「已迁移的北交所老码 / 长期停牌股」照样返回 HTTP 200 +
        # 一份定格在最后交易日的报价（成交量 0、最新价==昨收），不报任何错。
        # 直接拿去算估值会得出完全错误的结论（实测 bj832982 报 112.60，真实新码 920982 为 131.74）。
        q = result[code]
        q["is_stale"] = (q["amount_wan"] == 0 and q["price"] == q["last_close"] and q["price"] > 0)
        if q["is_stale"] and key[2:4] in ("43", "83", "87"):
            q["stale_reason"] = "北交所老号段，多数已迁至 920xxx，请按名称反查现行代码"
        elif q["is_stale"]:
            q["stale_reason"] = "成交量为 0（停牌 / 未开盘 / 废码），报价非当日真实成交"
    return result


def _json_value(value):
    """JSON 不支持非有限数值；显式标记，避免混同缺失值。"""
    import math

    if isinstance(value, float) and not math.isfinite(value):
        return {"$float": "NaN" if math.isnan(value) else
                ("Infinity" if value > 0 else "-Infinity")}
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="tencent-quote-", suffix=".json", delete=False) as stream:
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
    import json
    import sys
    from contextlib import redirect_stdout
    from pathlib import Path

    # 本脚本不依赖 _runtime，需自行处理英文 Windows 管道（cp1252）无法输出中文的问题。
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if encoding and hasattr(stream, "reconfigure"):
            try:
                "中文".encode(encoding)
            except (UnicodeEncodeError, LookupError):
                stream.reconfigure(encoding="utf-8", errors=stream.errors)

    parser = argparse.ArgumentParser(
        description="批量查询腾讯实时行情，输出 JSON；仅使用 Python 标准库。",
        epilog="示例：python3 tencent_quote.py sh000001 sz000001 510300\n"
               "裸 000001 为平安银行；上证指数须使用 sh000001。\n"
               "成交额单位万元，市值单位亿元；is_stale 表示疑似陈旧报价。\n"
               "非有限数值编码为 {\"$float\": \"NaN/Infinity/-Infinity\"}。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("codes", nargs="+", help="证券代码字符串，保留前导零及显式 sh/sz/bj 前缀")
    parser.add_argument("--output", type=Path, help="完整 JSON 保存到新文件；路径相对当前目录，不覆盖已有文件")
    args = parser.parse_args(argv)
    if len(args.codes) > 20 and args.output is None:
        parser.error("超过 20 个代码请指定 --output，避免完整结果占满上下文")
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")

    try:
        # 原函数保持不变，CLI 层隔离日志；一次调用批量请求全部代码。
        with redirect_stdout(sys.stderr):
            quotes = tencent_quote(args.codes)
        payload = _json_value(quotes)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        if args.output is None:
            print(encoded)
        else:
            _save_payload(encoded, args.output)
            print(json.dumps({
                "output": str(args.output.resolve()),
                "requested_count": len(args.codes),
                "returned_count": len(quotes),
                "preview": dict(list(payload.items())[:3]),
                "preview_only": True,
            }, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
