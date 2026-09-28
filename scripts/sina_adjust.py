# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""新浪复权因子及复权计算；保留原生 list / DataFrame API。"""
import _runtime  # noqa: F401  须在第三方库之前导入
from _ticker import get_prefix, norm_ticker

import json
import re

import requests


def sina_adjust_factor(code: str, kind: str = "qfq") -> list:
    """新浪复权因子序列 — kind='qfq'(前复权) | 'hfq'(后复权)，按日期倒序（最新在前）"""
    if kind not in ("qfq", "hfq"):
        raise ValueError(f"kind 只能是 'qfq' 或 'hfq'，收到 {kind!r}")
    # 数字位用 norm_ticker() 剥掉前后缀（否则 "sz000016" 会拼成 "szsz000016" ——
    # zfill(6) 对 8 字符输入不做任何事）。
    raw = str(code).strip()
    digits = norm_ticker(raw)
    # 市场：**显式写法优先**——前缀或 `.SH` 后缀直接采信（V3.7.1 起 get_prefix() 也认后缀，
    # 本地显式匹配保留，语义不变）。都没写显式市场时，才用 get_prefix() 按号段推断
    # （它已处理 92 必须先于 9x）。
    m = re.match(r"^(sh|sz|bj)", raw, re.I) or re.search(r"\.(sh|sz|bj|xshg|xshe)$", raw, re.I)
    prefix = {"xshg": "sh", "xshe": "sz"}.get(m.group(1).lower(), m.group(1).lower()) if m else get_prefix(digits)
    symbol = f"{prefix}{digits}"
    url = f"https://finance.sina.com.cn/realstock/company/{symbol}/{kind}.js"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0",
                                   "Referer": "https://finance.sina.com.cn/"}, timeout=10)
    r.raise_for_status()
    # 🔴 响应形如 `var sh600519qfq={...}` 且**末尾挂着 /* base64 */ 注释块**，
    #    不能用 $ 锚定正则。从第一个 { 起用 raw_decode，让解析器自己在 JSON 结束处停下。
    text = r.text
    brace = text.find("{")
    if brace < 0:
        raise RuntimeError(f"新浪复权因子响应无 JSON（{symbol}/{kind}）: {text[:120]}")
    try:
        data, _ = json.JSONDecoder().raw_decode(text[brace:])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"新浪复权因子 JSON 解析失败（{symbol}/{kind}）: {e}") from e
    return [{"date": it["d"], "factor": float(it["f"])} for it in data.get("data", [])]


def apply_adjust(bars, factors: list, kind: str = "qfq",
                 price_keys=("open", "high", "low", "close")):
    """把复权因子套到不复权 K 线上。

    `bars` 接受两种形态：
      - **§1.7 `tdx_client().bars()` 的 DataFrame**（日期列名是 `datetime`）或 §1.2 `tencent_kline(adjust='')` 的 DataFrame（`date` 列）→ 返回 DataFrame
      - list[dict]（需含 `date` 键）→ 返回 list[dict]

    🔴 **qfq 与 hfq 的运算方向相反，必须传对 kind**：
      - `qfq`（前复权）因子是**除数**：`前复权价 = 不复权价 ÷ factor`
      - `hfq`（后复权）因子是**乘数**：`后复权价 = 不复权价 × factor`
    传错方向不会报错，只会把历史价格放大/缩小几倍（见下方实测对照表）。

    因子表是「生效日 → 因子」的阶梯，每根 K 线取**不晚于它**的最近一个因子。
    """
    if kind not in ("qfq", "hfq"):
        raise ValueError(f"kind 只能是 'qfq' 或 'hfq'，收到 {kind!r}")
    # 🔴 因子为空时绝不能「原样返回」—— 那会把不复权价当成复权价交出去，
    #    调用方拿到的数字看着正常却是错的（新浪对不支持的标的就返回空 data）。
    if not factors:
        raise ValueError(
            "复权因子列表为空，无法复权。请先确认 sina_adjust_factor() 是否取到数据"
            "（新浪对不支持的标的会返回空 data），不要用未复权价继续计算。"
        )

    is_df = hasattr(bars, "columns") and hasattr(bars, "to_dict")
    if is_df:
        # mootdx bars() 的日期列叫 datetime，且可能带时分秒，统一截成 YYYY-MM-DD
        date_col = next((c for c in ("date", "datetime") if c in bars.columns), None)
        if date_col is None:
            raise ValueError(f"DataFrame 需含 date 或 datetime 列，实际列={list(bars.columns)}")
        rows = bars.to_dict("records")
        for r in rows:
            r["date"] = str(r[date_col])[:10]
    else:
        rows = [dict(b) for b in bars]
        for r in rows:
            if "date" not in r:
                raise ValueError(f"每根 K 线需含 'date' 键，实际键={sorted(r)}")
            r["date"] = str(r["date"])[:10]

    fac = sorted(factors, key=lambda x: x["date"])
    out, i, cur = [], 0, None
    for bar in sorted(rows, key=lambda b: b["date"]):
        while i < len(fac) and fac[i]["date"] <= bar["date"]:
            cur = fac[i]["factor"]
            i += 1
        # 🔴 早于最早因子日的 K 线不能原样放行 —— 那会让一份结果里混着「已复权」和
        #    「未复权」两种价格且无从分辨。新浪的因子表通常带 1900-01-01 哨兵
        #    （实测 600519/000001/300750/688981/000004/601398 六只均是），
        #    真出现未覆盖行，说明因子表异常，必须显式失败。
        if cur is None:
            raise RuntimeError(
                f"K 线日期 {bar['date']} 早于因子序列最早日 {fac[0]['date']}，"
                "无法复权；不返回未复权价以免与已复权行混淆。"
            )
        if cur == 0:
            raise RuntimeError(f"复权因子为 0（{bar['date']}），无法换算")
        nb = dict(bar)
        for k in price_keys:
            if k in nb and nb[k] is not None:
                v = float(nb[k])
                nb[k] = round(v / cur if kind == "qfq" else v * cur, 4)
        nb["adj_factor"] = cur
        out.append(nb)
    if is_df:
        import pandas as pd
        res = pd.DataFrame(out)
        # mootdx 的 bars() 带 DatetimeIndex，重建 DataFrame 会退化成 RangeIndex，
        # 下游按时间切片 / resample / 时间对齐 join 都会失效。按排序后的顺序还原索引。
        if getattr(bars, "index", None) is not None and not isinstance(
            bars.index, pd.RangeIndex
        ):
            order = sorted(range(len(bars)), key=lambda n: str(bars.iloc[n][date_col])[:10])
            res.index = bars.index[order]
            res.index.name = bars.index.name
        return res
    return out


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
    # numpy 标量转为等值 Python 标量；新浪 JSON 字段没有任意对象列。
    if hasattr(value, "item"):
        return _json_safe(value.item())
    raise TypeError(f"无法无歧义地序列化 {type(value).__name__}")


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="sina-adjust-", suffix=".json", delete=False) as stream:
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


def _read_records(path):
    """读取 JSON 记录列表；还原本 CLI 的保留 $float 单键标记。"""
    def decode(value):
        if set(value) == {"$float"}:
            tags = {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": -float("inf")}
            tag = value["$float"]
            if not isinstance(tag, str) or tag not in tags:
                raise ValueError("无效 $float 标记")
            return tags[tag]
        return value
    with path.open(encoding="utf-8") as stream:
        records = json.load(stream, object_hook=decode)
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise ValueError("输入必须是 JSON 对象列表；DataFrame 请使用 Python API")
    return records


def main(argv=None):
    import argparse
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description="新浪复权：完整 JSON 落盘，stdout 仅给三条预览。")
    commands = parser.add_subparsers(dest="command", required=True)
    factors = commands.add_parser("factors", help="获取 qfq 或 hfq 因子")
    factors.add_argument("code")
    apply = commands.add_parser("apply", help="对本地不复权 JSON 对象列表应用因子")
    apply.add_argument("--bars", type=Path, required=True)
    apply.add_argument("--factors", type=Path, required=True)
    apply.add_argument("--price-key", action="append", help="替换默认 OHLC 字段，可重复指定")
    for subparser in (factors, apply):
        subparser.add_argument("--kind", choices=("qfq", "hfq"), default="qfq",
                               help="必须与因子种类一致：qfq 除法，hfq 乘法")
        subparser.add_argument("--output", type=Path, help="完整 JSON 新文件；不覆盖已有路径")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        if args.command == "factors":
            result = sina_adjust_factor(args.code, kind=args.kind)
        else:
            keys = args.price_key if args.price_key is not None else ("open", "high", "low", "close")
            result = apply_adjust(_read_records(args.bars), _read_records(args.factors),
                                  kind=args.kind, price_keys=keys)
        payload = _json_safe(result)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        path = _save_payload(encoded, args.output)
        print(json.dumps({"output": str(path), "row_count": len(result), "kind": args.kind,
                          "preview_only": True, "preview": payload[:3]},
                         ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
