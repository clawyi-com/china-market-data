# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""新浪研报列表；保留最小间隔、空页重试和完整行解析规则。"""
import _runtime  # noqa: F401  须在第三方库之前导入
from _ticker import get_prefix, norm_ticker
from _market_common import _v39_http, _v39_src_date, _v39_contract, _v39_frame

import re
import time
import html as _html

SINA_REPORT_URL = "https://vip.stock.finance.sina.com.cn/q/go.php/vReport_List/kind/{kind}/index.phtml"
_SINA_REPORT_ROW = re.compile(
    r"<tr>\s*<td>\d+</td>\s*<td class=\"tal f14\">\s*<a[^>]*?title=\"([^\"]*)\"[^>]*?"
    r"href=\"([^\"]*?/rptid/(\d+)/[^\"]*)\"[^>]*>.*?</a>\s*</td>\s*"
    r"<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>", re.S)


# 实测（2026-09-20）：个股研报搜索两次请求间隔 1 秒时，第二次起返回「没有找到相关内容..」
# 空页（HTTP 200，与真的没有研报长得一样）；间隔 ≥5 秒恢复正常。因此强制最小间隔，
# 并对空页等待后重试一次，仍为空才当作「该股确实没有」。
SINA_REPORT_MIN_INTERVAL = 6.0
_sina_report_last = [0.0]


def _sina_report_page(url, params):
    for attempt in range(2):
        wait = SINA_REPORT_MIN_INTERVAL - (time.time() - _sina_report_last[0])
        if wait > 0:
            time.sleep(wait)
        try:
            response = _v39_http(url, params=params,
                                 headers={"Referer": "https://finance.sina.com.cn/"})
        finally:
            _sina_report_last[0] = time.time()
        text = response.content.decode("gbk", "replace")
        if "没有找到相关内容" not in text:
            return response, text
    return response, text


def _sina_text(fragment):
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


@_v39_contract
def sina_research_reports(code=None, page=1):
    """新浪研报列表 — 研报标题/类型/日期/机构/研究员（#53 的第二来源）。

    code=None 返回全市场最新；给代码则只看该股。每页约 40 条，page 从 1 开始。
    只给列表与详情页链接，不含评级与目标价（需要这些用 §2.1 东财）。
    新浪对连续请求会返回假的「没有找到」空页，本函数内置 6 秒最小间隔，批量翻页会比较慢。
    """
    if int(page) < 1:
        raise ValueError("page 从 1 开始")
    if code is None:
        url = SINA_REPORT_URL.format(kind="lastest")
        params = {"p": int(page)}
    else:
        url = SINA_REPORT_URL.format(kind="search")
        symbol = norm_ticker(code, stock_only=True)
        # 北交所必须带 bj 前缀：只给 6 位数字时新浪返回「没有找到」空页（2026-09-20 实测 920982）
        if get_prefix(code) == "bj":
            symbol = "bj" + symbol
        params = {"symbol": symbol, "t1": "all", "p": int(page)}
    response, text = _sina_report_page(url, params)
    if "tb_01" not in text or "研究员" not in text:
        raise RuntimeError("新浪研报页面结构改变（找不到研报表格）")
    rows = []
    for title, href, rptid, kind, day, org, author in _SINA_REPORT_ROW.findall(text):
        rows.append({"date": _v39_src_date(day.strip()), "title": _html.unescape(title).strip(),
                     "type": kind.strip(), "org": _sina_text(org), "author": _sina_text(author),
                     "report_id": rptid,
                     "url": ("https:" + href) if href.startswith("//") else href})
    # 每页序号都从 1 编起（2026-09-20 实测第 2、3 页也是 1…40）；带序号的行必须全部解析出来。
    # 0 行只有页面写着「没有找到相关内容」（翻过末页 / 该股没有研报）才算真的没有
    numbered = len(re.findall(r"<tr>\s*<td>\d+</td>", text))
    if len(rows) != numbered or (not rows and "没有找到相关内容" not in text):
        raise RuntimeError(f"新浪研报表格有 {numbered} 行带序号、解析出 {len(rows)} 条，行结构可能已变")
    return _v39_frame(rows, "sina", response.url,
                      ["date", "title", "type", "org", "author", "report_id", "url"])


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
    # numpy 标量转为等值 Python 标量；研报字段没有任意对象列。
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
                                         prefix="sina-reports-", suffix=".json", delete=False) as stream:
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

    parser = argparse.ArgumentParser(description="新浪研报单页列表：完整 JSON 落盘，终端只给三条预览。")
    parser.add_argument("code", nargs="?", help="省略为全市场最新；否则为该证券研报")
    parser.add_argument("--page", type=int, default=1, help="单页页码，从 1 开始；不自动翻页")
    parser.add_argument("--output", type=Path, help="完整 JSON 新文件；不覆盖")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        with redirect_stdout(sys.stderr):
            frame = sina_research_reports(args.code, page=args.page)
        payload = _frame_payload(frame)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        path = _save_payload(encoded, args.output)
        preview = dict(payload)
        preview["data"] = payload["data"][:3]
        print(json.dumps({"output": str(path), "row_count": len(frame), "preview_only": True,
                          "preview": preview}, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
