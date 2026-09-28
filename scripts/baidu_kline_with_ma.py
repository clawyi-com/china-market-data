# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""百度股市通日 K 线与均线：保持正常 keys/rows，明确拒绝错误及空数据。"""
try:
    import _runtime  # noqa: F401  须在第三方库之前导入
except ModuleNotFoundError:  # 单文件复制安装时没有 helper
    pass
import requests


def _baidu_payload(response):
    """区分 HTTP/业务失败、结构异常和显式空数据，不把缺失字段默认为空行情。"""
    try:
        payload = response.json()
    except ValueError as exc:
        if not 200 <= response.status_code < 300:
            raise requests.HTTPError(f"百度 K 线 HTTP {response.status_code}，返回非 JSON 错误页",
                                     response=response) from exc
        raise RuntimeError("百度 K 线返回非 JSON，数据格式可能已变") from exc
    # 仅提取有限的错误字段，保留风控原因，不把整份行情写入异常信息。
    details = []
    for label, node in (("response", payload),
                        ("Result", payload.get("Result") if isinstance(payload, dict) else None)):
        if isinstance(node, dict):
            for key in ("ResultCode", "code", "error", "msg", "message", "isCaptchaEnabled"):
                if key in node:
                    details.append(f"{label}.{key}={str(node[key])[:200]}")
    detail = "; ".join(details)
    if not 200 <= response.status_code < 300:
        raise requests.HTTPError(f"百度 K 线 HTTP {response.status_code}: {detail}", response=response)
    if not isinstance(payload, dict):
        raise RuntimeError("百度 K 线顶层不是对象，数据格式可能已变")
    result = payload.get("Result")
    for node in (payload, result):
        if not isinstance(node, dict):
            continue
        for key, successes in (("ResultCode", (0, "0")), ("code", (0, "0", 200, "200"))):
            if key in node and (isinstance(node[key], bool) or node[key] not in successes):
                raise RuntimeError(f"百度 K 线业务错误: {detail}")
        if node.get("error") or node.get("isCaptchaEnabled") in (True, "true", "True", "1"):
            raise RuntimeError(f"百度 K 线业务错误/验证码要求: {detail}")
    if not isinstance(result, dict) or not isinstance(result.get("newMarketData"), dict):
        raise RuntimeError("百度 K 线缺少有效 Result.newMarketData，不能视为空行情")
    market = result["newMarketData"]
    keys, data = market.get("keys"), market.get("marketData")
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and k.strip() for k in keys):
        raise RuntimeError("百度 K 线 keys 必须为非空字段名列表")
    if not isinstance(data, str):
        raise RuntimeError("百度 K 线缺少字符串 marketData，数据格式可能已变")
    rows = data.split(";")
    if not any(row.strip() for row in rows):
        raise ValueError("百度 K 线没有非空行情记录；请核查证券代码、查询起点或数据源状态")
    return {"keys": keys, "rows": rows}


def baidu_kline_with_ma(code: str, start_time: str = "") -> dict:
    """百度股市通K线 — 独有能力: 返回时自带 ma5/ma10/ma20 均价"""
    url = "https://finance.pae.baidu.com/selfselect/getstockquotation"
    params = {
        "all": "1", "isIndex": "false", "isBk": "false", "isBlock": "false",
        "isFutures": "false", "isStock": "true", "newFormat": "1",
        "group": "quotation_kline_ab", "finClientType": "pc",
        "code": code, "start_time": start_time, "ktype": "1",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.finance-web.v1+json",
        "Origin": "https://gushitong.baidu.com",
        "Referer": "https://gushitong.baidu.com/",
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    return _baidu_payload(r)

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
    # numpy 标量转为等值 Python 标量；百度 JSON 字段没有任意对象列。
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
                                         prefix="baidu-kline-", suffix=".json", delete=False) as stream:
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

    parser = argparse.ArgumentParser(description="百度日 K 线与均线：原始 keys/rows 完整落盘，stdout 仅给预览。")
    parser.add_argument("code", help="代码字符串，原样传入接口，例如 600519")
    parser.add_argument("--start-time", default="", help="原样传递 start_time；省略为空，不转换日期或自动分页")
    parser.add_argument("--output", type=Path, help="完整 JSON 的新文件路径；父目录须存在，不覆盖已有文件")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        with redirect_stdout(sys.stderr):
            result = baidu_kline_with_ma(args.code, start_time=args.start_time)
        payload = _json_safe(result)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        path = _save_payload(encoded, args.output)
        print(json.dumps({"output": str(path), "row_count": len(result["rows"]),
                          "preview_only": True, "preview": {"keys": payload["keys"], "rows": payload["rows"][:3]}},
                         ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
