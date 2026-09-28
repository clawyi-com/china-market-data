# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""全市场风险警示快照，保留主源与降级覆盖说明。"""
import _runtime  # noqa: F401  须在第三方库之前导入
import re
import pandas as pd
from _eastmoney import em_get
from _market_common import _v39_json, _v39_count, _v39_rows, _v39_num, _v39_frame, _v39_contract

# 主源不需要 baostock；实际降级时才加载 SDK，复用原会话与结果转换。
def bs_session():
    from baostock_data import bs_session as session
    return session()


def _rs_to_df(rs):
    from baostock_data import _rs_to_df as convert
    return convert(rs)


import requests

EM_CLIST_HOSTS = ["https://push2.eastmoney.com", "https://push2delay.eastmoney.com"]


def _em_clist_all(fs, fields, page_size=100):
    """东财 clist 全量翻页。主域网络失败时换 push2delay（同一接口，行情延迟约 15 分钟）。
    网络层全部失败抛 requests.ConnectionError；服务端返回异常内容（含非 JSON 的错误页）抛 RuntimeError，
    不换域重试，也不会让 st_stock_list 退到只有沪深的备胎。"""
    errors = []
    for host in EM_CLIST_HOSTS:
        url = host + "/api/qt/clist/get"
        rows, page, total = [], 1, None
        try:
            while True:
                response = em_get(url, params={"pn": page, "pz": page_size, "po": 1, "np": 1,
                                               "fltt": 2, "invt": 2, "fid": "f12",
                                               "fs": fs, "fields": fields}, timeout=15)
                response.raise_for_status()
                payload = _v39_json(response)
                data = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(data, dict) or payload.get("rc") != 0 or not data:
                    raise RuntimeError(f"东财 clist 返回异常或无数据（fs={fs}）: {str(payload)[:100]}")
                page_total = _v39_count(data.get("total"), f"东财 clist total（fs={fs}）")
                diff = _v39_rows(data.get("diff"), f"东财 clist 的 diff（fs={fs}）")
                if total is None:
                    total = page_total
                elif page_total != total:   # 翻页途中名单变了：拼出来的是两份名单的混合
                    raise RuntimeError(f"东财 clist 翻页时 total 从 {total} 变成 {page_total}，请重试")
                rows.extend(diff)
                if not diff or len(rows) >= total:
                    break
                page += 1
        except requests.RequestException as exc:
            errors.append(f"{host}: {type(exc).__name__}")
            continue
        if len(rows) != total:
            raise RuntimeError(f"东财 clist 翻页后 {len(rows)} 条，与 total={total} 不符")
        return rows, url
    raise requests.ConnectionError("东财 push2 / push2delay 均不可达: " + "; ".join(errors))


@_v39_contract
def st_stock_list():
    """全市场 ST / *ST 名单（风险警示）— 当日快照。

    沪深：东财「风险警示板」过滤（含 B 股）；北交所：东财不纳入该过滤，改为拉北交所全表按名称筛。
    东财两个域名都连不上时退到 baostock 证券列表按名称筛（**只有沪深、没有价格**，attrs 里注明）。
    price / pct_change 在走 push2delay 时约有 15 分钟延迟（source_url 可看出走的是哪个域）。
    """
    fields = "f12,f13,f14,f2,f3"
    try:
        shsz, url = _em_clist_all("m:0+f:4,m:1+f:4", fields)
        bj, bj_url = _em_clist_all("m:0+t:81+s:2048", fields)
    except requests.ConnectionError as exc:
        return _st_list_baostock(str(exc))
    # 两边原始集合都不该为空：北交所全表空了还标「沪深京」，会把缺失说成「北交所没有 ST」
    if not shsz or not bj:
        raise RuntimeError(f"东财风险警示板 {len(shsz)} 条、北交所全表 {len(bj)} 条，"
                           "有一边为空，不能当成沪深京完整名单")
    if bj_url != url:
        url = url + " | " + bj_url      # 两次调用可能落在不同域名（push2 / push2delay）
    rows = []
    for rec, is_bj in [(r, False) for r in shsz] + [(r, True) for r in bj]:
        # 代码 / 市场号 / 名称都是身份字段：f13 缺失或变样按「深市」处理会给出错误市场，
        # 名称为空则北交所那半边会被静默筛掉，结果却仍标「沪深京」。
        # 2026-09-20 实测两张表共 562 行：f12 全是 6 位、f13 只有 int 0/1、f14 无空值。
        code, market_id, name = rec["f12"], rec["f13"], str(rec["f14"]).strip()
        if (not re.fullmatch(r"[0-9]{6}", str(code)) or isinstance(market_id, bool)
                or market_id not in (0, 1)):
            raise RuntimeError(f"东财 clist 返回了认不出的代码 / 市场号: f12={code!r} f13={market_id!r}")
        if not name:
            raise RuntimeError(f"东财 clist 里 {code} 没有名称，ST 判定要靠名称，不能当成完整名单")
        if is_bj and "ST" not in name.upper():
            continue
        rows.append({"code": code,
                     "market": "bj" if is_bj else ("sh" if market_id == 1 else "sz"),
                     "name": name, "st_type": "*ST" if name.startswith("*") else "ST",
                     "price": _v39_num(rec.get("f2")), "pct_change": _v39_num(rec.get("f3"))})
    frame = _v39_frame(rows, "eastmoney", url)
    if frame.empty or frame.duplicated(["code"]).any():
        raise RuntimeError("ST 名单为空或代码重复，不能当成完整快照")
    frame.attrs["coverage"] = "沪深京"
    return frame


def _st_list_baostock(reason):
    import baostock as bs
    # 用名称模糊查询（约 300 条、2 秒）；不带参数的全量查询实测会在服务端卡住
    with bs_session():
        basic = _rs_to_df(bs.query_stock_basic(code_name="ST"))
    # type 1 = 股票，status 1 = 上市
    picked = basic[(basic["type"] == "1") & (basic["status"] == "1")
                   & basic["code_name"].str.upper().str.contains("ST")]
    rows = [{"code": c.split(".")[1], "market": c.split(".")[0], "name": n,
             "st_type": "*ST" if n.startswith("*") else "ST", "price": None, "pct_change": None}
            for c, n in zip(picked["code"], picked["code_name"])]
    frame = _v39_frame(rows, "baostock", "baostock.query_stock_basic")
    if frame.empty:
        raise RuntimeError("baostock 证券列表里没有筛出 ST，结果不可信")
    frame.attrs["coverage"] = "沪深（东财不可达，baostock 不含北交所）"
    frame.attrs["fallback_reason"] = reason
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
                                         prefix="st-list-", suffix=".json", delete=False) as stream:
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

    parser = argparse.ArgumentParser(description="ST / *ST 当日快照，完整数据及覆盖信息保存为 JSON")
    parser.add_argument('--output', type=Path, help='完整 JSON 新文件，不覆盖')
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error('输出文件已存在，请指定新路径')
    try:
        with redirect_stdout(sys.stderr):
            frame = st_stock_list()
        payload = _frame_payload(frame)
        preview = _frame_payload(frame.head(3))
        path = _save_payload(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2), args.output)
        print(json.dumps({'output': str(path), 'row_count': len(frame), 'preview_only': True,
                          'preview': preview}, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
