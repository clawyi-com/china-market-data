# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""两所官方 ETF 份额：沪历史归档，深当前快照。"""
import _runtime  # noqa: F401  须在第三方库之前导入
import pandas as pd
from _market_common import _v39_http, _v39_json, _v39_date, _v39_src_date, _v39_count, _v39_req_num, _v39_contract, _v39_frame
import re
import time

SSE_ETF_SHARES_URL = "https://query.sse.com.cn/commonQuery.do"
SZSE_FUND_LIST_URL = "https://fund.szse.cn/api/report/ShowReport/data"


def _etf_shares_sse(day):
    params = {"sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L", "STAT_DATE": day,
              "isPagination": "true", "pageHelp.pageSize": 10000, "pageHelp.pageNo": 1,
              "pageHelp.beginPage": 1, "pageHelp.cacheSize": 1, "pageHelp.endPage": 1}
    response = _v39_http(SSE_ETF_SHARES_URL, params=params,
                         headers={"Referer": "https://www.sse.com.cn/"})
    payload = _v39_json(response)
    result = payload.get("result") if isinstance(payload, dict) else None
    page_help = payload.get("pageHelp") if isinstance(payload, dict) else None
    if (not isinstance(result, list) or not all(isinstance(r, dict) for r in result)
            or not isinstance(page_help, dict)):
        raise RuntimeError("上交所 ETF 规模接口返回结构改变")
    # 服务端把每页压到 2000 条（请求 10000 也回 pageSize=2000，2026-09-20 实测当日共 912 条）；
    # 条数必须等于它自报的 total，超过一页或只回了一部分都不能当完整快照
    total = _v39_count(page_help.get("total"), "上交所 ETF 规模 pageHelp.total")
    if len(result) != total:
        raise RuntimeError(f"上交所 ETF 规模返回 {len(result)} 条，与自报总数 {total} 不符，结果不完整")
    if not result:
        raise ValueError(f"上交所 {day} 没有 ETF 份额数据：非交易日或尚未发布")
    rows = []
    for rec in result:
        if rec.get("STAT_DATE") != day:
            raise RuntimeError("上交所返回了其他日期的数据")
        try:
            rows.append({"date": day, "exchange": "SH", "code": rec["SEC_CODE"],
                         "name": rec["SEC_NAME"], "etf_type": rec.get("ETF_TYPE"),
                         "shares_10k": _v39_req_num(rec["TOT_VOL"], "上交所 ETF 份额")})
        except KeyError as exc:
            raise RuntimeError(f"上交所 ETF 规模字段缺失: {exc!r}") from exc
    return rows, response.url


def _etf_shares_szse(day):
    rows, page, first, url = [], 1, None, SZSE_FUND_LIST_URL
    while first is None or page <= first[1]:
        response = _v39_http(SZSE_FUND_LIST_URL,
                             params={"SHOWTYPE": "JSON", "CATALOGID": "1000_lf", "TABKEY": "tab1",
                                     "selectJjlb": "ETF", "PAGENO": page},
                             headers={"Referer": "https://fund.szse.cn/"})
        payload = _v39_json(response)
        table = payload[0] if isinstance(payload, list) and payload else None
        meta = table.get("metadata") if isinstance(table, dict) else None
        data = table.get("data") if isinstance(table, dict) else None
        if not isinstance(meta, dict) or not isinstance(data, list):
            raise RuntimeError(f"深交所基金列表第 {page} 页的返回结构变了（缺 metadata / data）")
        # subname 是这份快照的数据日期（实测 '2026-09-18'）。缺失或写法变了先按来源坏掉报错，
        # 否则下面会说成「快照日期是 None，不是 2026-09-18」，把结构损坏伪装成用户要了历史日期。
        snap = (_v39_src_date(meta.get("subname")),
                _v39_count(meta.get("pagecount"), "深交所基金列表 pagecount"),
                _v39_count(meta.get("recordcount"), "深交所基金列表 recordcount"))
        if snap[1] < 1:
            raise RuntimeError(f"深交所基金列表 pagecount={snap[1]}，分页信息异常")
        if first is None:
            # 深交所只提供「当前」规模快照，metadata.subname 是它的数据日期。
            if snap[0] != day:
                raise ValueError(f"深交所当前规模快照日期是 {snap[0]}，不是 {day}；"
                                 "深市只能取最新一天，历史份额请自行按日留存")
            first = snap
        elif snap != first:     # 翻页途中快照换了日期或总数：拼出来的是两份快照的混合
            raise RuntimeError(f"深交所 ETF 列表翻页时快照从 {first} 变成 {snap}，请重试")
        if not data:        # 预期内的页是空的：返回前几页会被当成完整快照
            raise RuntimeError(f"深交所 ETF 列表第 {page}/{first[1]} 页是空的，结果不完整")
        for rec in data:
            try:
                code = re.search(r"<u>(\d{6})</u>", rec["sys_key"])
                name = re.search(r"<u>(.*?)</u>", rec["jjjcurl"])
                shares = re.search(r">([\d,\.]+)</a>", rec["dqgm"])
            except (KeyError, TypeError) as exc:
                raise RuntimeError(f"深交所基金列表字段缺失: {exc!r}") from exc
            if not (code and name and shares):
                raise RuntimeError("深交所基金列表字段格式改变")
            rows.append({"date": day, "exchange": "SZ", "code": code.group(1),
                         "name": name.group(1), "fund_category": rec.get("tzlb"),
                         "shares_10k": _v39_req_num(shares.group(1), "深交所 ETF 份额"),
                         "manager": rec.get("glrmc"), "listing_date": rec.get("ssrq")})
        url = response.url
        page += 1
        time.sleep(0.3)
    if len(rows) != first[2]:
        raise RuntimeError(f"深交所 ETF 列表取到 {len(rows)} 条，与它自报的总数 {first[2]} 不符")
    return rows, url


@_v39_contract
def etf_shares(date, exchange="SH"):
    """ETF 份额（万份）— 上交所按日归档，深交所只有当前快照。

    date: 'YYYY-MM-DD'。上交所可查历史日期（实测 2023-01-03 仍有 446 只）；
    深交所只返回最新一天，date 与快照日期不符直接抛错（深交所注明 T 日晚为预估、T+1 早为确认值）。
    exchange: 'SH' 或 'SZ'。两所单位都是万份。上交所的 etf_type 是单市/跨市/跨境等，
    深交所给的是 fund_category（股票基金/债券基金…），两者口径不同，没有混成一列。
    """
    day = _v39_date(date)
    exchange = str(exchange).upper()
    if exchange == "SH":
        rows, url = _etf_shares_sse(day)
    elif exchange == "SZ":
        rows, url = _etf_shares_szse(day)
    else:
        raise ValueError("exchange 只能是 'SH' 或 'SZ'")
    frame = _v39_frame(rows, exchange.lower() + "se", url)
    if frame.duplicated(["code"]).any():
        raise RuntimeError("ETF 份额数据代码重复，不能当成完整快照")
    return frame


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="etf-shares-", suffix=".json", delete=False) as stream:
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

    parser = argparse.ArgumentParser(description="ETF 份额：完整表格保存，终端仅三行预览。")
    parser.add_argument("date", help="YYYY-MM-DD 查询日期")
    parser.add_argument("--exchange", type=str.upper, choices=("SH", "SZ"), default="SH")
    parser.add_argument("--output", type=Path, help="完整 JSON 新文件，不覆盖已有路径")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        with redirect_stdout(sys.stderr):
            frame = etf_shares(args.date, args.exchange)
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
