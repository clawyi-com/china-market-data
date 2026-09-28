# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""新浪ETF期权合约、T型报价与希腊字母。"""
import _runtime  # noqa: F401  须在第三方库之前导入
from _eastmoney import UA
import requests

SINA_OPT_HDR = {"Referer": "https://stock.finance.sina.com.cn/", "User-Agent": UA}

def _opt_f(x):
    try: return float(x)
    except Exception: return x

def _sina_opt_list(param: str) -> list:
    """新浪 hq.sinajs.cn 取值（GBK，逗号分隔，去 var hq_str_XXX="..." 壳）。"""
    r = requests.get(f"https://hq.sinajs.cn/list={param}", headers=SINA_OPT_HDR, timeout=10)
    r.encoding = "gbk"
    t = r.text
    return t.split('"')[1].split(",") if '"' in t else []

def sina_option_codes(underlying: str = "510050", call: bool = True) -> dict:
    """ETF期权合约清单。underlying: 510050/510300/588000/510500。call=True认购/False认沽。
    返回 {月份YYMM: [合约代码,...]}，第一个 key 即近月。"""
    cate = {"510050": "50ETF", "510300": "300ETF",
            "588000": "科创50ETF", "510500": "500ETF"}.get(underlying, "50ETF")
    url = ("https://stock.finance.sina.com.cn/futures/api/openapi.php/"
           f"StockOptionService.getStockName?exchange=null&cate={cate}")
    try:
        months = requests.get(url, headers=SINA_OPT_HDR, timeout=10).json()["result"]["data"]["contractMonth"]
    except Exception as e:
        print(f"[WARN] 期权月份获取失败: {e}")
        return {}
    months = [m.replace("-", "")[2:] for m in months[1:]]  # 丢首个，转 YYMM
    flag = "OP_UP_" if call else "OP_DOWN_"
    out = {}
    for m in months:
        codes = [c.replace("CON_OP_", "") for c in _sina_opt_list(f"{flag}{underlying}{m}")
                 if c.startswith("CON_OP_")]
        if codes:
            out[m] = codes
    return out

def sina_option_tquote(code: str) -> dict:
    """期权T型报价。返回 bid_vol/bid/last/ask/ask_vol/open_interest(持仓量)/pct/
    strike(行权价)/prev_close/open/limit_up/limit_down/name/amplitude/high/low/volume/amount。"""
    v = _sina_opt_list(f"CON_OP_{code}")
    if len(v) < 43:
        return {}
    return {"bid_vol": _opt_f(v[0]), "bid": _opt_f(v[1]), "last": _opt_f(v[2]),
        "ask": _opt_f(v[3]), "ask_vol": _opt_f(v[4]), "open_interest": _opt_f(v[5]),
        "pct": _opt_f(v[6]), "strike": _opt_f(v[7]), "prev_close": _opt_f(v[8]),
        "open": _opt_f(v[9]), "limit_up": _opt_f(v[10]), "limit_down": _opt_f(v[11]),
        "name": v[37], "amplitude": _opt_f(v[38]), "high": _opt_f(v[39]),
        "low": _opt_f(v[40]), "volume": _opt_f(v[41]), "amount": _opt_f(v[42])}

def sina_option_greeks(code: str) -> dict:
    """期权希腊字母 + 隐含波动率。返回 name/volume/delta/gamma/theta/vega/
    iv(隐含波动率,小数)/high/low/trade_code/strike/last/theory(理论价值)。"""
    raw = _sina_opt_list(f"CON_SO_{code}")
    if len(raw) < 16:
        return {}
    v = [raw[0]] + raw[4:]  # ⚠️ raw[1:4] 是 3 个空串，必须跳过否则字段错位
    return {"name": v[0], "volume": _opt_f(v[1]), "delta": _opt_f(v[2]),
        "gamma": _opt_f(v[3]), "theta": _opt_f(v[4]), "vega": _opt_f(v[5]),
        "iv": _opt_f(v[6]), "high": _opt_f(v[7]), "low": _opt_f(v[8]),
        "trade_code": v[9], "strike": _opt_f(v[10]), "last": _opt_f(v[11]), "theory": _opt_f(v[12])}


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
    # numpy 标量转为等值 Python 标量；新闻 JSON 字段没有任意对象列。
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
                                         prefix="sina-options-", suffix=".json", delete=False) as stream:
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
    import io
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description='新浪ETF期权：完整JSON保存')
    commands = parser.add_subparsers(dest='command', required=True)
    codes = commands.add_parser('codes')
    codes.add_argument('--underlying', default='510050')
    codes.add_argument('--put', action='store_true', help='认沽；默认认购')
    codes.add_argument('--output', type=Path)
    for name in ('quote', 'greeks'):
        command = commands.add_parser(name)
        command.add_argument('code')
        command.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error('输出文件已存在，请指定新路径')
    diagnostics = io.StringIO()
    try:
        with redirect_stdout(diagnostics):
            if args.command == 'codes':
                result = sina_option_codes(args.underlying, not args.put)
            elif args.command == 'quote':
                result = sina_option_tquote(args.code)
            else:
                result = sina_option_greeks(args.code)
        if '[WARN]' in diagnostics.getvalue():
            raise RuntimeError('期权月份请求失败，未保存结果')
        payload = _json_safe(result)
        preview = payload
        if args.command == 'codes':
            preview = {month: values[:3] for month, values in list(payload.items())[:3]}
        path = _save_payload(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2), args.output)
        summary = {'output': str(path), 'preview_only': True, 'preview': preview}
        if args.command == 'codes':
            summary.update(month_count=len(payload), contract_count=sum(len(v) for v in payload.values()))
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    finally:
        if diagnostics.getvalue():
            print(diagnostics.getvalue(), end='', file=sys.stderr)


if __name__ == '__main__':
    raise SystemExit(main())
