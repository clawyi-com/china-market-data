# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""上证e互动HTML解析、公司定位与进程缓存。"""
import _runtime  # noqa: F401  须在第三方库之前导入
import pandas as pd
from _ticker import norm_ticker, get_prefix
from _market_common import _v39_http, _v39_json, _v39_contract, _v39_frame
import html as _html
import re

SSE_E_BASE = "https://sns.sseinfo.com"
_sse_uid_cache = {}                 # 证券代码 → 上证e互动公司 uid
_sse_company_pages = {}             # 页码 → [(code, uid)]，二分查找时复用
_SSE_COMPANY_END = "没有任何上市公司的信息"
# 没有问答时的提示：公司维度「近1个月暂无回复 / 暂无提问」，全市场翻过末页「暂时没有问答内容」（2026-09-20 实测）
_SSE_EMPTY_NOTE = re.compile(r'class="m_feed_note"[^>]*>[^<]*(暂无|暂时没有)[^<]*<')


def _sse_company_page(page):
    if page not in _sse_company_pages:
        response = _v39_http(SSE_E_BASE + "/allcompany.do", method="POST",
                             data={"code": "0", "order": "2", "areaId": "0", "page": page},
                             headers={"Referer": SSE_E_BASE + "/"})
        payload = _v39_json(response)
        content = payload.get("content") if isinstance(payload, dict) else None
        if not isinstance(content, str):    # 末页之后也返回字符串（2026-09-20 实测），缺 content 是格式变了
            raise RuntimeError(f"上证e互动公司列表第 {page} 页的返回结构变了（没有 content 字符串）")
        pairs = [(code, uid) for uid, code in
                 re.findall(r"uid=['\"]?(\d+)['\"]?[^>]*>\s*<img[^>]*company/(\d{6})\.png", content)]
        # 末页之后固定返回「没有任何上市公司的信息」（2026-09-20 实测第 74 页起）。
        # 第 1 页为空、或者别的页既解析不出公司又没有这句话，只能是页面格式变了，不能说成「公司不存在」
        if not pairs and (page == 1 or _SSE_COMPANY_END not in content):
            raise RuntimeError(f"上证e互动公司列表第 {page} 页解析出 0 家公司，页面格式可能已变")
        _sse_company_pages[page] = pairs
        for code, uid in pairs:
            _sse_uid_cache[code] = uid
    return _sse_company_pages[page]


def _sse_company_uid(code):
    """上证e互动按公司 uid 查询；公司列表按代码升序分页（每页 32 家），倍增 + 二分定位。"""
    if code in _sse_uid_cache:
        return _sse_uid_cache[code]
    low, high = 1, 1
    while _sse_company_page(high):      # 先倍增找到末页之后的空页
        if _sse_company_page(high)[-1][0] >= code:
            break
        low, high = high, high * 2
    while low <= high:
        mid = (low + high) // 2
        pairs = _sse_company_page(mid)
        if not pairs or code < pairs[0][0]:
            high = mid - 1
        elif code > pairs[-1][0]:
            low = mid + 1
        else:
            break
    if code not in _sse_uid_cache:
        raise ValueError(f"上证e互动没有 {code}（公司不在上交所，或已退市）")
    return _sse_uid_cache[code]


def _sse_text(fragment):
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _sse_time(text):
    match = re.search(r"(\d{4})年(\d{2})月(\d{2})日\s*(\d{2}:\d{2})", text)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}" if match else None


def _sse_required_time(item_id, text):
    """问答时间必须解析出来：认不出还照常返回，就是把「时间格式变了」变成了一列 None。"""
    when = _sse_time(text)
    if when is None:
        raise RuntimeError(f"上证e互动第 {item_id} 条的提问时间认不出: {text!r}")
    return when


def _sse_parse_feed(text):
    """「最新回复」与「最新提问」两种列表的标记不同（问题框有没有 id），
    所以不靠 id 区分问答，而是以回复块 class="m_feed_detail m_qa" 为界切成问题段和回复段。"""
    rows = []
    for chunk in re.split(r'<div class="m_feed_item[^"]*" id="item-', text)[1:]:
        numbered = re.match(r"(\d+)", chunk)
        if not numbered:
            raise RuntimeError(f"上证e互动条目 id 不是数字，页面结构可能已变: {chunk[:60]}")
        item_id = numbered.group(1)
        # 注意全市场列表的问题块 class 是 "m_feed_detail m_qa_detail"，只能按完整 class 值切
        ask_part, _, answer_part = chunk.partition('class="m_feed_detail m_qa"')
        question = re.search(r'<div class="m_feed_txt"[^>]*>\s*<a[^>]*>:(.*?)\((\d{6})\)</a>(.*?)</div>',
                             ask_part, re.S)
        asker = re.search(r'rel="face"[^>]*?title="([^"]*)"', ask_part, re.S)
        ask_time = re.search(r'<div class="m_feed_from"[^>]*>\s*<span>([^<]+)</span>', ask_part)
        if not question or not ask_time:
            raise RuntimeError(f"上证e互动第 {item_id} 条结构改变，无法解析问题或时间")
        answer = answer_time = None
        if answer_part:
            body = re.search(r'<div class="m_feed_txt"[^>]*>(.*?)</div>', answer_part, re.S)
            when = re.search(r'<div class="m_feed_from"[^>]*>\s*<span>([^<]+)</span>', answer_part)
            if not body or not when:
                raise RuntimeError(f"上证e互动第 {item_id} 条有回复块但解析不出回复内容或回复时间")
            answer, answer_time = _sse_text(body.group(1)), _sse_time(when.group(1))
            if answer_time is None:     # 实测 500 条问答（含 250 条回复）时间字段无一缺失
                raise RuntimeError(f"上证e互动第 {item_id} 条的回复时间认不出: {when.group(1)!r}")
        rows.append({"id": item_id, "code": question.group(2), "name": _sse_text(question.group(1)),
                     "asker": asker.group(1) if asker else None,
                     "question": _sse_text(question.group(3)),
                     "question_time": _sse_required_time(item_id, ask_time.group(1)),
                     "answer": answer, "answer_time": answer_time})
    return rows


_SSE_KIND = {"answered": 11, "questions": 10}


@_v39_contract
def sse_e_interaction(code=None, kind="answered", page=1, page_size=10):
    """上证e互动 — 投资者提问与沪市上市公司回复（上交所官方平台）。

    code=None 看全市场，给沪市代码（60/68/900 开头）只看该公司。
    kind='answered'：最新已回复问答；kind='questions'：最新提问（含未回复，answer 为 None）。
    平台只开放近期问答：公司维度实测约近 1 个月，更早的翻页为空。
    §10.1 巨潮互动易实测对沪市返回 0 条（2026-09-20，600519/600000/688981），沪市问答只能走本函数。
    首次查某家公司要先在公司列表里定位 uid（倍增 + 二分，约 10–13 次请求），之后走缓存。
    """
    if kind not in _SSE_KIND:
        raise ValueError("kind 只能是 'answered' 或 'questions'")
    if int(page) < 1 or not 1 <= int(page_size) <= 50:
        raise ValueError("page 从 1 开始，page_size 范围 1–50")
    if code is None:
        response = _v39_http(SSE_E_BASE + "/ajax/feeds.do",
                             params={"type": _SSE_KIND[kind], "pageSize": int(page_size), "lastid": -1,
                                     "show": 1, "page": int(page)},
                             headers={"Referer": SSE_E_BASE + "/"})
    else:
        digits = norm_ticker(code, stock_only=True)
        if get_prefix(code) != "sh":
            raise ValueError(f"{code} 不是沪市证券；深市互动问答请用 §10.1 cninfo_irm")  # 北交所两处都没有
        response = _v39_http(SSE_E_BASE + "/ajax/userfeeds.do", method="POST",
                             data={"typeCode": "company", "type": _SSE_KIND[kind], "pageSize": int(page_size),
                                   "uid": _sse_company_uid(digits), "page": int(page)},
                             headers={"Referer": SSE_E_BASE + "/"})
    text = response.content.decode("utf-8", "replace")
    rows = _sse_parse_feed(text)
    # 只有带明确的「暂无 / 暂时没有」提示才算真没有问答；解析出 0 条又没有这句提示，是页面结构变了
    if not rows and not _SSE_EMPTY_NOTE.search(text):
        raise RuntimeError("上证e互动返回的页面既没有问答也没有「暂无」提示，结构可能已变")
    if code is not None and any(r["code"] != digits for r in rows):
        raise RuntimeError("上证e互动返回了其他公司的问答，uid 映射可能已变")
    return _v39_frame(rows, "sse_e", response.url,
                      ["id", "code", "name", "asker", "question", "question_time",
                       "answer", "answer_time"])


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="sse-interaction-", suffix=".json", delete=False) as stream:
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
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description='上证e互动：完整DataFrame保存为JSON')
    parser.add_argument('--code', default=None)
    parser.add_argument('--kind', choices=('answered', 'questions'), default='answered')
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--page-size', type=int, default=10)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error('输出文件已存在，请指定新路径')
    try:
        frame = sse_e_interaction(args.code, args.kind, args.page, args.page_size)
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
